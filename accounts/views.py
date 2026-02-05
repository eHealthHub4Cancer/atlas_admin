"""
Atlas Config - Views

Authentication, dashboard, and admin views with strict RBAC enforcement.
"""

import logging
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_protect
from django.db.models import Count, Q
from django.core.paginator import Paginator

from .models import User, AuditLog, PasswordResetToken
from .forms import (
    LoginForm, SignupForm, ForgotPasswordForm, ResetPasswordForm,
    ChangePasswordForm, ProfileForm, UserEditForm, RoleChangeForm
)
from .tasks import (
    send_welcome_email, send_password_reset_email,
    send_promotion_email, send_demotion_email, send_password_changed_email
)

logger = logging.getLogger(__name__)


# =============================================================================
# Decorators for Authentication and Authorization
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


def login_required(view_func):
    """Decorator to require authentication."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            messages.warning(request, 'Please log in to access this page.')
            return redirect('login')
        request.user = user
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Decorator to require admin or super_admin role."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            messages.warning(request, 'Please log in to access this page.')
            return redirect('login')
        if not user.is_admin:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('dashboard')
        request.user = user
        return view_func(request, *args, **kwargs)
    return wrapper


def super_admin_required(view_func):
    """Decorator to require super_admin role."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            messages.warning(request, 'Please log in to access this page.')
            return redirect('login')
        if not user.is_super_admin:
            messages.error(request, 'Only Super Admins can perform this action.')
            return redirect('dashboard')
        request.user = user
        return view_func(request, *args, **kwargs)
    return wrapper


def anonymous_required(view_func):
    """Decorator to redirect authenticated users."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = get_current_user(request)
        if user:
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


# =============================================================================
# Authentication Views
# =============================================================================

@anonymous_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def login_view(request):
    """User login view."""
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']

            # Set session
            request.session['user_id'] = user.id
            request.session['user_email'] = user.email

            # Update last login
            user.update_last_login()

            # Log the action
            AuditLog.log(
                action=AuditLog.ACTION_LOGIN,
                actor=user,
                target=user,
                description=f'User logged in',
                request=request
            )

            messages.success(request, f'Welcome back, {user.first_name}!')
            return redirect('dashboard')
        else:
            # Log failed login attempt
            email = request.POST.get('email', '')
            AuditLog.log(
                action=AuditLog.ACTION_LOGIN_FAILED,
                description=f'Failed login attempt for email: {email}',
                request=request
            )
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


@anonymous_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def signup_view(request):
    """User registration view."""
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Log the action
            AuditLog.log(
                action=AuditLog.ACTION_USER_CREATED,
                target=user,
                description=f'New user registered: {user.email}',
                new_state=f'role={user.role}',
                request=request
            )

            # Send welcome email
            try:
                send_welcome_email.delay(user.id)
            except Exception as e:
                logger.warning(f'Failed to queue welcome email: {e}')

            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('login')
    else:
        form = SignupForm()

    return render(request, 'accounts/signup.html', {'form': form})


@require_POST
@csrf_protect
def logout_view(request):
    """User logout view."""
    user = get_current_user(request)

    if user:
        AuditLog.log(
            action=AuditLog.ACTION_LOGOUT,
            actor=user,
            target=user,
            description='User logged out',
            request=request
        )

    request.session.flush()
    messages.success(request, 'You have been logged out.')
    return redirect('login')


@anonymous_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def forgot_password_view(request):
    """Password reset request view."""
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].lower()

            try:
                user = User.objects.get(email=email, is_active=True)

                # Create reset token
                reset_token = PasswordResetToken.create_for_user(user)

                # Log the action
                AuditLog.log(
                    action=AuditLog.ACTION_PASSWORD_RESET_REQUESTED,
                    target=user,
                    description=f'Password reset requested for {email}',
                    request=request
                )

                # Send email
                try:
                    send_password_reset_email.delay(user.id, reset_token.token)
                except Exception as e:
                    logger.warning(f'Failed to queue password reset email: {e}')

            except User.DoesNotExist:
                # Don't reveal if email exists
                pass

            # Always show success to prevent email enumeration
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
            user = reset_token.user

            # Update password
            user.set_password(form.cleaned_data['password'])
            user.save()

            # Mark token as used
            reset_token.use()

            # Log the action
            AuditLog.log(
                action=AuditLog.ACTION_PASSWORD_RESET_COMPLETED,
                target=user,
                description='Password reset completed',
                request=request
            )

            # Send confirmation email
            try:
                send_password_changed_email.delay(user.id)
            except Exception as e:
                logger.warning(f'Failed to queue password changed email: {e}')

            return render(request, 'accounts/reset_password_done.html')
    else:
        form = ResetPasswordForm()

    return render(request, 'accounts/reset_password.html', {'form': form})


# =============================================================================
# Dashboard Views
# =============================================================================

@login_required
def dashboard_view(request):
    """Main dashboard view."""
    user = request.user

    context = {
        'user': user,
        'page_title': 'Dashboard',
    }

    # Add admin stats if user is admin
    if user.is_admin:
        context['stats'] = {
            'total_users': User.objects.filter(role=User.ROLE_USER).count(),
            'total_admins': User.objects.filter(role__in=[User.ROLE_ADMIN, User.ROLE_SUPER_ADMIN]).count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'recent_logins': AuditLog.objects.filter(action=AuditLog.ACTION_LOGIN).count(),
        }

    return render(request, 'accounts/dashboard.html', context)


@login_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def profile_view(request):
    """User profile view and update."""
    user = request.user

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()

            AuditLog.log(
                action=AuditLog.ACTION_PROFILE_UPDATED,
                actor=user,
                target=user,
                description='Profile updated',
                request=request
            )

            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=user)

    return render(request, 'accounts/profile.html', {
        'user': user,
        'form': form,
        'page_title': 'My Profile',
    })


@login_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def change_password_view(request):
    """Change password view for authenticated users."""
    user = request.user

    if request.method == 'POST':
        form = ChangePasswordForm(user, request.POST)
        if form.is_valid():
            form.save()

            AuditLog.log(
                action=AuditLog.ACTION_PASSWORD_CHANGED,
                actor=user,
                target=user,
                description='Password changed',
                request=request
            )

            # Send confirmation email
            try:
                send_password_changed_email.delay(user.id)
            except Exception as e:
                logger.warning(f'Failed to queue password changed email: {e}')

            messages.success(request, 'Password changed successfully.')
            return redirect('dashboard')
    else:
        form = ChangePasswordForm(user)

    return render(request, 'accounts/change_password.html', {
        'user': user,
        'form': form,
        'page_title': 'Change Password',
    })


# =============================================================================
# Admin Views
# =============================================================================

@admin_required
def admin_users_view(request):
    """Admin view for managing regular users."""
    user = request.user

    # Only show users with role='user'
    users = User.objects.filter(role=User.ROLE_USER).order_by('-created_at')

    # Search
    search = request.GET.get('search', '')
    if search:
        users = users.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )

    return render(request, 'accounts/admin/users.html', {
        'user': user,
        'users_list': users,
        'search': search,
        'page_title': 'Users',
    })


@admin_required
def admin_admins_view(request):
    """Admin view for managing administrators."""
    user = request.user

    # Show admin and super_admin users
    admins = User.objects.filter(
        role__in=[User.ROLE_ADMIN, User.ROLE_SUPER_ADMIN]
    ).order_by('-role', '-created_at')

    # Search
    search = request.GET.get('search', '')
    if search:
        admins = admins.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )

    return render(request, 'accounts/admin/admins.html', {
        'user': user,
        'admins_list': admins,
        'search': search,
        'page_title': 'Administrators',
    })


@admin_required
def admin_user_detail_view(request, user_id):
    """Admin view for user details."""
    current_user = request.user
    target_user = get_object_or_404(User, id=user_id)

    if request.method == 'POST' and current_user.is_super_admin:
        form = UserEditForm(request.POST, instance=target_user)
        if form.is_valid():
            old_active = target_user.is_active
            form.save()

            # Log changes
            if old_active != target_user.is_active:
                action = AuditLog.ACTION_USER_ACTIVATED if target_user.is_active else AuditLog.ACTION_USER_DEACTIVATED
                AuditLog.log(
                    action=action,
                    actor=current_user,
                    target=target_user,
                    description=f"User {'activated' if target_user.is_active else 'deactivated'}",
                    previous_state=f'is_active={old_active}',
                    new_state=f'is_active={target_user.is_active}',
                    request=request
                )

            messages.success(request, 'User updated successfully.')
            return redirect('admin_user_detail', user_id=user_id)
    else:
        form = UserEditForm(instance=target_user)

    return render(request, 'accounts/admin/user_detail.html', {
        'user': current_user,
        'target_user': target_user,
        'form': form,
        'page_title': f'User: {target_user.display_name}',
    })


@super_admin_required
@csrf_protect
@require_POST
def admin_change_role_view(request):
    """Change user role (super_admin only)."""
    current_user = request.user

    form = RoleChangeForm(request.POST, actor=current_user)
    if form.is_valid():
        target_user, old_role, new_role = form.save()

        # Log the change
        AuditLog.log(
            action=AuditLog.ACTION_ROLE_CHANGED,
            actor=current_user,
            target=target_user,
            description=f'Role changed from {old_role} to {new_role}',
            previous_state=f'role={old_role}',
            new_state=f'role={new_role}',
            request=request
        )

        # Send email notifications
        try:
            if new_role in [User.ROLE_ADMIN, User.ROLE_SUPER_ADMIN] and old_role == User.ROLE_USER:
                send_promotion_email.delay(target_user.id, new_role)
            elif new_role == User.ROLE_USER and old_role in [User.ROLE_ADMIN, User.ROLE_SUPER_ADMIN]:
                send_demotion_email.delay(target_user.id)
        except Exception as e:
            logger.warning(f'Failed to queue role change email: {e}')

        messages.success(request, f'Role updated to {target_user.role_display}.')
    else:
        for error in form.non_field_errors():
            messages.error(request, error)

    # Redirect based on new role
    if form.target_user and form.target_user.role == User.ROLE_USER:
        return redirect('admin_users')
    return redirect('admin_admins')


@admin_required
def admin_audit_log_view(request):
    """Admin view for audit logs."""
    user = request.user

    logs = AuditLog.objects.select_related('actor', 'target').order_by('-created_at')

    # Filter by action
    action_filter = request.GET.get('action', '')
    if action_filter:
        logs = logs.filter(action=action_filter)

    # Filter by date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        logs = logs.filter(created_at__date__gte=date_from)
    if date_to:
        logs = logs.filter(created_at__date__lte=date_to)

    # Search
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

    return render(request, 'accounts/admin/audit_log.html', {
        'user': user,
        'logs': logs_page,
        'action_filter': action_filter,
        'action_choices': AuditLog.ACTION_CHOICES,
        'search': search,
        'date_from': date_from,
        'date_to': date_to,
        'page_title': 'Audit Log',
    })


# =============================================================================
# Health Check
# =============================================================================

def health_check(request):
    """Health check endpoint for container orchestration."""
    from django.http import JsonResponse
    from django.db import connection

    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')

        return JsonResponse({'status': 'healthy'})
    except Exception as e:
        return JsonResponse({'status': 'unhealthy', 'error': str(e)}, status=500)


# =============================================================================
# Error handlers
# =============================================================================

def handler404(request, exception):
    """Custom 404 page."""
    return render(request, 'errors/404.html', status=404)


def handler500(request):
    """Custom 500 page."""
    return render(request, 'errors/500.html', status=500)
