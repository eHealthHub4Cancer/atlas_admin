"""
REST API views for the Atlas Admin dashboard.
Uses Django REST Framework for consistent API responses.
"""
import math
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import AtlasUser, UserProfile, AdminUser, Permission
from .serializers import (
    AtlasUserSerializer,
    PermissionSerializer,
    CombinedUserSerializer,
    ActivityLogSerializer,
    DashboardStatsSerializer,
    AuthSessionSerializer,
    LoginSerializer,
    AdminLoginSerializer,
    SignupSerializer,
    ProfileUpdateSerializer,
    PasswordChangeSerializer,
    BulkGrantSerializer,
    UserUpdateSerializer,
)

# Import helpers from main views
from .views import (
    get_current_user,
    get_current_admin,
    sync_permissions_from_webapi,
    ensure_webapi_user,
    set_webapi_user_roles_preserving_base,
)


def _parse_int(value, default=1, min_value=1, max_value=None):
    """Parse integer from request with bounds checking."""
    try:
        val = int(value) if value else default
        val = max(min_value, val)
        if max_value:
            val = min(max_value, val)
        return val
    except (ValueError, TypeError):
        return default


def _paginate(queryset, page, page_size):
    """Paginate a queryset and return (items, metadata)."""
    total = queryset.count()
    total_pages = max(1, math.ceil(total / page_size))
    page = min(page, total_pages)
    offset = (page - 1) * page_size
    items = list(queryset[offset:offset + page_size])
    return items, {
        'count': total,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
    }


# ─────────────────────────────────────────────────────────────────────────────
# AUTH API ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['GET'])
def session_api(request):
    """Get current session info."""
    user = get_current_user(request)
    admin = get_current_admin(request)

    if admin:
        return Response({
            'user_id': admin.id,
            'username': None,
            'role': 'admin',
            'is_admin': admin.is_admin,
            'is_super_admin': admin.is_super_admin,
            'display_name': admin.name,
            'email': admin.email,
        })
    elif user:
        profile = getattr(user, 'profile', None)
        return Response({
            'user_id': user.id,
            'username': user.username,
            'role': user.role,
            'is_admin': False,
            'is_super_admin': False,
            'display_name': profile.display_name if profile else user.username,
            'email': profile.email if profile else None,
        })

    return Response(None, status=status.HTTP_200_OK)


@api_view(['POST'])
def login_api(request):
    """User login API."""
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    username = serializer.validated_data['username'].strip()
    password = serializer.validated_data['password']

    try:
        user = AtlasUser.objects.get(username__iexact=username)
    except AtlasUser.DoesNotExist:
        if "@" in username:
            try:
                profile = UserProfile.objects.select_related("user").get(email__iexact=username)
                user = profile.user
            except UserProfile.DoesNotExist:
                return Response({'message': 'Invalid username or password'}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({'message': 'Invalid username or password'}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.check_password(password):
        return Response({'message': 'Invalid username or password'}, status=status.HTTP_401_UNAUTHORIZED)

    if user.is_disabled:
        return Response({'message': 'Your account has been disabled'}, status=status.HTTP_403_FORBIDDEN)

    # Set session
    request.session['user_id'] = user.id
    request.session['username'] = user.username
    request.session['role'] = user.role

    return Response({'success': True, 'redirect': '/user'})


@api_view(['POST'])
def admin_login_api(request):
    """Admin login API."""
    serializer = AdminLoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email'].strip().lower()
    password = serializer.validated_data['password']

    try:
        admin = AdminUser.objects.get(email__iexact=email)
    except AdminUser.DoesNotExist:
        return Response({'message': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)

    if not admin.check_password(password):
        return Response({'message': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)

    if not (admin.is_admin or admin.is_super_admin):
        return Response({'message': 'You do not have admin access'}, status=status.HTTP_403_FORBIDDEN)

    # Set session
    request.session['admin_user_id'] = admin.id
    request.session['admin_email'] = admin.email
    request.session['is_super_admin'] = admin.is_super_admin

    return Response({'success': True, 'redirect': '/admin'})


@api_view(['POST'])
def signup_api(request):
    """User signup API."""
    serializer = SignupSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    # Create user
    user = AtlasUser(
        username=data['username'],
        role=data.get('role', 'guest'),
    )
    user.set_password(data['password1'])
    user.save()

    # Create profile
    UserProfile.objects.create(
        user=user,
        display_name=data['display_name'],
        email=data['email'],
        affiliation=data.get('affiliation', ''),
        prefix=data.get('prefix', ''),
    )

    # Sync to WebAPI
    try:
        ensure_webapi_user(user)
    except Exception:
        pass  # Don't fail signup if WebAPI sync fails

    return Response({'success': True, 'redirect': '/login'})


@api_view(['POST'])
def logout_api(request):
    """Logout API."""
    request.session.flush()
    return Response({'success': True})


# ─────────────────────────────────────────────────────────────────────────────
# USER API ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['GET', 'PUT'])
def user_profile_api(request):
    """Get or update user profile."""
    user = get_current_user(request)
    if not user:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if request.method == 'GET':
        return Response(AtlasUserSerializer(user).data)

    # PUT - Update profile
    serializer = ProfileUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    profile = getattr(user, 'profile', None)

    # Check email uniqueness
    if data['email'].lower() != (profile.email.lower() if profile else ''):
        if UserProfile.objects.filter(email__iexact=data['email']).exclude(user=user).exists():
            return Response({'errors': {'email': ['This email is already in use.']}}, status=status.HTTP_400_BAD_REQUEST)

    if profile:
        profile.display_name = data['display_name']
        profile.email = data['email']
        profile.affiliation = data.get('affiliation', '')
        profile.prefix = data.get('prefix', '')
        profile.save()
    else:
        UserProfile.objects.create(
            user=user,
            display_name=data['display_name'],
            email=data['email'],
            affiliation=data.get('affiliation', ''),
            prefix=data.get('prefix', ''),
        )

    return Response(AtlasUserSerializer(user).data)


@api_view(['POST'])
def user_change_password_api(request):
    """Change user password."""
    user = get_current_user(request)
    if not user:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    serializer = PasswordChangeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    if not user.check_password(data['current_password']):
        return Response({'errors': {'current_password': ['Current password is incorrect.']}}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(data['new_password1'])
    user.save()

    return Response({'success': True})


@api_view(['GET'])
def user_roles_api(request):
    """Get user's assigned roles/permissions."""
    user = get_current_user(request)
    if not user:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    permissions = user.permissions.all()
    return Response(PermissionSerializer(permissions, many=True).data)


@api_view(['GET'])
def user_activity_api_v2(request):
    """Get user activity log with pagination."""
    user = get_current_user(request)
    if not user:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    profile = getattr(user, 'profile', None)

    # Build activity entries
    entries = [
        {'id': 1, 'action': 'Account Created', 'summary': 'Your account was created', 'timestamp': user.created_at, 'status': 'success'},
        {'id': 2, 'action': 'Account Updated', 'summary': 'Your account was updated', 'timestamp': user.updated_at, 'status': 'info'},
    ]
    if profile:
        entries.extend([
            {'id': 3, 'action': 'Profile Created', 'summary': 'Your profile was created', 'timestamp': profile.created_at, 'status': 'success'},
            {'id': 4, 'action': 'Profile Updated', 'summary': 'Your profile was updated', 'timestamp': profile.updated_at, 'status': 'info'},
        ])

    # Filters
    search = request.GET.get('search', '').lower()
    status_filter = request.GET.get('status', '').lower()
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    ordering = request.GET.get('ordering', '-timestamp')
    page = _parse_int(request.GET.get('page'), default=1)
    page_size = _parse_int(request.GET.get('page_size'), default=10, max_value=50)

    # Apply filters
    if search:
        entries = [e for e in entries if search in e['summary'].lower() or search in e['action'].lower()]
    if status_filter:
        entries = [e for e in entries if e['status'] == status_filter]
    if date_from:
        entries = [e for e in entries if str(e['timestamp'].date()) >= date_from]
    if date_to:
        entries = [e for e in entries if str(e['timestamp'].date()) <= date_to]

    # Sort
    reverse = ordering.startswith('-')
    sort_key = ordering.lstrip('-')
    if sort_key in ('timestamp', 'action', 'status'):
        entries.sort(key=lambda x: x[sort_key], reverse=reverse)

    # Paginate
    total = len(entries)
    total_pages = max(1, math.ceil(total / page_size))
    page = min(page, total_pages)
    offset = (page - 1) * page_size
    page_entries = entries[offset:offset + page_size]

    return Response({
        'results': page_entries,
        'count': total,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
    })


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN API ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['GET'])
def admin_stats_api(request):
    """Get admin dashboard statistics."""
    admin = get_current_admin(request)
    if not admin:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    total_users = AtlasUser.objects.count()
    admin_users = AdminUser.objects.filter(is_admin=True).count()
    roles_count = Permission.objects.count()
    active_users = AtlasUser.objects.filter(is_disabled=False).count()
    disabled_users = AtlasUser.objects.filter(is_disabled=True).count()

    return Response({
        'total_users': total_users,
        'admin_users': admin_users,
        'roles_count': roles_count,
        'active_users': active_users,
        'disabled_users': disabled_users,
    })


@api_view(['GET'])
def admin_users_api(request):
    """Get all users (combined atlas + admin) with pagination."""
    admin = get_current_admin(request)
    if not admin:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    # Get params
    search = request.GET.get('search', '').strip()
    user_type = request.GET.get('user_type', '').strip()
    status_filter = request.GET.get('status', '').strip()
    role_filter = request.GET.get('role', '').strip()
    ordering = request.GET.get('ordering', 'display_name')
    page = _parse_int(request.GET.get('page'), default=1)
    page_size = _parse_int(request.GET.get('page_size'), default=10, max_value=50)

    # Build combined user list
    users = []

    # Add Atlas users
    if user_type in ('', 'atlas'):
        atlas_qs = AtlasUser.objects.select_related('profile').prefetch_related('permissions')
        if search:
            atlas_qs = atlas_qs.filter(
                Q(username__icontains=search) |
                Q(profile__display_name__icontains=search) |
                Q(profile__email__icontains=search)
            )
        if status_filter == 'active':
            atlas_qs = atlas_qs.filter(is_disabled=False)
        elif status_filter == 'disabled':
            atlas_qs = atlas_qs.filter(is_disabled=True)
        if role_filter:
            atlas_qs = atlas_qs.filter(role=role_filter)

        for u in atlas_qs:
            profile = getattr(u, 'profile', None)
            users.append({
                'id': u.id,
                'username': u.username,
                'display_name': profile.display_name if profile else u.username,
                'email': profile.email if profile else '',
                'role': u.role,
                'is_disabled': u.is_disabled,
                'is_admin': False,
                'is_super_admin': False,
                'user_type': 'atlas',
                'permissions': list(u.permissions.all().values('id', 'name', 'external_id', 'description')),
            })

    # Add Admin users
    if user_type in ('', 'admin'):
        admin_qs = AdminUser.objects.filter(is_admin=True)
        if search:
            admin_qs = admin_qs.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search)
            )

        for a in admin_qs:
            users.append({
                'id': a.id,
                'username': None,
                'display_name': a.name,
                'email': a.email,
                'role': 'super_admin' if a.is_super_admin else 'admin',
                'is_disabled': False,
                'is_admin': a.is_admin,
                'is_super_admin': a.is_super_admin,
                'user_type': 'admin',
                'permissions': [],
            })

    # Sort
    reverse = ordering.startswith('-')
    sort_key = ordering.lstrip('-')
    if sort_key in ('display_name', 'email', 'role', 'is_disabled'):
        users.sort(key=lambda x: (x.get(sort_key) or '').lower() if isinstance(x.get(sort_key), str) else x.get(sort_key, False), reverse=reverse)

    # Paginate
    total = len(users)
    total_pages = max(1, math.ceil(total / page_size))
    page = min(page, total_pages)
    offset = (page - 1) * page_size
    page_users = users[offset:offset + page_size]

    return Response({
        'results': page_users,
        'count': total,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
    })


@api_view(['GET', 'PUT'])
def admin_user_detail_api(request, user_id):
    """Get or update a specific user."""
    admin = get_current_admin(request)
    if not admin:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    user_type = request.GET.get('type', 'atlas')

    if request.method == 'GET':
        if user_type == 'admin':
            try:
                user = AdminUser.objects.get(id=user_id)
                return Response({
                    'id': user.id,
                    'username': None,
                    'display_name': user.name,
                    'email': user.email,
                    'role': 'super_admin' if user.is_super_admin else 'admin',
                    'is_disabled': False,
                    'is_admin': user.is_admin,
                    'is_super_admin': user.is_super_admin,
                    'user_type': 'admin',
                    'permissions': [],
                })
            except AdminUser.DoesNotExist:
                return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            try:
                user = AtlasUser.objects.select_related('profile').prefetch_related('permissions').get(id=user_id)
                profile = getattr(user, 'profile', None)
                return Response({
                    'id': user.id,
                    'username': user.username,
                    'display_name': profile.display_name if profile else user.username,
                    'email': profile.email if profile else '',
                    'role': user.role,
                    'is_disabled': user.is_disabled,
                    'is_admin': False,
                    'is_super_admin': False,
                    'user_type': 'atlas',
                    'permissions': list(user.permissions.all().values('id', 'name', 'external_id', 'description')),
                })
            except AtlasUser.DoesNotExist:
                return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    # PUT - Update user
    serializer = UserUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    target_type = data.get('type', 'atlas')

    if target_type == 'atlas':
        try:
            user = AtlasUser.objects.get(id=user_id)
            if 'is_disabled' in data:
                user.is_disabled = data['is_disabled']
                user.save()
            if 'permissions' in data:
                perm_ids = data['permissions']
                perms = Permission.objects.filter(id__in=perm_ids)
                user.permissions.set(perms)
                # Sync to WebAPI
                try:
                    set_webapi_user_roles_preserving_base(user, [p.name for p in perms])
                except Exception:
                    pass
            return Response({'success': True})
        except AtlasUser.DoesNotExist:
            return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    return Response({'success': True})


@api_view(['GET'])
def admin_roles_api_v2(request):
    """Get all roles with pagination."""
    admin = get_current_admin(request)
    if not admin:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    # Sync from WebAPI
    sync_permissions_from_webapi()

    # Get params
    search = request.GET.get('search', '').strip()
    filter_value = request.GET.get('filter', '').strip()
    ordering = request.GET.get('ordering', 'name')
    page = _parse_int(request.GET.get('page'), default=1)
    page_size = _parse_int(request.GET.get('page_size'), default=10, max_value=50)

    # Build queryset
    queryset = Permission.objects.all()
    if search:
        queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
    if filter_value == 'with_id':
        queryset = queryset.filter(external_id__isnull=False)
    elif filter_value == 'no_id':
        queryset = queryset.filter(external_id__isnull=True)

    # Ordering
    allowed_ordering = {'name', '-name', 'external_id', '-external_id'}
    if ordering not in allowed_ordering:
        ordering = 'name'
    queryset = queryset.order_by(ordering)

    # Paginate
    items, meta = _paginate(queryset, page, page_size)

    return Response({
        'results': PermissionSerializer(items, many=True).data,
        **meta,
    })


@api_view(['GET'])
def admin_permissions_api_v2(request):
    """Get all permissions with pagination."""
    # Same as roles for now
    return admin_roles_api_v2(request)


@api_view(['POST'])
def admin_bulk_grant_api(request):
    """Bulk grant permissions to users."""
    admin = get_current_admin(request)
    if not admin:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    serializer = BulkGrantSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    user_ids = data['user_ids']
    permission_ids = data['permission_ids']

    users = AtlasUser.objects.filter(id__in=user_ids)
    permissions = Permission.objects.filter(id__in=permission_ids)

    updated = 0
    for user in users:
        # Add permissions (don't remove existing)
        for perm in permissions:
            user.permissions.add(perm)
        updated += 1
        # Sync to WebAPI
        try:
            all_perms = list(user.permissions.all())
            set_webapi_user_roles_preserving_base(user, [p.name for p in all_perms])
        except Exception:
            pass

    return Response({'success': True, 'updated': updated})


@api_view(['POST'])
def admin_promote_api(request):
    """Promote an Atlas user to Admin."""
    admin = get_current_admin(request)
    if not admin or not admin.is_super_admin:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    user_id = request.data.get('user_id')
    if not user_id:
        return Response({'message': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = AtlasUser.objects.select_related('profile').get(id=user_id)
    except AtlasUser.DoesNotExist:
        return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    profile = getattr(user, 'profile', None)
    if not profile or not profile.email:
        return Response({'message': 'User must have an email to be promoted'}, status=status.HTTP_400_BAD_REQUEST)

    # Check if already admin
    if AdminUser.objects.filter(email__iexact=profile.email).exists():
        return Response({'message': 'This user is already an admin'}, status=status.HTTP_400_BAD_REQUEST)

    # Create admin user
    admin_user = AdminUser(
        name=profile.display_name,
        email=profile.email,
        affiliation=profile.affiliation or '',
        is_admin=True,
        is_super_admin=False,
    )
    admin_user.set_password('changeme123')  # Default password, should be changed
    admin_user.save()

    return Response({'success': True})


@api_view(['POST'])
def admin_remove_admin_api(request):
    """Remove admin access from a user."""
    admin = get_current_admin(request)
    if not admin or not admin.is_super_admin:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    admin_id = request.data.get('admin_id')
    if not admin_id:
        return Response({'message': 'admin_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        target_admin = AdminUser.objects.get(id=admin_id)
    except AdminUser.DoesNotExist:
        return Response({'message': 'Admin not found'}, status=status.HTTP_404_NOT_FOUND)

    if target_admin.is_super_admin:
        return Response({'message': 'Cannot remove super admin'}, status=status.HTTP_400_BAD_REQUEST)

    target_admin.is_admin = False
    target_admin.save()

    return Response({'success': True})


@api_view(['POST'])
def admin_sync_roles_api(request):
    """Manually sync roles from WebAPI."""
    admin = get_current_admin(request)
    if not admin:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    count = sync_permissions_from_webapi()
    return Response({'success': True, 'synced': count or 0})
