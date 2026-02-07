"""
Atlas Config - REST API Views

API endpoints for authentication, user management, roles, and prefixes.
"""

import math
from django.db.models import Q, Count
from rest_framework import status
from rest_framework.decorators import api_view
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.response import Response

from .models import User, AtlasAdmin, Role, Prefix, Category, UserRole
from .serializers import (
    UserSerializer,
    RoleSerializer,
    RoleCreateUpdateSerializer,
    PrefixSerializer,
    PrefixCreateUpdateSerializer,
    CategorySerializer,
    CategoryCreateUpdateSerializer,
    LoginSerializer,
    AdminLoginSerializer,
    SignupSerializer,
    PasswordChangeSerializer,
    AuthSessionSerializer,
    ProfileUpdateSerializer,
    BulkRoleAssignSerializer,
    DashboardStatsSerializer,
)
from .sec_sync import sync_user_to_sec, grant_role_to_sec, sync_user_profile_to_sec, sync_user_password_to_sec


# =============================================================================
# Helper Functions
# =============================================================================

def get_current_user(request):
    """Get the current user from session."""
    user_id = request.session.get('user_id')
    if user_id:
        try:
            return User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            pass
    return None


def get_current_admin(request):
    """Get the current admin from session."""
    admin_id = request.session.get('admin_id')
    if admin_id:
        try:
            return AtlasAdmin.objects.get(id=admin_id, is_active=True)
        except AtlasAdmin.DoesNotExist:
            pass
    return None


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


# =============================================================================
# Authentication API
# =============================================================================

@ensure_csrf_cookie
@api_view(['GET'])
def session_api(request):
    """Get current session info."""
    user = get_current_user(request)
    admin = get_current_admin(request)

    if admin:
        return Response({
            'user_id': admin.id,
            'username': None,
            'role': admin.role,
            'is_admin': admin.is_admin,
            'is_super_admin': admin.is_super_admin,
            'display_name': admin.display_name,
            'email': admin.email,
        })
    elif user:
        return Response({
            'user_id': user.id,
            'username': user.username,
            'role': user.role_names[0] if user.role_names else 'guest',
            'is_admin': False,
            'is_super_admin': False,
            'display_name': user.display_name,
            'email': user.email,
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

    # Try username or email
    try:
        if '@' in username:
            user = User.objects.get(email__iexact=username)
        else:
            user = User.objects.get(username__iexact=username)
    except User.DoesNotExist:
        return Response({'message': 'Invalid username or password'}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.check_password(password):
        return Response({'message': 'Invalid username or password'}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.is_active:
        return Response({'message': 'Your account has been disabled'}, status=status.HTTP_403_FORBIDDEN)

    # Set session
    request.session['user_id'] = user.id
    request.session['username'] = user.username

    user.update_last_login()

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
        admin = AtlasAdmin.objects.get(email__iexact=email)
    except AtlasAdmin.DoesNotExist:
        return Response({'message': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)

    if not admin.check_password(password):
        return Response({'message': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)

    if not admin.is_active:
        return Response({'message': 'Your account has been disabled'}, status=status.HTTP_403_FORBIDDEN)

    # Set session
    request.session['admin_id'] = admin.id
    request.session['admin_email'] = admin.email

    admin.update_last_login()

    return Response({'success': True, 'redirect': '/admin'})


@api_view(['POST'])
def signup_api(request):
    """User signup API."""
    serializer = SignupSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    
    # Parse display_name into first_name and last_name
    display_name = data.get('display_name', '').strip()
    name_parts = display_name.split(' ', 1)
    first_name = name_parts[0] if name_parts else ''
    last_name = name_parts[1] if len(name_parts) > 1 else ''

    # Get prefix if provided
    prefix = None
    if data.get('prefix'):
        try:
            prefix = Prefix.objects.get(name=data['prefix'], is_active=True)
        except Prefix.DoesNotExist:
            pass

    # Get category if provided
    category = None
    if data.get('category'):
        try:
            category = Category.objects.get(name=data['category'], is_active=True)
        except Category.DoesNotExist:
            pass

    # Create user
    user = User(
        username=data['username'],
        email=data['email'],
        first_name=first_name,
        last_name=last_name,
        prefix=prefix,
        category=category,
        affiliation=data.get('affiliation', ''),
    )
    user.set_password(data['password1'])
    user.save()

    # Sync user into SEC tables (sec_user + base roles)
    sync_user_to_sec(user, raw_password=data['password1'])

    # Assign role if provided
    if data.get('role'):
        try:
            role = Role.objects.get(name=data['role'], is_active=True)
            UserRole.objects.create(user=user, role=role, origin=UserRole.ORIGIN_ATLAS)
            grant_role_to_sec(user, role.name)
        except Role.DoesNotExist:
            pass

    return Response({'success': True, 'redirect': '/login'})


@api_view(['POST'])
def logout_api(request):
    """Logout API."""
    request.session.flush()
    return Response({'success': True})


# =============================================================================
# Prefix API (Public - for signup form)
# =============================================================================

@api_view(['GET'])
def prefixes_list_api(request):
    """Get all active prefixes for forms."""
    prefixes = Prefix.objects.filter(is_active=True).order_by('sort_order', 'display_name')
    return Response(PrefixSerializer(prefixes, many=True).data)


# =============================================================================
# Role API (Public - for signup form)
# =============================================================================

@api_view(['GET'])
def roles_list_api(request):
    """Get all active roles for forms."""
    roles = Role.objects.filter(is_active=True).order_by('sort_order', 'name')
    return Response(RoleSerializer(roles, many=True).data)


# =============================================================================
# Category API (Public - for signup form)
# =============================================================================

@api_view(['GET'])
def categories_list_api(request):
    """Get all active categories for forms."""
    categories = Category.objects.filter(is_active=True).order_by('sort_order', 'display_name')
    return Response(CategorySerializer(categories, many=True).data)


# =============================================================================
# Admin - Prefix CRUD API
# =============================================================================

@api_view(['GET', 'POST'])
def admin_prefixes_api(request):
    """List all prefixes or create a new one (super_admin only)."""
    admin = get_current_admin(request)
    if not admin or not admin.is_super_admin:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if request.method == 'GET':
        # Get params
        search = request.GET.get('search', '').strip()
        page = _parse_int(request.GET.get('page'), default=1)
        page_size = _parse_int(request.GET.get('page_size'), default=10, max_value=50)

        # Build queryset
        queryset = Prefix.objects.all()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(display_name__icontains=search)
            )

        queryset = queryset.order_by('sort_order', 'display_name')

        # Paginate
        items, meta = _paginate(queryset, page, page_size)

        return Response({
            'results': PrefixSerializer(items, many=True).data,
            **meta,
        })

    # POST - Create new prefix
    serializer = PrefixCreateUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    prefix = serializer.save()
    return Response(PrefixSerializer(prefix).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
def admin_prefix_detail_api(request, prefix_id):
    """Get, update, or delete a specific prefix (super_admin only)."""
    admin = get_current_admin(request)
    if not admin or not admin.is_super_admin:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        prefix = Prefix.objects.get(id=prefix_id)
    except Prefix.DoesNotExist:
        return Response({'detail': 'Prefix not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(PrefixSerializer(prefix).data)

    elif request.method == 'PUT':
        serializer = PrefixCreateUpdateSerializer(prefix, data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
        prefix = serializer.save()
        return Response(PrefixSerializer(prefix).data)

    elif request.method == 'DELETE':
        # Check if any users are using this prefix
        user_count = prefix.users.count()
        if user_count > 0:
            return Response({
                'message': f'Cannot delete prefix. {user_count} user(s) are using it.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        prefix.delete()
        return Response({'success': True}, status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# Admin - Role CRUD API
# =============================================================================

@api_view(['GET', 'POST'])
def admin_roles_api(request):
    """List all roles or create a new one (super_admin only)."""
    admin = get_current_admin(request)
    if not admin or not admin.is_super_admin:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if request.method == 'GET':
        # Get params
        search = request.GET.get('search', '').strip()
        page = _parse_int(request.GET.get('page'), default=1)
        page_size = _parse_int(request.GET.get('page_size'), default=10, max_value=50)

        # Build queryset with user count
        queryset = Role.objects.annotate(user_count=Count('users'))
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        queryset = queryset.order_by('sort_order', 'name')

        # Paginate
        items, meta = _paginate(queryset, page, page_size)

        return Response({
            'results': RoleSerializer(items, many=True).data,
            **meta,
        })

    # POST - Create new role
    serializer = RoleCreateUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    role = serializer.save()
    return Response(RoleSerializer(role).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
def admin_role_detail_api(request, role_id):
    """Get, update, or delete a specific role (super_admin only)."""
    admin = get_current_admin(request)
    if not admin or not admin.is_super_admin:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        role = Role.objects.annotate(user_count=Count('users')).get(id=role_id)
    except Role.DoesNotExist:
        return Response({'detail': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(RoleSerializer(role).data)

    elif request.method == 'PUT':
        serializer = RoleCreateUpdateSerializer(role, data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
        role = serializer.save()
        return Response(RoleSerializer(role).data)

    elif request.method == 'DELETE':
        # Check if any users have this role
        user_count = role.users.count()
        if user_count > 0:
            return Response({
                'message': f'Cannot delete role. {user_count} user(s) have this role.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        role.delete()
        return Response({'success': True}, status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# Admin - Category CRUD API
# =============================================================================

@api_view(['GET', 'POST'])
def admin_categories_api(request):
    """List all categories or create a new one (super_admin only)."""
    admin = get_current_admin(request)
    if not admin or not admin.is_super_admin:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if request.method == 'GET':
        search = request.GET.get('search', '').strip()
        page = _parse_int(request.GET.get('page'), default=1)
        page_size = _parse_int(request.GET.get('page_size'), default=10, max_value=50)

        queryset = Category.objects.annotate(user_count=Count('users'))
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(display_name__icontains=search)
            )

        queryset = queryset.order_by('sort_order', 'display_name')
        items, meta = _paginate(queryset, page, page_size)

        return Response({
            'results': CategorySerializer(items, many=True).data,
            **meta,
        })

    # POST - Create new category
    serializer = CategoryCreateUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    category = serializer.save()
    return Response(CategorySerializer(category).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
def admin_category_detail_api(request, category_id):
    """Get, update, or delete a specific category (super_admin only)."""
    admin = get_current_admin(request)
    if not admin or not admin.is_super_admin:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        category = Category.objects.annotate(user_count=Count('users')).get(id=category_id)
    except Category.DoesNotExist:
        return Response({'detail': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(CategorySerializer(category).data)

    elif request.method == 'PUT':
        serializer = CategoryCreateUpdateSerializer(category, data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        category = serializer.save()
        return Response(CategorySerializer(category).data)

    elif request.method == 'DELETE':
        user_count = category.users.count()
        if user_count > 0:
            return Response({
                'message': f'Cannot delete category. {user_count} user(s) are using it.'
            }, status=status.HTTP_400_BAD_REQUEST)

        category.delete()
        return Response({'success': True}, status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# Admin - Dashboard Stats
# =============================================================================

@api_view(['GET'])
def admin_stats_api(request):
    """Get admin dashboard statistics."""
    admin = get_current_admin(request)
    if not admin:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    total_users = User.objects.count()
    admin_users = AtlasAdmin.objects.filter(is_active=True).count()
    roles_count = Role.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    disabled_users = User.objects.filter(is_active=False).count()

    return Response({
        'total_users': total_users,
        'admin_users': admin_users,
        'roles_count': roles_count,
        'active_users': active_users,
        'disabled_users': disabled_users,
    })


# =============================================================================
# Admin - User Management
# =============================================================================

@api_view(['GET'])
def admin_users_api(request):
    """Get all users with pagination."""
    admin = get_current_admin(request)
    if not admin:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    # Get params
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    role_filter = request.GET.get('role', '').strip()
    page = _parse_int(request.GET.get('page'), default=1)
    page_size = _parse_int(request.GET.get('page_size'), default=10, max_value=50)

    # Build queryset
    queryset = User.objects.prefetch_related('roles', 'prefix')
    
    if search:
        queryset = queryset.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    if status_filter == 'active':
        queryset = queryset.filter(is_active=True)
    elif status_filter == 'disabled':
        queryset = queryset.filter(is_active=False)
    
    if role_filter:
        queryset = queryset.filter(roles__id=role_filter)

    queryset = queryset.order_by('-created_at')

    # Paginate
    items, meta = _paginate(queryset, page, page_size)

    # Serialize with combined user format
    results = []
    for user in items:
        results.append({
            'id': user.id,
            'username': user.username,
            'display_name': user.display_name,
            'email': user.email,
            'role': user.role_names[0] if user.role_names else 'guest',
            'is_disabled': not user.is_active,
            'is_admin': False,
            'is_super_admin': False,
            'user_type': 'atlas',
            'permissions': [{'id': r.id, 'name': r.name} for r in user.roles.all()],
        })

    return Response({
        'results': results,
        **meta,
    })


# =============================================================================
# User Profile API
# =============================================================================

@api_view(['GET', 'PUT'])
def user_profile_api(request):
    """Get or update user profile."""
    user = get_current_user(request)
    if not user:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    if request.method == 'GET':
        return Response(UserSerializer(user).data)

    # PUT - Update profile
    serializer = ProfileUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    
    # Parse display_name
    display_name = data.get('display_name', '').strip()
    name_parts = display_name.split(' ', 1)
    user.first_name = name_parts[0] if name_parts else ''
    user.last_name = name_parts[1] if len(name_parts) > 1 else ''
    
    user.email = data['email']
    user.affiliation = data.get('affiliation', '')
    
    # Update prefix
    if data.get('prefix'):
        try:
            user.prefix = Prefix.objects.get(name=data['prefix'], is_active=True)
        except Prefix.DoesNotExist:
            user.prefix = None
    else:
        user.prefix = None
    
    user.save()
    sync_user_profile_to_sec(user)

    return Response(UserSerializer(user).data)


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
        return Response({
            'errors': {'current_password': ['Current password is incorrect.']}
        }, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(data['new_password1'])
    user.save()
    sync_user_password_to_sec(user, raw_password=data['new_password1'])

    return Response({'success': True})


@api_view(['GET'])
def user_roles_api(request):
    """Get user's assigned roles."""
    user = get_current_user(request)
    if not user:
        return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    roles = user.roles.all()
    return Response(RoleSerializer(roles, many=True).data)
