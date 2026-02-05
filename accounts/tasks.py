"""
Atlas Config - Celery Tasks

Asynchronous tasks for email notifications and background processing.
Supports both User and AtlasAdmin models for notifications.
"""

import logging
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_task(self, subject, template_name, context, recipient_email):
    """
    Send an email asynchronously using a template.

    Args:
        subject: Email subject line
        template_name: Name of the email template (without extension)
        context: Dictionary of context variables for the template
        recipient_email: Recipient email address
    """
    try:
        # Render HTML template
        html_content = render_to_string(f'emails/{template_name}.html', context)
        text_content = strip_tags(html_content)

        # Try to load plain text template if it exists
        try:
            text_content = render_to_string(f'emails/{template_name}.txt', context)
        except Exception:
            pass  # Use stripped HTML as fallback

        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
            reply_to=[settings.EMAIL_REPLY_TO] if hasattr(settings, 'EMAIL_REPLY_TO') else None
        )
        email.attach_alternative(html_content, 'text/html')

        # Send email
        email.send(fail_silently=False)

        logger.info(f"Email sent successfully to {recipient_email}: {subject}")
        return True

    except Exception as exc:
        logger.error(f"Failed to send email to {recipient_email}: {exc}")
        raise self.retry(exc=exc)


@shared_task
def send_welcome_email(user_id):
    """
    Send welcome email to a newly registered user.
    """
    from accounts.models import User

    try:
        user = User.objects.get(id=user_id)

        context = {
            'user_name': user.first_name,
            'user_email': user.email,
            'username': user.username,
            'site_url': settings.SITE_URL,
            'login_url': f"{settings.SITE_URL}/login/",
            'site_name': 'Atlas Config',
        }

        send_email_task.delay(
            subject='Welcome to Atlas Config',
            template_name='welcome',
            context=context,
            recipient_email=user.email
        )

        logger.info(f"Welcome email queued for {user.email}")

    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for welcome email")


@shared_task
def send_password_reset_email(account_id, reset_token, account_type='user'):
    """
    Send password reset email with secure link.

    Args:
        account_id: ID of the User or AtlasAdmin
        reset_token: The reset token string
        account_type: Either 'user' or 'admin'
    """
    from accounts.models import User, AtlasAdmin

    try:
        if account_type == 'admin':
            account = AtlasAdmin.objects.get(id=account_id)
            login_url = f"{settings.SITE_URL}/admin-login/"
        else:
            account = User.objects.get(id=account_id)
            login_url = f"{settings.SITE_URL}/login/"

        reset_url = f"{settings.SITE_URL}/reset-password/{reset_token}/"

        context = {
            'user_name': account.first_name,
            'user_email': account.email,
            'reset_url': reset_url,
            'login_url': login_url,
            'site_url': settings.SITE_URL,
            'site_name': 'Atlas Config',
            'expiry_hours': getattr(settings, 'PASSWORD_RESET_TIMEOUT_HOURS', 24),
            'is_admin': account_type == 'admin',
        }

        send_email_task.delay(
            subject='Reset Your Atlas Config Password',
            template_name='password_reset',
            context=context,
            recipient_email=account.email
        )

        logger.info(f"Password reset email queued for {account.email}")

    except (User.DoesNotExist, AtlasAdmin.DoesNotExist):
        logger.error(f"{account_type.capitalize()} {account_id} not found for password reset email")


@shared_task
def send_password_changed_email(account_id, account_type='user'):
    """
    Send confirmation email when password is changed.

    Args:
        account_id: ID of the User or AtlasAdmin
        account_type: Either 'user' or 'admin'
    """
    from accounts.models import User, AtlasAdmin

    try:
        if account_type == 'admin':
            account = AtlasAdmin.objects.get(id=account_id)
            login_url = f"{settings.SITE_URL}/admin-login/"
        else:
            account = User.objects.get(id=account_id)
            login_url = f"{settings.SITE_URL}/login/"

        context = {
            'user_name': account.first_name,
            'user_email': account.email,
            'login_url': login_url,
            'site_url': settings.SITE_URL,
            'site_name': 'Atlas Config',
            'is_admin': account_type == 'admin',
        }

        send_email_task.delay(
            subject='Your Password Has Been Changed - Atlas Config',
            template_name='password_changed',
            context=context,
            recipient_email=account.email
        )

        logger.info(f"Password changed email queued for {account.email}")

    except (User.DoesNotExist, AtlasAdmin.DoesNotExist):
        logger.error(f"{account_type.capitalize()} {account_id} not found for password changed email")


@shared_task
def send_promotion_email(admin_id, new_role):
    """
    Send notification email when admin role is changed.
    """
    from accounts.models import AtlasAdmin

    try:
        admin = AtlasAdmin.objects.get(id=admin_id)

        role_display = admin.role_display

        context = {
            'user_name': admin.first_name,
            'user_email': admin.email,
            'new_role': role_display,
            'site_url': settings.SITE_URL,
            'dashboard_url': f"{settings.SITE_URL}/admin/",
            'site_name': 'Atlas Config',
        }

        send_email_task.delay(
            subject=f'Your Role Has Been Updated - Atlas Config',
            template_name='promotion',
            context=context,
            recipient_email=admin.email
        )

        logger.info(f"Role change email queued for {admin.email} (new role: {new_role})")

    except AtlasAdmin.DoesNotExist:
        logger.error(f"Admin {admin_id} not found for promotion email")


@shared_task
def send_demotion_email(admin_id):
    """
    Send notification email when admin role is downgraded.
    """
    from accounts.models import AtlasAdmin

    try:
        admin = AtlasAdmin.objects.get(id=admin_id)

        context = {
            'user_name': admin.first_name,
            'user_email': admin.email,
            'site_url': settings.SITE_URL,
            'dashboard_url': f"{settings.SITE_URL}/admin/",
            'site_name': 'Atlas Config',
        }

        send_email_task.delay(
            subject='Your Admin Role Has Been Changed - Atlas Config',
            template_name='demotion',
            context=context,
            recipient_email=admin.email
        )

        logger.info(f"Demotion email queued for {admin.email}")

    except AtlasAdmin.DoesNotExist:
        logger.error(f"Admin {admin_id} not found for demotion email")


@shared_task
def send_role_granted_email(user_id, role_name):
    """
    Send notification email when a role is granted to a user.
    """
    from accounts.models import User

    try:
        user = User.objects.get(id=user_id)

        context = {
            'user_name': user.first_name,
            'user_email': user.email,
            'role_name': role_name,
            'site_url': settings.SITE_URL,
            'dashboard_url': f"{settings.SITE_URL}/dashboard/",
            'roles_url': f"{settings.SITE_URL}/dashboard/roles/",
            'site_name': 'Atlas Config',
        }

        send_email_task.delay(
            subject=f'New Role Granted: {role_name} - Atlas Config',
            template_name='role_granted',
            context=context,
            recipient_email=user.email
        )

        logger.info(f"Role granted email queued for {user.email} (role: {role_name})")

    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for role granted email")
