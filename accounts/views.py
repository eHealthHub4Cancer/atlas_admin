"""
Atlas Config - Views

Authentication, dashboard, role management, and admin views.
Supports dual authentication: User (username) and AtlasAdmin (email).
Includes HTMX/AJAX endpoints for async operations.

View Organization:
-----------------
1. Decorators - Authentication and authorization
2. User Authentication - Login, signup, logout, password reset
3. Admin Authentication - Separate admin login flow
4. User Dashboard - Profile, roles, messages, support
5. Admin Dashboard - User management, role management, bulk operations
6. HTMX/AJAX Views - Async operations for role grants, search, etc.
7. Message Views - Announcements management
8. Utility Views - Health check, error handlers

SEC Sync Integration:
--------------------
User creation triggers SEC sync via sync_user_to_sec()
Role grants/revokes sync via grant_role_to_sec() / revoke_role_from_sec()
"""

import logging
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.decorators.csrf import csrf_protect
from django.db.models import Count, Q, Prefetch
from django.core.paginator import Paginator
from django.template.loader import render_to_string

from .models import User, AtlasAdmin, Role, Category, Prefix, UserRole, Message, MessageDismissal, AuditLog, PasswordResetToken
from .forms import (
    UserLoginForm, UserSignupForm, AdminLoginForm,
    ForgotPasswordForm, ResetPasswordForm, ChangePasswordForm,
    UserProfileForm, AdminProfileForm, UserEditForm,
    RoleForm, RoleDescriptionForm, UserRoleAssignForm, UserRoleRevokeForm,
    BulkRoleAssignForm, AdminCreateForm, AdminRoleChangeForm,
    MessageForm, UserSearchForm
)
from .sec_sync import (
    sync_user_to_sec,
    sync_roles_from_sec,
    grant_role_to_sec,
    revoke_role_from_sec,
    sync_user_profile_to_sec,
    sync_user_password_to_sec,
)
from .tasks import (
    send_welcome_email, send_password_reset_email,
    send_password_changed_email
)

logger = logging.getLogger(__name__)


def _render_user_roles_modal(admin, user):
    """Render role-management modal content for a specific user."""
    user_roles = user.user_roles.select_related('role', 'granted_by').order_by('role__name')
    all_roles = Role.objects.order_by('name')
    user_role_ids = set(user.roles.values_list('id', flat=True))
    available_roles = all_roles.exclude(id__in=user_role_ids)
    return render_to_string('accounts/partials/user_roles_modal.html', {
        'admin': admin,
        'target_user': user,
        'user_roles': user_roles,
        'available_roles': available_roles,
    })


# =============================================================================
# Authentication Decorators
# =============================================================================

def get_current_user(request):
    """Get the current user from session (User model)."""
    user_id = request.session.get('user_id')
    if user_id:
        try:
            return User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            pass
    return None


def get_current_admin(request):
    """Get the current admin from session (AtlasAdmin model)."""
    admin_id = request.session.get('admin_id')
    if admin_id:
        try:
            return AtlasAdmin.objects.get(id=admin_id, is_active=True)
        except AtlasAdmin.DoesNotExist:
            pass
    return None


def user_login_required(view_func):
    """Decorator to require user authentication."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            messages.warning(request, 'Please log in to access this page.')
            return redirect('user_login')
        request.current_user = user
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_login_required(view_func):
    """Decorator to require admin authentication."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        admin = get_current_admin(request)
        if not admin:
            messages.warning(request, 'Please log in as an administrator.')
            return redirect('admin_login')
        request.current_admin = admin
        return view_func(request, *args, **kwargs)
    return wrapper


def super_admin_required(view_func):
    """Decorator to require super_admin role."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        admin = get_current_admin(request)
        if not admin:
            messages.warning(request, 'Please log in as an administrator.')
            return redirect('admin_login')
        if not admin.is_super_admin:
            messages.error(request, 'Only Super Admins can perform this action.')
            return redirect('admin_dashboard')
        request.current_admin = admin
        return view_func(request, *args, **kwargs)
    return wrapper


def system_superadmin_required(view_func):
    """Decorator to require system_superadmin role."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        admin = get_current_admin(request)
        if not admin:
            messages.warning(request, 'Please log in as an administrator.')
            return redirect('admin_login')
        if not admin.is_system_superadmin:
            messages.error(request, 'Only System Super Admins can perform this action.')
            return redirect('admin_dashboard')
        request.current_admin = admin
        return view_func(request, *args, **kwargs)
    return wrapper


def anonymous_required(view_func):
    """Decorator to redirect authenticated users."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if get_current_user(request):
            return redirect('user_dashboard')
        if get_current_admin(request):
            return redirect('admin_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


# =============================================================================
# User Authentication Views
# =============================================================================

@anonymous_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def user_login_view(request):
    """User login view (username/email based)."""
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']

            # Set session
            request.session['user_id'] = user.id
            request.session['user_email'] = user.email
            request.session['user_username'] = user.username

            # Update last login
            user.update_last_login()

            # Log the action
            AuditLog.log(
                action=AuditLog.ACTION_LOGIN,
                actor_user=user,
                target_user=user,
                description=f'User logged in: {user.username}',
                request=request
            )

            messages.success(request, f'Welcome back, {user.first_name}!')
            return redirect('user_dashboard')
        else:
            # Log failed login attempt
            username = request.POST.get('username', '')
            AuditLog.log(
                action=AuditLog.ACTION_LOGIN_FAILED,
                description=f'Failed user login attempt: {username}',
                request=request
            )
    else:
        form = UserLoginForm()

    return render(request, 'accounts/user_login.html', {'form': form})


@anonymous_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def user_signup_view(request):
    """User registration view with SEC sync."""
    if request.method == 'POST':
        form = UserSignupForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Sync to SEC tables
            try:
                sync_user_to_sec(user)
            except Exception as e:
                logger.warning(f'SEC sync failed for new user {user.username}: {e}')

            # Log the action
            AuditLog.log(
                action=AuditLog.ACTION_USER_CREATED,
                target_user=user,
                description=f'New user registered: {user.username}',
                new_state=f'username={user.username}, email={user.email}',
                request=request
            )

            # Send welcome email
            try:
                send_welcome_email.delay(user.id)
            except Exception as e:
                logger.warning(f'Failed to queue welcome email: {e}')

            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('user_login')
    else:
        form = UserSignupForm()

    return render(request, 'accounts/user_signup.html', {'form': form})


@require_POST
@csrf_protect
def user_logout_view(request):
    """User logout view."""
    user = get_current_user(request)

    if user:
        AuditLog.log(
            action=AuditLog.ACTION_LOGOUT,
            actor_user=user,
            target_user=user,
            description='User logged out',
            request=request
        )

    # Clear user session data
    request.session.pop('user_id', None)
    request.session.pop('user_email', None)
    request.session.pop('user_username', None)

    messages.success(request, 'You have been logged out.')
    return redirect('user_login')


# =============================================================================
# Admin Authentication Views
# =============================================================================

@anonymous_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def admin_login_view(request):
    """Admin login view (email based, separate from user login)."""
    if request.method == 'POST':
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            admin = form.cleaned_data['admin']

            # Set session
            request.session['admin_id'] = admin.id
            request.session['admin_email'] = admin.email

            # Update last login
            admin.update_last_login()

            # Log the action
            AuditLog.log(
                action=AuditLog.ACTION_ADMIN_LOGIN,
                actor_admin=admin,
                target_admin=admin,
                description=f'Admin logged in: {admin.email}',
                request=request
            )

            messages.success(request, f'Welcome, {admin.first_name}!')
            return redirect('admin_dashboard')
        else:
            email = request.POST.get('email', '')
            AuditLog.log(
                action=AuditLog.ACTION_LOGIN_FAILED,
                description=f'Failed admin login attempt: {email}',
                request=request
            )
    else:
        form = AdminLoginForm()

    return render(request, 'accounts/admin_login.html', {'form': form})


@require_POST
@csrf_protect
def admin_logout_view(request):
    """Admin logout view."""
    admin = get_current_admin(request)

    if admin:
        AuditLog.log(
            action=AuditLog.ACTION_ADMIN_LOGOUT,
            actor_admin=admin,
            target_admin=admin,
            description='Admin logged out',
            request=request
        )

    # Clear admin session data
    request.session.pop('admin_id', None)
    request.session.pop('admin_email', None)

    messages.success(request, 'You have been logged out.')
    return redirect('admin_login')


# =============================================================================
# Password Reset Views
# =============================================================================

@anonymous_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def forgot_password_view(request):
    """Password reset request view."""
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].lower()

            # Try User first, then Admin
            try:
                user = User.objects.get(email=email, is_active=True)
                reset_token = PasswordResetToken.create_for_user(user)
                AuditLog.log(
                    action=AuditLog.ACTION_PASSWORD_RESET_REQUESTED,
                    target_user=user,
                    description=f'Password reset requested for user: {email}',
                    request=request
                )
                try:
                    send_password_reset_email.delay(user.id, reset_token.token, 'user')
                except Exception as e:
                    logger.warning(f'Failed to queue password reset email: {e}')
            except User.DoesNotExist:
                try:
                    admin = AtlasAdmin.objects.get(email=email, is_active=True)
                    reset_token = PasswordResetToken.create_for_admin(admin)
                    AuditLog.log(
                        action=AuditLog.ACTION_PASSWORD_RESET_REQUESTED,
                        target_admin=admin,
                        description=f'Password reset requested for admin: {email}',
                        request=request
                    )
                    try:
                        send_password_reset_email.delay(admin.id, reset_token.token, 'admin')
                    except Exception as e:
                        logger.warning(f'Failed to queue password reset email: {e}')
                except AtlasAdmin.DoesNotExist:
                    pass  # Don't reveal if email exists

            return render(request, 'accounts/forgot_password_done.html')
    else:
        form = ForgotPasswordForm()

    return render(request, 'accounts/forgot_password.html', {'form': form})


@anonymous_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def reset_password_view(request, token):
    """Password reset view (with token)."""
    reset_token = PasswordResetToken.get_valid_token(token)

    if not reset_token:
        return render(request, 'accounts/reset_password_invalid.html')

    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            account = reset_token.account

            # Update password
            account.set_password(form.cleaned_data['password'])
            account.save()
            if reset_token.user:
                sync_user_password_to_sec(reset_token.user)

            # Mark token as used
            reset_token.use()

            # Log the action
            if reset_token.user:
                AuditLog.log(
                    action=AuditLog.ACTION_PASSWORD_RESET_COMPLETED,
                    target_user=reset_token.user,
                    description='Password reset completed',
                    request=request
                )
            else:
                AuditLog.log(
                    action=AuditLog.ACTION_PASSWORD_RESET_COMPLETED,
                    target_admin=reset_token.admin,
                    description='Admin password reset completed',
                    request=request
                )

            # Send confirmation email
            try:
                account_type = 'user' if reset_token.user else 'admin'
                send_password_changed_email.delay(account.id, account_type)
            except Exception as e:
                logger.warning(f'Failed to queue password changed email: {e}')

            return render(request, 'accounts/reset_password_done.html')
    else:
        form = ResetPasswordForm()

    return render(request, 'accounts/reset_password.html', {'form': form})


# =============================================================================
# User Dashboard Views
# =============================================================================

@user_login_required
def user_dashboard_view(request):
    """Main user dashboard view."""
    user = request.current_user

    # Get user's roles with descriptions
    user_roles = user.roles.all().order_by('name')

    # Get visible messages for this user
    visible_messages = []
    for msg in Message.objects.filter(is_active=True):
        if msg.is_visible_to_user(user):
            # Check if dismissed
            if not MessageDismissal.objects.filter(user=user, message=msg).exists():
                visible_messages.append(msg)

    context = {
        'user': user,
        'user_roles': user_roles,
        'messages_list': visible_messages[:5],  # Show max 5 messages
        'page_title': 'Dashboard',
    }

    return render(request, 'accounts/user_dashboard.html', context)


@user_login_required
def user_roles_view(request):
    """View user's roles with descriptions."""
    user = request.current_user
    user_roles = user.user_roles.select_related('role').order_by('role__name')

    context = {
        'user': user,
        'user_roles': user_roles,
        'page_title': 'My Roles',
    }

    return render(request, 'accounts/user_roles.html', context)


@user_login_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def user_profile_view(request):
    """User profile view and update."""
    user = request.current_user

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            sync_user_profile_to_sec(user)

            AuditLog.log(
                action=AuditLog.ACTION_PROFILE_UPDATED,
                actor_user=user,
                target_user=user,
                description='Profile updated',
                request=request
            )

            messages.success(request, 'Profile updated successfully.')
            return redirect('user_profile')

        messages.error(request, 'Please correct the highlighted profile fields and try again.')
    else:
        form = UserProfileForm(instance=user)

    return render(request, 'accounts/user_profile.html', {
        'user': user,
        'form': form,
        'page_title': 'My Profile',
    })


@user_login_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def user_change_password_view(request):
    """Change password view for users."""
    user = request.current_user

    if request.method == 'POST':
        form = ChangePasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            sync_user_password_to_sec(user)

            AuditLog.log(
                action=AuditLog.ACTION_PASSWORD_CHANGED,
                actor_user=user,
                target_user=user,
                description='Password changed',
                request=request
            )

            try:
                send_password_changed_email.delay(user.id, 'user')
            except Exception as e:
                logger.warning(f'Failed to queue password changed email: {e}')

            messages.success(request, 'Password changed successfully.')
            return redirect('user_dashboard')
    else:
        form = ChangePasswordForm(user)

    return render(request, 'accounts/user_change_password.html', {
        'user': user,
        'form': form,
        'page_title': 'Change Password',
    })


@user_login_required
def user_support_view(request):
    """Support page with contact information."""
    return render(request, 'accounts/user_support.html', {
        'user': request.current_user,
        'page_title': 'Support',
    })


@user_login_required
@require_POST
@csrf_protect
def user_dismiss_message_view(request, message_id):
    """HTMX endpoint to dismiss a message."""
    user = request.current_user
    message = get_object_or_404(Message, id=message_id)

    MessageDismissal.objects.get_or_create(user=user, message=message)

    if request.htmx:
        return HttpResponse('')  # Empty response removes the element
    return redirect('user_dashboard')


# =============================================================================
# Admin Dashboard Views
# =============================================================================

@admin_login_required
def admin_dashboard_view(request):
    """Main admin dashboard view."""
    admin = request.current_admin

    # Stats
    stats = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'total_roles': Role.objects.count(),
        'recent_logins': AuditLog.objects.filter(action=AuditLog.ACTION_LOGIN).count(),
    }

    # Recent activity
    recent_logs = AuditLog.objects.select_related(
        'actor_user', 'actor_admin', 'target_user', 'target_admin'
    ).order_by('-created_at')[:10]

    context = {
        'admin': admin,
        'stats': stats,
        'recent_logs': recent_logs,
        'page_title': 'Admin Dashboard',
    }

    return render(request, 'accounts/admin_dashboard.html', context)


@admin_login_required
def admin_users_view(request):
    """Admin view for managing users."""
    admin = request.current_admin

    # Sync roles from SEC (updates local cache)
    sync_roles_from_sec()

    # Get all users with their roles
    users = User.objects.prefetch_related(
        Prefetch('roles', queryset=Role.objects.order_by('name'))
    ).order_by('-created_at')

    # Search/Filter
    search = request.GET.get('search', '')
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )

    role_filter = request.GET.get('role', '')
    if role_filter:
        users = users.filter(roles__id=role_filter)

    is_active_filter = request.GET.get('is_active', '')
    if is_active_filter == 'true':
        users = users.filter(is_active=True)
    elif is_active_filter == 'false':
        users = users.filter(is_active=False)

    # Pagination
    paginator = Paginator(users.distinct(), 25)
    page = request.GET.get('page', 1)
    users_page = paginator.get_page(page)

    # All roles for filter dropdown and assignment
    all_roles = Role.objects.order_by('name')

    context = {
        'admin': admin,
        'users_list': users_page,
        'all_roles': all_roles,
        'search': search,
        'role_filter': role_filter,
        'is_active_filter': is_active_filter,
        'page_title': 'User Management',
    }

    # Return partial for HTMX requests
    if request.htmx:
        return render(request, 'accounts/partials/users_table.html', context)

    return render(request, 'accounts/admin_users.html', context)


@admin_login_required
def admin_user_detail_view(request, user_id):
    """Admin view for user details and role management."""
    admin = request.current_admin
    target_user = get_object_or_404(User, id=user_id)

    # Get user's roles
    user_roles = target_user.user_roles.select_related('role', 'granted_by').order_by('role__name')

    # Get all available roles for assignment
    all_roles = Role.objects.order_by('name')
    user_role_ids = set(target_user.roles.values_list('id', flat=True))
    available_roles = all_roles.exclude(id__in=user_role_ids)

    context = {
        'admin': admin,
        'target_user': target_user,
        'user_roles': user_roles,
        'available_roles': available_roles,
        'page_title': f'User: {target_user.display_name}',
    }

    return render(request, 'accounts/admin_user_detail.html', context)


@super_admin_required
def admin_roles_view(request):
    """Admin view for managing roles and their descriptions."""
    admin = request.current_admin

    # Sync roles from SEC
    roles = sync_roles_from_sec()

    # Add user counts
    roles_with_counts = roles.annotate(user_count=Count('users'))

    context = {
        'admin': admin,
        'roles': roles_with_counts,
        'page_title': 'Role Management',
    }

    return render(request, 'accounts/admin_roles.html', context)


@super_admin_required
def admin_admins_view(request):
    """
    Admin view for managing administrators.
    Only visible to super_admin and system_superadmin.
    Regular admins cannot see this page.
    """
    admin = request.current_admin

    # Only system_superadmin can see all admins
    # super_admin can see admins but not system_superadmins
    if admin.is_system_superadmin:
        admins = AtlasAdmin.objects.all()
    else:
        # Hide system_superadmins from regular super_admins
        admins = AtlasAdmin.objects.exclude(role=AtlasAdmin.ROLE_SYSTEM_SUPERADMIN)

    admins = admins.order_by('-role', '-created_at')

    # Search
    search = request.GET.get('search', '')
    if search:
        admins = admins.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )

    context = {
        'admin': admin,
        'admins_list': admins,
        'search': search,
        'page_title': 'Administrator Management',
    }

    return render(request, 'accounts/admin_admins.html', context)


@admin_login_required
def admin_audit_log_view(request):
    """Admin view for audit logs."""
    admin = request.current_admin

    logs = AuditLog.objects.select_related(
        'actor_user', 'actor_admin', 'target_user', 'target_admin'
    ).order_by('-created_at')

    # Filters
    action_filter = request.GET.get('action', '')
    if action_filter:
        logs = logs.filter(action=action_filter)

    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        logs = logs.filter(created_at__date__gte=date_from)
    if date_to:
        logs = logs.filter(created_at__date__lte=date_to)

    search = request.GET.get('search', '')
    if search:
        logs = logs.filter(
            Q(actor_email__icontains=search) |
            Q(target_email__icontains=search) |
            Q(description__icontains=search)
        )

    # Pagination
    paginator = Paginator(logs, 50)
    page = request.GET.get('page', 1)
    logs_page = paginator.get_page(page)

    context = {
        'admin': admin,
        'logs': logs_page,
        'action_choices': AuditLog.ACTION_CHOICES,
        'action_filter': action_filter,
        'search': search,
        'date_from': date_from,
        'date_to': date_to,
        'page_title': 'Audit Log',
    }

    return render(request, 'accounts/admin_audit_log.html', context)


@admin_login_required
def admin_messages_view(request):
    """Admin view for managing messages/announcements."""
    admin = request.current_admin

    messages_list = Message.objects.select_related('created_by').order_by('-created_at')

    context = {
        'admin': admin,
        'messages_list': messages_list,
        'message_form': MessageForm(),
        'page_title': 'Messages',
    }

    return render(request, 'accounts/admin_messages.html', context)


@super_admin_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def admin_message_create_view(request):
    """Create new message/announcement."""
    admin = request.current_admin

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.created_by = admin
            message.save()
            form.save_m2m()

            AuditLog.log(
                action=AuditLog.ACTION_MESSAGE_CREATED,
                actor_admin=admin,
                description=f'Message created: {message.title}',
                request=request
            )

            messages.success(request, 'Message created successfully.')
            return redirect('admin_messages')
    else:
        form = MessageForm()

    return render(request, 'accounts/admin_message_form.html', {
        'admin': admin,
        'form': form,
        'page_title': 'Create Message',
    })


# =============================================================================
# Admin - Prefix Management Views
# =============================================================================

@super_admin_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def admin_prefixes_view(request):
    """Admin view for managing prefixes."""
    admin = request.current_admin

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'create':
            name = request.POST.get('name', '').lower().strip()
            display_name = request.POST.get('display_name', '').strip()
            sort_order = int(request.POST.get('sort_order', 0) or 0)

            if not name or not display_name:
                messages.error(request, 'Name and display name are required.')
            elif Prefix.objects.filter(name=name).exists():
                messages.error(request, f'A prefix with name "{name}" already exists.')
            else:
                Prefix.objects.create(
                    name=name, display_name=display_name,
                    sort_order=sort_order, is_active=True
                )
                messages.success(request, f'Prefix "{display_name}" created successfully.')

        elif action == 'update':
            prefix_id = request.POST.get('prefix_id')
            try:
                prefix = Prefix.objects.get(id=prefix_id)
                prefix.display_name = request.POST.get('display_name', '').strip()
                prefix.sort_order = int(request.POST.get('sort_order', 0) or 0)
                prefix.is_active = request.POST.get('is_active') == 'on'
                prefix.save()
                messages.success(request, f'Prefix "{prefix.display_name}" updated.')
            except Prefix.DoesNotExist:
                messages.error(request, 'Prefix not found.')

        elif action == 'delete':
            prefix_id = request.POST.get('prefix_id')
            try:
                prefix = Prefix.objects.get(id=prefix_id)
                user_count = prefix.users.count()
                if user_count > 0:
                    messages.error(request, f'Cannot delete prefix "{prefix.display_name}". {user_count} user(s) are using it.')
                else:
                    display = prefix.display_name
                    prefix.delete()
                    messages.success(request, f'Prefix "{display}" deleted.')
            except Prefix.DoesNotExist:
                messages.error(request, 'Prefix not found.')

        return redirect('admin_prefixes')

    prefixes = Prefix.objects.annotate(user_count=Count('users')).order_by('sort_order', 'display_name')

    context = {
        'admin': admin,
        'prefixes': prefixes,
        'page_title': 'Prefix Management',
    }

    return render(request, 'accounts/admin_prefixes.html', context)


# =============================================================================
# Admin - Category Management Views
# =============================================================================

@super_admin_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def admin_categories_view(request):
    """Admin view for managing categories."""
    admin = request.current_admin

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'create':
            name = request.POST.get('name', '').lower().strip()
            display_name = request.POST.get('display_name', '').strip()
            description = request.POST.get('description', '').strip()
            sort_order = int(request.POST.get('sort_order', 0) or 0)

            if not name or not display_name:
                messages.error(request, 'Name and display name are required.')
            elif Category.objects.filter(name=name).exists():
                messages.error(request, f'A category with name "{name}" already exists.')
            else:
                Category.objects.create(
                    name=name, display_name=display_name,
                    description=description, sort_order=sort_order, is_active=True
                )
                messages.success(request, f'Category "{display_name}" created successfully.')

        elif action == 'update':
            category_id = request.POST.get('category_id')
            try:
                category = Category.objects.get(id=category_id)
                category.display_name = request.POST.get('display_name', '').strip()
                category.description = request.POST.get('description', '').strip()
                category.sort_order = int(request.POST.get('sort_order', 0) or 0)
                category.is_active = request.POST.get('is_active') == 'on'
                category.save()
                messages.success(request, f'Category "{category.display_name}" updated.')
            except Category.DoesNotExist:
                messages.error(request, 'Category not found.')

        elif action == 'delete':
            category_id = request.POST.get('category_id')
            try:
                category = Category.objects.get(id=category_id)
                user_count = category.users.count()
                if user_count > 0:
                    messages.error(request, f'Cannot delete category "{category.display_name}". {user_count} user(s) are using it.')
                else:
                    display = category.display_name
                    category.delete()
                    messages.success(request, f'Category "{display}" deleted.')
            except Category.DoesNotExist:
                messages.error(request, 'Category not found.')

        return redirect('admin_categories')

    categories = Category.objects.annotate(user_count=Count('users')).order_by('sort_order', 'display_name')

    context = {
        'admin': admin,
        'categories': categories,
        'page_title': 'Category Management',
    }

    return render(request, 'accounts/admin_categories.html', context)


# =============================================================================
# HTMX/AJAX Views for Async Operations
# =============================================================================

@super_admin_required
@require_POST
@csrf_protect
def htmx_grant_role_view(request):
    """HTMX endpoint to grant a role to a user."""
    admin = request.current_admin

    form = UserRoleAssignForm(request.POST)
    if form.is_valid():
        user = form.cleaned_data['user']
        role = form.cleaned_data['role']

        # Create local UserRole
        user_role, created = UserRole.objects.get_or_create(
            user=user,
            role=role,
            defaults={'granted_by': admin, 'origin': UserRole.ORIGIN_ATLAS}
        )

        if created:
            # Sync to SEC
            grant_role_to_sec(user, role.name)

            # Log
            AuditLog.log(
                action=AuditLog.ACTION_ROLE_GRANTED,
                actor_admin=admin,
                target_user=user,
                description=f'Role granted: {role.name}',
                new_state=f'role={role.name}',
                request=request
            )

            return HttpResponse(_render_user_roles_modal(admin, user))
        else:
            return HttpResponse(_render_user_roles_modal(admin, user))

    return HttpResponse('<div class="toast-message error">Invalid request</div>', status=400)


@super_admin_required
@require_POST
@csrf_protect
def htmx_revoke_role_view(request):
    """HTMX endpoint to revoke a role from a user."""
    admin = request.current_admin

    form = UserRoleRevokeForm(request.POST)
    if form.is_valid():
        user = form.cleaned_data['user']
        role = form.cleaned_data['role']

        # Delete local UserRole
        deleted_count, _ = UserRole.objects.filter(user=user, role=role).delete()

        if deleted_count > 0:
            # Sync to SEC
            revoke_role_from_sec(user, role.name)

            # Log
            AuditLog.log(
                action=AuditLog.ACTION_ROLE_REVOKED,
                actor_admin=admin,
                target_user=user,
                description=f'Role revoked: {role.name}',
                previous_state=f'role={role.name}',
                request=request
            )

            return HttpResponse(_render_user_roles_modal(admin, user))
        else:
            return HttpResponse(_render_user_roles_modal(admin, user))

    return HttpResponse('<div class="toast-message error">Invalid request</div>', status=400)


@super_admin_required
@require_POST
@csrf_protect
def htmx_bulk_grant_roles_view(request):
    """HTMX endpoint for bulk role assignment."""
    admin = request.current_admin

    form = BulkRoleAssignForm(request.POST)
    if form.is_valid():
        users = form.cleaned_data['user_ids']
        roles = form.cleaned_data['role_ids']

        granted_count = 0
        for user in users:
            for role in roles:
                user_role, created = UserRole.objects.get_or_create(
                    user=user,
                    role=role,
                    defaults={'granted_by': admin, 'origin': UserRole.ORIGIN_ATLAS}
                )
                if created:
                    grant_role_to_sec(user, role.name)
                    granted_count += 1

        # Log bulk operation
        AuditLog.log(
            action=AuditLog.ACTION_ROLE_BULK_GRANT,
            actor_admin=admin,
            description=f'Bulk role grant: {granted_count} assignments to {len(users)} users',
            new_state=f'users={len(users)}, roles={len(roles)}, granted={granted_count}',
            request=request
        )

        return HttpResponse(
            f'<div class="toast-message success">Granted {granted_count} role assignments</div>'
        )

    return HttpResponse('<div class="toast-message error">Invalid request</div>', status=400)




@super_admin_required
@require_GET
def htmx_sync_roles_view(request):
    """HTMX endpoint to sync roles from SEC and refresh table rows."""
    roles = sync_roles_from_sec().annotate(user_count=Count('users'))
    html = render_to_string('accounts/partials/admin_roles_rows.html', {
        'roles': roles,
        'admin': request.current_admin,
    })
    return HttpResponse(html)


@super_admin_required
@require_GET
def htmx_role_users_view(request, role_id):
    """HTMX endpoint to show users assigned to a specific role."""
    role = get_object_or_404(Role, id=role_id)
    users = role.users.order_by('first_name', 'last_name', 'username')
    html = render_to_string('accounts/partials/role_users_modal_content.html', {
        'role': role,
        'users': users,
    })
    return HttpResponse(html)

@super_admin_required
@require_POST
@csrf_protect
def htmx_update_role_description_view(request):
    """HTMX endpoint to update role description."""
    admin = request.current_admin

    form = RoleDescriptionForm(request.POST)
    if form.is_valid():
        role = form.save()
        role = Role.objects.annotate(user_count=Count('users')).get(pk=role.pk)
        html = render_to_string('accounts/partials/admin_role_row.html', {
            'role': role,
            'admin': admin,
        })
        return HttpResponse(html)

    return HttpResponse('<div class="toast-message error">Invalid request</div>', status=400)


@super_admin_required
@require_POST
@csrf_protect
def htmx_toggle_user_active_view(request, user_id):
    """HTMX endpoint to toggle user active status."""
    admin = request.current_admin
    user = get_object_or_404(User, id=user_id)

    old_status = user.is_active
    user.is_active = not user.is_active
    user.save()

    action = AuditLog.ACTION_USER_ACTIVATED if user.is_active else AuditLog.ACTION_USER_DEACTIVATED
    AuditLog.log(
        action=action,
        actor_admin=admin,
        target_user=user,
        description=f"User {'activated' if user.is_active else 'deactivated'}",
        previous_state=f'is_active={old_status}',
        new_state=f'is_active={user.is_active}',
        request=request
    )

    status_text = 'activated' if user.is_active else 'deactivated'
    return HttpResponse(
        f'<div class="toast-message success">User {user.display_name} {status_text}</div>'
    )


@admin_login_required
@require_GET
def htmx_search_users_view(request):
    """HTMX endpoint for searching users."""
    search = request.GET.get('search', '')

    users = User.objects.prefetch_related('roles').order_by('-created_at')

    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )[:20]
    else:
        users = users[:20]

    html = render_to_string('accounts/partials/users_search_results.html', {
        'users': users,
        'admin': request.current_admin,
    })

    return HttpResponse(html)


@admin_login_required
@require_GET
def htmx_user_roles_view(request, user_id):
    """HTMX endpoint to get user's roles for modal display."""
    user = get_object_or_404(User, id=user_id)
    user_roles = user.user_roles.select_related('role', 'granted_by').order_by('role__name')
    all_roles = Role.objects.order_by('name')
    user_role_ids = set(user.roles.values_list('id', flat=True))
    available_roles = all_roles.exclude(id__in=user_role_ids)

    html = render_to_string('accounts/partials/user_roles_modal.html', {
        'target_user': user,
        'user_roles': user_roles,
        'available_roles': available_roles,
        'admin': request.current_admin,
    })

    return HttpResponse(html)


# =============================================================================
# Admin Creation (System Superadmin Only)
# =============================================================================

@system_superadmin_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def admin_create_admin_view(request):
    """Create new admin account (system_superadmin only)."""
    admin = request.current_admin

    if request.method == 'POST':
        form = AdminCreateForm(request.POST, actor=admin)
        if form.is_valid():
            new_admin = form.save()

            AuditLog.log(
                action=AuditLog.ACTION_ADMIN_CREATED,
                actor_admin=admin,
                target_admin=new_admin,
                description=f'Admin created: {new_admin.email}',
                new_state=f'role={new_admin.role}',
                request=request
            )

            messages.success(request, f'Admin account created for {new_admin.email}.')
            return redirect('admin_admins')
    else:
        form = AdminCreateForm(actor=admin)

    return render(request, 'accounts/admin_create_admin.html', {
        'admin': admin,
        'form': form,
        'page_title': 'Create Administrator',
    })


@system_superadmin_required
@require_POST
@csrf_protect
def admin_change_admin_role_view(request):
    """Change admin role (system_superadmin only)."""
    admin = request.current_admin

    form = AdminRoleChangeForm(request.POST, actor=admin)
    if form.is_valid():
        target_admin, old_role, new_role = form.save()

        AuditLog.log(
            action=AuditLog.ACTION_ADMIN_ROLE_CHANGED,
            actor_admin=admin,
            target_admin=target_admin,
            description=f'Admin role changed from {old_role} to {new_role}',
            previous_state=f'role={old_role}',
            new_state=f'role={new_role}',
            request=request
        )

        messages.success(request, f'Admin role updated to {target_admin.role_display}.')
    else:
        for error in form.non_field_errors():
            messages.error(request, error)

    return redirect('admin_admins')


# =============================================================================
# Admin Profile
# =============================================================================

@admin_login_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def admin_profile_view(request):
    """Admin profile view and update."""
    admin = request.current_admin

    if request.method == 'POST':
        form = AdminProfileForm(request.POST, instance=admin)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('admin_profile')
    else:
        form = AdminProfileForm(instance=admin)

    return render(request, 'accounts/admin_profile.html', {
        'admin': admin,
        'form': form,
        'page_title': 'My Profile',
    })


@admin_login_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def admin_change_password_view(request):
    """Change password view for admins."""
    admin = request.current_admin

    if request.method == 'POST':
        form = ChangePasswordForm(admin, request.POST)
        if form.is_valid():
            form.save()

            AuditLog.log(
                action=AuditLog.ACTION_PASSWORD_CHANGED,
                actor_admin=admin,
                target_admin=admin,
                description='Admin password changed',
                request=request
            )

            try:
                send_password_changed_email.delay(admin.id, 'admin')
            except Exception as e:
                logger.warning(f'Failed to queue password changed email: {e}')

            messages.success(request, 'Password changed successfully.')
            return redirect('admin_dashboard')
    else:
        form = ChangePasswordForm(admin)

    return render(request, 'accounts/admin_change_password.html', {
        'admin': admin,
        'form': form,
        'page_title': 'Change Password',
    })


# =============================================================================
# Health Check & Utilities
# =============================================================================

def health_check(request):
    """Health check endpoint for container orchestration."""
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        return JsonResponse({'status': 'healthy'})
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JsonResponse({'status': 'unhealthy', 'error': str(e)}, status=500)


def handler404(request, exception):
    """Custom 404 page."""
    return render(request, 'errors/404.html', status=404)


def handler500(request):
    """Custom 500 page."""
    return render(request, 'errors/500.html', status=500)


# =============================================================================
# Redirect Views (for backwards compatibility)
# =============================================================================

def login_redirect_view(request):
    """Redirect /login/ to user login."""
    return redirect('user_login')


def signup_redirect_view(request):
    """Redirect /signup/ to user signup."""
    return redirect('user_signup')


def dashboard_redirect_view(request):
    """Redirect /dashboard/ based on session type."""
    if get_current_admin(request):
        return redirect('admin_dashboard')
    return redirect('user_dashboard')
