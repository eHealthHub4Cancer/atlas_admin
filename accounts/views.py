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
import os
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.decorators.csrf import csrf_protect
from django.db.models import Count, Q, Prefetch, Case, When, IntegerField, Sum
from django.db.utils import DatabaseError
from django.core.paginator import Paginator
from django.template.loader import render_to_string

from django.utils import timezone
from .models import User, AtlasAdmin, Role, Category, Prefix, UserRole, Message, MessageDismissal, AuditLog, PasswordResetToken, Notification, UserNotification
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

DEFAULT_SIGNUP_ROLE = os.environ.get('DEFAULT_SIGNUP_ROLE', 'guest').strip().lower()


def _assign_default_signup_role(user):
    """Assign a default role to new signup users (without exposing role in signup form)."""
    role = Role.objects.filter(is_active=True, name__iexact=DEFAULT_SIGNUP_ROLE).first()
    if role is None:
        role = Role.objects.filter(is_active=True).order_by('sort_order', 'name').first()

    if role is None:
        logger.warning('No active role available to assign for signup user %s', user.username)
        return None

    UserRole.objects.get_or_create(
        user=user,
        role=role,
        defaults={'origin': UserRole.ORIGIN_SYSTEM},
    )

    try:
        grant_role_to_sec(user, role.name)
    except Exception as e:
        logger.warning('Failed to grant default role %s to SEC user %s: %s', role.name, user.username, e)

    return role


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
                sync_user_to_sec(user, raw_password=form.cleaned_data['password'])
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

            assigned_role = _assign_default_signup_role(user)

            # Send welcome email
            try:
                send_welcome_email.delay(user.id)
            except Exception as e:
                logger.warning(f'Failed to queue welcome email: {e}')

            if assigned_role:
                messages.success(request, f'Account created successfully! Please log in. Default role assigned: {assigned_role.name}.')
            else:
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
                sync_user_password_to_sec(reset_token.user, raw_password=form.cleaned_data['password'])

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
    try:
        user_roles = list(user.roles.all().order_by('name'))
    except Exception as e:
        logger.warning('Failed loading roles for %s: %s', user.username, e)
        user_roles = []

    # Get visible messages for this user
    visible_messages = []
    try:
        for msg in Message.objects.filter(is_active=True):
            if msg.is_visible_to_user(user):
                # Check if dismissed
                if not MessageDismissal.objects.filter(user=user, message=msg).exists():
                    visible_messages.append(msg)
    except Exception as e:
        logger.warning('Failed loading announcements for %s: %s', user.username, e)

    try:
        recent_notifications = list(UserNotification.objects.filter(user=user).select_related('notification').order_by('-created_at')[:5])
    except Exception as e:
        logger.warning('Failed loading notifications for %s: %s', user.username, e)
        recent_notifications = []

    profile_fields = {
        'First name': bool(user.first_name and user.first_name.strip()),
        'Last name': bool(user.last_name and user.last_name.strip()),
        'Email': bool(user.email and user.email.strip()),
        'Affiliation': bool(user.affiliation and user.affiliation.strip()),
        'Prefix': bool(user.prefix_id),
        'Category': bool(user.category_id),
    }
    profile_completed = sum(profile_fields.values())
    profile_total = len(profile_fields)
    profile_completion = int((profile_completed / profile_total) * 100) if profile_total else 0

    context = {
        'user': user,
        'user_roles': user_roles,
        'messages_list': visible_messages[:5],  # Show max 5 messages
        'notifications_list': recent_notifications,
        'profile_completion': profile_completion,
        'profile_missing_fields': [label for label, done in profile_fields.items() if not done],
        'page_title': 'Dashboard',
    }

    return render(request, 'accounts/user_dashboard.html', context)


@user_login_required
def user_audit_log_view(request):
    """User view for own audit logs only."""
    user = request.current_user
    logs = AuditLog.objects.filter(
        Q(actor_user=user) | Q(target_user=user)
    ).select_related('actor_user', 'actor_admin', 'target_user', 'target_admin').distinct().order_by('-created_at')

    action_filter = request.GET.get('action', '')
    if action_filter:
        logs = logs.filter(action=action_filter)

    search = request.GET.get('search', '')
    if search:
        logs = logs.filter(
            Q(description__icontains=search) |
            Q(action__icontains=search)
        )

    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        logs = logs.filter(created_at__date__gte=date_from)
    if date_to:
        logs = logs.filter(created_at__date__lte=date_to)

    paginator = Paginator(logs, 5)
    page = request.GET.get('page', 1)
    logs_page = paginator.get_page(page)

    return render(request, 'accounts/user_audit_log.html', {
        'user': user,
        'logs': logs_page,
        'action_choices': AuditLog.ACTION_CHOICES,
        'action_filter': action_filter,
        'search': search,
        'date_from': date_from,
        'date_to': date_to,
        'page_title': 'My Audit Log',
    })


@user_login_required
def user_roles_view(request):
    """View user's roles with descriptions."""
    user = request.current_user
    user_roles = user.user_roles.select_related('role').order_by('role__name')

    # Search
    search = request.GET.get('search', '')
    if search:
        user_roles = user_roles.filter(
            Q(role__name__icontains=search) |
            Q(role__description__icontains=search)
        )

    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        user_roles = user_roles.filter(role__is_active=True)
    elif status_filter == 'inactive':
        user_roles = user_roles.filter(role__is_active=False)

    # Pagination
    paginator = Paginator(user_roles, 10)
    page = request.GET.get('page', 1)
    user_roles_page = paginator.get_page(page)

    context = {
        'user': user,
        'user_roles': user_roles_page,
        'search': search,
        'status_filter': status_filter,
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
            sync_user_password_to_sec(user, raw_password=form.cleaned_data['new_password'])

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
    try:
        stats = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'total_roles': Role.objects.count(),
            'recent_logins': AuditLog.objects.filter(action=AuditLog.ACTION_LOGIN).count(),
        }
    except Exception as e:
        logger.warning('Failed loading dashboard stats: %s', e)
        stats = {'total_users': 0, 'active_users': 0, 'total_roles': 0, 'recent_logins': 0}

    # Recent activity
    try:
        recent_logs = list(AuditLog.objects.select_related(
            'actor_user', 'actor_admin', 'target_user', 'target_admin'
        ).order_by('-created_at')[:10])
    except Exception as e:
        logger.warning('Failed loading recent activity: %s', e)
        recent_logs = []

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
    paginator = Paginator(users.distinct(), 10)
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

    # Search
    search = request.GET.get('search', '')
    if search:
        roles_with_counts = roles_with_counts.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )

    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        roles_with_counts = roles_with_counts.filter(is_active=True)
    elif status_filter == 'inactive':
        roles_with_counts = roles_with_counts.filter(is_active=False)

    # Pagination
    paginator = Paginator(roles_with_counts, 10)
    page = request.GET.get('page', 1)
    roles_page = paginator.get_page(page)

    context = {
        'admin': admin,
        'roles': roles_page,
        'search': search,
        'status_filter': status_filter,
        'page_title': 'Role Management',
    }

    if request.headers.get('HX-Request'):
        return render(request, 'accounts/admin_roles.html', context)

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
        'admins': admins,
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
    paginator = Paginator(logs, 5)
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

    try:
        messages_list = list(Message.objects.select_related('created_by').order_by('-created_at'))
    except Exception as e:
        logger.warning('Failed loading admin messages for %s: %s', admin.email, e)
        messages.error(request, 'Announcements are temporarily unavailable. Please try again shortly.')
        messages_list = []

    context = {
        'admin': admin,
        'messages_list': messages_list,
        'roles': Role.objects.filter(is_active=True).order_by('name'),
        'users': User.objects.filter(is_active=True).order_by('username'),
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
            if not message.starts_at:
                message.starts_at = timezone.now()
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
            # If form is invalid, redirect back with error
            messages.error(request, 'Failed to create message. Please check the form fields.')
            return redirect('admin_messages')

    return redirect('admin_messages')


@admin_login_required
@require_http_methods(["GET", "POST"])
def admin_message_edit_view(request, message_id):
    """Edit an existing announcement."""
    admin = request.current_admin
    message_obj = get_object_or_404(Message, id=message_id)

    if request.method == 'POST':
        form = MessageForm(request.POST, instance=message_obj)
        if form.is_valid():
            updated = form.save()
            AuditLog.log(
                action=AuditLog.ACTION_MESSAGE_UPDATED,
                actor_admin=admin,
                description=f'Message updated: {updated.title}',
                request=request,
            )
            messages.success(request, 'Announcement updated successfully.')
            return redirect('admin_messages')
    else:
        form = MessageForm(instance=message_obj)

    return render(request, 'accounts/admin_message_edit.html', {
        'admin': admin,
        'message_obj': message_obj,
        'form': form,
        'page_title': f'Edit Announcement: {message_obj.title}',
    })


@admin_login_required
@require_POST
def admin_message_delete_view(request, message_id):
    """Delete an announcement."""
    admin = request.current_admin
    message_obj = get_object_or_404(Message, id=message_id)
    title = message_obj.title
    message_obj.delete()
    AuditLog.log(
        action=AuditLog.ACTION_MESSAGE_UPDATED,
        actor_admin=admin,
        description=f'Message deleted: {title}',
        request=request,
    )
    messages.success(request, 'Announcement deleted successfully.')
    return redirect('admin_messages')


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
            grant_role_to_sec(user, role.name, create_missing_role=False)

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
                    grant_role_to_sec(user, role.name, create_missing_role=False)
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
# Notification Views
# =============================================================================

@user_login_required
def user_notifications_view(request):
    """User's notification list."""
    user = request.current_user

    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')

    try:
        user_notifs = UserNotification.objects.filter(user=user).select_related(
            'notification', 'notification__created_by'
        )

        if search:
            user_notifs = user_notifs.filter(
                Q(notification__title__icontains=search) |
                Q(notification__content__icontains=search)
            )

        if status_filter == 'unread':
            user_notifs = user_notifs.filter(is_read=False)
        elif status_filter == 'read':
            user_notifs = user_notifs.filter(is_read=True)

        paginator = Paginator(user_notifs, 10)
        page = request.GET.get('page', 1)
        notifs_page = paginator.get_page(page)

        unread_count = UserNotification.objects.filter(user=user, is_read=False).count()
    except Exception as e:
        logger.warning('Failed loading notifications for %s: %s', user.username, e)
        messages.error(
            request,
            'Notifications are temporarily unavailable. If this persists, run pending migrations and retry.'
        )
        notifs_page = Paginator(UserNotification.objects.none(), 10).get_page(1)
        unread_count = 0

    context = {
        'user': user,
        'notifications': notifs_page,
        'search': search,
        'status_filter': status_filter,
        'unread_count': unread_count,
        'page_title': 'Notifications',
    }
    return render(request, 'accounts/user_notifications.html', context)


@user_login_required
@require_POST
def user_mark_notification_read_view(request, notification_id):
    """Mark a notification as read."""
    user = request.current_user
    try:
        user_notif = get_object_or_404(UserNotification, id=notification_id, user=user)
        user_notif.is_read = True
        user_notif.read_at = timezone.now()
        user_notif.save(update_fields=['is_read', 'read_at'])
    except DatabaseError as e:
        logger.warning('Failed marking notification %s as read for %s: %s', notification_id, user.username, e)
        messages.error(
            request,
            'Unable to update notification right now. If this persists, run pending migrations and retry.'
        )
        if request.headers.get('HX-Request'):
            return HttpResponse(
                '<span class="badge bg-danger">Error</span>',
                content_type='text/html',
                status=500
            )
        return redirect('user_notifications')

    if request.headers.get('HX-Request'):
        return HttpResponse(
            f'<span class="badge bg-secondary">Read</span>',
            content_type='text/html'
        )
    return redirect('user_notifications')


@user_login_required
@require_POST
def user_mark_all_notifications_read_view(request):
    """Mark all notifications as read."""
    user = request.current_user
    try:
        UserNotification.objects.filter(user=user, is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        messages.success(request, 'All notifications marked as read.')
    except DatabaseError as e:
        logger.warning('Failed marking all notifications as read for %s: %s', user.username, e)
        messages.error(
            request,
            'Unable to update notifications right now. If this persists, run pending migrations and retry.'
        )
    return redirect('user_notifications')


@user_login_required
def user_notification_count_view(request):
    """Get unread notification count (for AJAX polling)."""
    user = request.current_user
    try:
        count = UserNotification.objects.filter(user=user, is_read=False).count()
    except Exception as e:
        logger.warning('Failed counting notifications for %s: %s', user.username, e)
        count = 0
    if request.headers.get('HX-Request'):
        return HttpResponse(
            f'<span class="badge bg-danger rounded-pill">{count}</span>',
            content_type='text/html'
        )
    return JsonResponse({'count': count})


@super_admin_required
@require_http_methods(["GET", "POST"])
def admin_notifications_view(request):
    """Admin view for managing notifications."""
    admin = request.current_admin

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        priority = request.POST.get('priority', 'normal')
        tag = request.POST.get('tag', Notification.TAG_INFO)
        target_type = request.POST.get('target_type', 'all')
        target_role_ids = request.POST.getlist('target_roles')
        target_user_ids = request.POST.getlist('target_users')

        if not title or not content:
            messages.error(request, 'Title and content are required.')
            return redirect('admin_notifications')

        try:
            notification = Notification.objects.create(
                title=title,
                content=content,
                priority=priority,
                tag=tag,
                target_all_users=(target_type == 'all'),
                created_by=admin,
            )

            if target_type == 'roles' and target_role_ids:
                notification.target_roles.set(target_role_ids)
            elif target_type == 'users' and target_user_ids:
                notification.target_users.set(target_user_ids)

            # Create UserNotification entries for all targeted users
            target_users = notification.get_target_users()
            user_notifications = [
                UserNotification(user=u, notification=notification)
                for u in target_users
            ]
            UserNotification.objects.bulk_create(user_notifications, ignore_conflicts=True)
        except DatabaseError as e:
            logger.warning('Failed creating notification for %s: %s', admin.email, e)
            messages.error(request, 'Unable to send notification right now. Please try again shortly.')
            return redirect('admin_notifications')

        AuditLog.log(
            action=AuditLog.ACTION_MESSAGE_CREATED,
            actor_admin=admin,
            description=f'Notification sent: "{title}" to {len(user_notifications)} user(s)',
            request=request
        )

        messages.success(request, f'Notification sent to {len(user_notifications)} user(s).')
        return redirect('admin_notifications')

    # List existing notifications
    try:
        notifications = Notification.objects.select_related('created_by').prefetch_related('target_roles').annotate(
            read_count=Sum(
                Case(
                    When(user_notifications__is_read=True, then=1),
                    default=0,
                    output_field=IntegerField(),
                )
            )
        )

        search = request.GET.get('search', '')
        if search:
            notifications = notifications.filter(
                Q(title__icontains=search) | Q(content__icontains=search)
            )

        paginator = Paginator(notifications, 10)
        page = request.GET.get('page', 1)
        notifs_page = paginator.get_page(page)
    except Exception as e:
        logger.warning('Failed loading notifications for %s: %s', admin.email, e)
        messages.error(request, 'Notifications are temporarily unavailable. Please try again shortly.')
        search = request.GET.get('search', '')
        notifs_page = Paginator(Notification.objects.none(), 10).get_page(1)

    try:
        active_roles = list(Role.objects.filter(is_active=True).order_by('name'))
    except Exception as e:
        logger.warning('Failed loading active roles for notifications page: %s', e)
        active_roles = []

    try:
        active_users = list(User.objects.filter(is_active=True).order_by('username'))
    except Exception as e:
        logger.warning('Failed loading active users for notifications page: %s', e)
        active_users = []

    context = {
        'admin': admin,
        'notifications': notifs_page,
        'search': search,
        'roles': active_roles,
        'users': active_users,
        'page_title': 'Notifications',
    }
    return render(request, 'accounts/admin_notifications.html', context)


@super_admin_required
@require_http_methods(["GET", "POST"])
def admin_notification_edit_view(request, notification_id):
    """Edit an existing notification."""
    admin = request.current_admin
    notification = get_object_or_404(Notification, id=notification_id)

    if request.method == 'POST':
        notification.title = request.POST.get('title', notification.title).strip()
        notification.content = request.POST.get('content', notification.content).strip()
        notification.priority = request.POST.get('priority', notification.priority)
        notification.tag = request.POST.get('tag', notification.tag)
        notification.save()
        messages.success(request, 'Notification updated.')
        return redirect('admin_notifications')

    context = {
        'admin': admin,
        'notification': notification,
        'page_title': f'Edit Notification: {notification.title}',
    }
    return render(request, 'accounts/admin_notification_edit.html', context)


@super_admin_required
@require_POST
def admin_notification_delete_view(request, notification_id):
    """Delete a notification."""
    notification = get_object_or_404(Notification, id=notification_id)
    notification.delete()
    messages.success(request, 'Notification deleted.')
    return redirect('admin_notifications')


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
