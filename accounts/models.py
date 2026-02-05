"""
Atlas Config - Database Models

This module defines the core models for the Atlas Config management system:
- User: Unified user model with role-based access control
- AuditLog: Comprehensive audit trail for all significant actions
- PasswordResetToken: Secure password reset functionality
"""

import secrets
import bcrypt
from datetime import timedelta
from django.db import models
from django.utils import timezone
from django.conf import settings


class User(models.Model):
    """
    Unified user model with role-based access control.

    Roles:
    - user: Standard user with basic access
    - admin: Administrator with user management capabilities
    - super_admin: Full system access including role management
    """

    ROLE_USER = 'user'
    ROLE_ADMIN = 'admin'
    ROLE_SUPER_ADMIN = 'super_admin'

    ROLE_CHOICES = (
        (ROLE_USER, 'User'),
        (ROLE_ADMIN, 'Admin'),
        (ROLE_SUPER_ADMIN, 'Super Admin'),
    )

    PREFIX_CHOICES = (
        ('', ''),
        ('mr', 'Mr.'),
        ('mrs', 'Mrs.'),
        ('ms', 'Ms.'),
        ('dr', 'Dr.'),
        ('prof', 'Prof.'),
    )

    # Authentication fields
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)

    # Profile fields
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    prefix = models.CharField(max_length=10, choices=PREFIX_CHOICES, blank=True, default='')
    affiliation = models.CharField(max_length=255, blank=True, default='')

    # Role and status
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_USER)
    is_active = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'atlas_user'
        ordering = ['-created_at']
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    @property
    def full_name(self):
        """Return the user's full name with optional prefix."""
        prefix_display = dict(self.PREFIX_CHOICES).get(self.prefix, '')
        if prefix_display:
            return f"{prefix_display} {self.first_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    @property
    def display_name(self):
        """Return user's name without prefix."""
        return f"{self.first_name} {self.last_name}"

    @property
    def is_admin(self):
        """Check if user has admin or super_admin role."""
        return self.role in (self.ROLE_ADMIN, self.ROLE_SUPER_ADMIN)

    @property
    def is_super_admin(self):
        """Check if user has super_admin role."""
        return self.role == self.ROLE_SUPER_ADMIN

    @property
    def role_display(self):
        """Get human-readable role name."""
        return dict(self.ROLE_CHOICES).get(self.role, 'Unknown')

    def set_password(self, raw_password):
        """Hash and set the user's password using bcrypt."""
        salt = bcrypt.gensalt(rounds=12, prefix=b"2b")
        self.password = bcrypt.hashpw(raw_password.encode('utf-8'), salt).decode('utf-8')

    def check_password(self, raw_password):
        """Verify a password against the stored hash."""
        try:
            return bcrypt.checkpw(raw_password.encode('utf-8'), self.password.encode('utf-8'))
        except (ValueError, TypeError):
            return False

    def update_last_login(self):
        """Update the last login timestamp."""
        self.last_login = timezone.now()
        self.save(update_fields=['last_login'])

    def can_manage_user(self, target_user):
        """
        Check if this user can manage (edit/view) another user.

        Rules:
        - Users can only manage themselves
        - Admins can view users but not promote/demote
        - Super admins can manage everyone
        """
        if self.id == target_user.id:
            return True
        if self.is_super_admin:
            return True
        if self.is_admin and target_user.role == self.ROLE_USER:
            return True
        return False

    def can_change_role(self, target_user, new_role):
        """
        Check if this user can change another user's role.

        STRICT RULES:
        - Only super_admin can promote/demote users
        - Admins CANNOT promote or demote anyone
        - Cannot demote the last super_admin
        """
        # Only super_admin can change roles
        if not self.is_super_admin:
            return False

        # Can't change own role (edge case protection)
        if self.id == target_user.id:
            # Check if this would remove the last super_admin
            if new_role != self.ROLE_SUPER_ADMIN:
                super_admin_count = User.objects.filter(
                    role=self.ROLE_SUPER_ADMIN,
                    is_active=True
                ).exclude(id=self.id).count()
                if super_admin_count == 0:
                    return False

        # Check if demoting target would remove last super_admin
        if target_user.is_super_admin and new_role != self.ROLE_SUPER_ADMIN:
            super_admin_count = User.objects.filter(
                role=self.ROLE_SUPER_ADMIN,
                is_active=True
            ).exclude(id=target_user.id).count()
            if super_admin_count == 0:
                return False

        return True


class AuditLog(models.Model):
    """
    Comprehensive audit trail for tracking all significant system actions.

    Records:
    - User creation/updates
    - Role changes (promotions/demotions)
    - Password resets
    - Login/logout events
    - Admin actions
    """

    ACTION_LOGIN = 'login'
    ACTION_LOGOUT = 'logout'
    ACTION_LOGIN_FAILED = 'login_failed'
    ACTION_USER_CREATED = 'user_created'
    ACTION_USER_UPDATED = 'user_updated'
    ACTION_USER_DEACTIVATED = 'user_deactivated'
    ACTION_USER_ACTIVATED = 'user_activated'
    ACTION_ROLE_CHANGED = 'role_changed'
    ACTION_PASSWORD_CHANGED = 'password_changed'
    ACTION_PASSWORD_RESET_REQUESTED = 'password_reset_requested'
    ACTION_PASSWORD_RESET_COMPLETED = 'password_reset_completed'
    ACTION_PROFILE_UPDATED = 'profile_updated'

    ACTION_CHOICES = (
        (ACTION_LOGIN, 'User Login'),
        (ACTION_LOGOUT, 'User Logout'),
        (ACTION_LOGIN_FAILED, 'Login Failed'),
        (ACTION_USER_CREATED, 'User Created'),
        (ACTION_USER_UPDATED, 'User Updated'),
        (ACTION_USER_DEACTIVATED, 'User Deactivated'),
        (ACTION_USER_ACTIVATED, 'User Activated'),
        (ACTION_ROLE_CHANGED, 'Role Changed'),
        (ACTION_PASSWORD_CHANGED, 'Password Changed'),
        (ACTION_PASSWORD_RESET_REQUESTED, 'Password Reset Requested'),
        (ACTION_PASSWORD_RESET_COMPLETED, 'Password Reset Completed'),
        (ACTION_PROFILE_UPDATED, 'Profile Updated'),
    )

    # Who performed the action (null for system actions or anonymous)
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='actions_performed'
    )
    actor_email = models.EmailField(blank=True, default='')  # Preserved even if user deleted

    # Target of the action (if applicable)
    target = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='actions_received'
    )
    target_email = models.EmailField(blank=True, default='')  # Preserved even if user deleted

    # Action details
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField(blank=True, default='')

    # State changes (JSON-like text for simplicity)
    previous_state = models.TextField(blank=True, default='')
    new_state = models.TextField(blank=True, default='')

    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')

    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'atlas_audit_log'
        ordering = ['-created_at']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['actor', 'created_at']),
            models.Index(fields=['target', 'created_at']),
        ]

    def __str__(self):
        actor_str = self.actor_email or 'System'
        return f"{actor_str} - {self.get_action_display()} - {self.created_at}"

    @classmethod
    def log(cls, action, actor=None, target=None, description='',
            previous_state='', new_state='', request=None):
        """
        Create an audit log entry.

        Args:
            action: One of the ACTION_* constants
            actor: User who performed the action
            target: User who was affected (optional)
            description: Human-readable description
            previous_state: State before the action
            new_state: State after the action
            request: HTTP request for IP/user agent extraction
        """
        ip_address = None
        user_agent = ''

        if request:
            # Get IP address
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0].strip()
            else:
                ip_address = request.META.get('REMOTE_ADDR')

            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]

        return cls.objects.create(
            actor=actor,
            actor_email=actor.email if actor else '',
            target=target,
            target_email=target.email if target else '',
            action=action,
            description=description,
            previous_state=previous_state,
            new_state=new_state,
            ip_address=ip_address,
            user_agent=user_agent
        )


class PasswordResetToken(models.Model):
    """
    Secure token for password reset functionality.

    Features:
    - Cryptographically secure token generation
    - Automatic expiration
    - Single-use enforcement
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=64, unique=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'atlas_password_reset_token'
        ordering = ['-created_at']
        verbose_name = 'Password Reset Token'
        verbose_name_plural = 'Password Reset Tokens'

    def __str__(self):
        return f"Reset token for {self.user.email}"

    @classmethod
    def create_for_user(cls, user):
        """
        Create a new password reset token for a user.
        Invalidates any existing unused tokens.
        """
        # Invalidate existing unused tokens
        cls.objects.filter(user=user, is_used=False).update(is_used=True)

        # Generate secure token
        token = secrets.token_urlsafe(48)

        # Calculate expiration
        timeout_hours = getattr(settings, 'PASSWORD_RESET_TIMEOUT_HOURS', 24)
        expires_at = timezone.now() + timedelta(hours=timeout_hours)

        return cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )

    @property
    def is_valid(self):
        """Check if the token is still valid (not used and not expired)."""
        if self.is_used:
            return False
        if timezone.now() > self.expires_at:
            return False
        return True

    def use(self):
        """Mark the token as used."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])

    @classmethod
    def get_valid_token(cls, token):
        """
        Retrieve a valid token by its string value.
        Returns None if not found or invalid.
        """
        try:
            reset_token = cls.objects.select_related('user').get(token=token)
            if reset_token.is_valid:
                return reset_token
        except cls.DoesNotExist:
            pass
        return None
