"""
Atlas Config - Database Models

This module defines the core models for the Atlas Config management system:
- User: User model for regular atlas users (uses username + SEC sync)
- AtlasAdmin: Separate admin model for administrator authentication
- Role: Local representation of SEC roles with descriptions
- UserRole: Many-to-many relationship between Users and Roles
- Message: In-app announcements/messages system
- AuditLog: Comprehensive audit trail for all significant actions
- PasswordResetToken: Secure password reset functionality

SEC Architecture Notes:
----------------------
The system maintains synchronization with external SEC tables:
- sec_user: External user records (synced via ensure_sec_user)
- sec_role: External role definitions (synced to local Role model)
- sec_user_role: User-role assignments (synced via sync_user_roles_to_sec)

The local Role model acts as a cache/mirror of sec_role with additional
metadata like descriptions for display in the admin dashboard.
"""

import secrets
import bcrypt
from datetime import timedelta
from django.db import models
from django.utils import timezone
from django.conf import settings


# =============================================================================
# Prefix Model - Manageable name prefixes
# =============================================================================

class Prefix(models.Model):
    """
    User name prefix options (Mr., Mrs., Ms., Dr., Prof., etc.).
    
    Managed by super admins instead of being hardcoded.
    """
    
    name = models.CharField(max_length=20, unique=True,
        help_text="Short code for the prefix (e.g., 'mr', 'dr')")
    display_name = models.CharField(max_length=50,
        help_text="Display text for the prefix (e.g., 'Mr.', 'Dr.')")
    is_active = models.BooleanField(default=True,
        help_text="Whether this prefix is available for selection")
    sort_order = models.IntegerField(default=0,
        help_text="Order in which to display this prefix")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'atlas_prefix'
        ordering = ['sort_order', 'display_name']
        verbose_name = 'Prefix'
        verbose_name_plural = 'Prefixes'
    
    def __str__(self):
        return self.display_name


# =============================================================================
# Category Model - User categories (student, researcher, clinician, etc.)
# =============================================================================

class Category(models.Model):
    """
    User category options (Student, Researcher, Clinician, Module Member, etc.).

    Categories define what type of user is registering.
    Managed by super admins via the admin dashboard.
    """

    name = models.CharField(max_length=100, unique=True,
        help_text="Category name (e.g., 'student', 'researcher')")
    display_name = models.CharField(max_length=150,
        help_text="Display text for the category (e.g., 'Student', 'Researcher')")
    description = models.TextField(blank=True, default='',
        help_text="Description of this category")
    is_active = models.BooleanField(default=True,
        help_text="Whether this category is available for selection")
    sort_order = models.IntegerField(default=0,
        help_text="Order in which to display this category")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'atlas_category'
        ordering = ['sort_order', 'display_name']
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.display_name


# =============================================================================
# Role Model - Manageable user roles
# =============================================================================

class Role(models.Model):
    """
    User role definitions (guest, student, researcher, clinician, etc.).
    
    Managed by super admins. Roles define user access levels and permissions.
    """

    name = models.CharField(max_length=255, unique=True,
        help_text="Role name (e.g., 'guest', 'researcher')")
    description = models.TextField(blank=True, default='',
        help_text="Description of what this role represents")
    is_active = models.BooleanField(default=True,
        help_text="Whether this role is available for assignment")
    sort_order = models.IntegerField(default=0,
        help_text="Order in which to display this role")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'atlas_role'
        ordering = ['sort_order', 'name']
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.name


# =============================================================================
# User Model - Regular users with SEC sync
# =============================================================================

class User(models.Model):
    """
    User model for regular Atlas users.

    This model represents users who authenticate via the user login flow.
    Users are synced to the SEC tables (sec_user) upon creation.

    SEC Sync Architecture:
    - On signup, ensure_sec_user() creates a sec_user record
    - User roles are managed via the UserRole model
    - Role changes are synced to sec_user_role automatically

    Note: Username is normalized to lowercase for SEC compatibility.
    """

    # Authentication fields - username is primary identifier
    username = models.CharField(max_length=150, unique=True,
        help_text="Lowercase username")
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)

    # Profile fields
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    prefix = models.ForeignKey(Prefix, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='users', help_text="Name prefix (Mr., Dr., etc.)")
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='users', help_text="User category (Student, Researcher, etc.)")
    affiliation = models.CharField(max_length=255, blank=True, default='')

    # Roles - many-to-many through UserRole
    roles = models.ManyToManyField(Role, through='UserRole', related_name='users')

    # Status
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
        return f"{self.full_name} ({self.username})"

    def save(self, *args, **kwargs):
        # Normalize username to lowercase for SEC compatibility
        if self.username:
            self.username = self.username.lower().strip()
        if self.email:
            self.email = self.email.lower().strip()
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        """Return the user's full name with optional prefix."""
        if self.prefix:
            return f"{self.prefix.display_name} {self.first_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    @property
    def display_name(self):
        """Return user's name without prefix."""
        return f"{self.first_name} {self.last_name}"

    @property
    def role_names(self):
        """Return list of role names for this user."""
        return list(self.roles.values_list('name', flat=True))

    def set_password(self, raw_password):
        """
        Hash and set the user's password using bcrypt.
        Uses OHDSI-compatible settings (prefix=2a, rounds=10).
        """
        salt = bcrypt.gensalt(rounds=10, prefix=b"2a")
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

    def has_role(self, role_name):
        """Check if user has a specific role."""
        return self.roles.filter(name__iexact=role_name).exists()

    def add_role(self, role):
        """Add a role to this user (creates UserRole record)."""
        if isinstance(role, str):
            role = Role.objects.get(name__iexact=role)
        UserRole.objects.get_or_create(user=self, role=role)

    def remove_role(self, role):
        """Remove a role from this user."""
        if isinstance(role, str):
            role = Role.objects.get(name__iexact=role)
        UserRole.objects.filter(user=self, role=role).delete()
        return True


# =============================================================================
# UserRole - Many-to-many relationship with metadata
# =============================================================================

class UserRole(models.Model):
    """
    Explicit many-to-many relationship between User and Role.

    This model tracks role assignments and provides metadata about
    when and by whom roles were granted.

    SEC Sync Architecture:
    - Creating a UserRole triggers sync to sec_user_role
    - Deleting a UserRole removes from sec_user_role
    - The origin field tracks whether the grant came from Atlas or SEC
    """

    ORIGIN_ATLAS = 'ATLAS'
    ORIGIN_SEC = 'SEC'
    ORIGIN_SYSTEM = 'SYSTEM'

    ORIGIN_CHOICES = (
        (ORIGIN_ATLAS, 'Atlas Admin'),
        (ORIGIN_SEC, 'SEC System'),
        (ORIGIN_SYSTEM, 'System'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_roles')
    origin = models.CharField(max_length=20, choices=ORIGIN_CHOICES, default=ORIGIN_ATLAS)
    granted_by = models.ForeignKey(
        'AtlasAdmin',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='roles_granted'
    )
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'atlas_user_role'
        unique_together = ['user', 'role']
        ordering = ['role__name']
        verbose_name = 'User Role'
        verbose_name_plural = 'User Roles'

    def __str__(self):
        return f"{self.user.username} - {self.role.name}"


# =============================================================================
# AtlasAdmin - Separate admin authentication
# =============================================================================

class AtlasAdmin(models.Model):
    """
    Separate model for administrator accounts.

    AtlasAdmin accounts are distinct from regular User accounts:
    - They authenticate via the admin login flow
    - They have admin/super_admin/system_superadmin roles
    - They do NOT sync to SEC tables
    - They manage users and their roles

    Permission Hierarchy:
    - admin: Can view users and their roles, but cannot modify
    - super_admin: Can manage users, assign/revoke roles
    - system_superadmin: Can manage other admins, create super_admins
      Only system_superadmin can promote/demote to super_admin level.
    """

    ROLE_ADMIN = 'admin'
    ROLE_SUPER_ADMIN = 'super_admin'
    ROLE_SYSTEM_SUPERADMIN = 'system_superadmin'

    ROLE_CHOICES = (
        (ROLE_ADMIN, 'Admin'),
        (ROLE_SUPER_ADMIN, 'Super Admin'),
        (ROLE_SYSTEM_SUPERADMIN, 'System Super Admin'),
    )

    # Authentication
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)

    # Profile
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    # Admin role
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default=ROLE_ADMIN)

    # Status
    is_active = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'atlas_admin'
        ordering = ['-role', '-created_at']
        verbose_name = 'Atlas Admin'
        verbose_name_plural = 'Atlas Admins'

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower().strip()
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def display_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_admin(self):
        """All AtlasAdmin accounts have at least admin privileges."""
        return True

    @property
    def is_super_admin(self):
        """Check if admin has super_admin or higher role."""
        return self.role in (self.ROLE_SUPER_ADMIN, self.ROLE_SYSTEM_SUPERADMIN)

    @property
    def is_system_superadmin(self):
        """Check if admin is the system super admin."""
        return self.role == self.ROLE_SYSTEM_SUPERADMIN

    @property
    def role_display(self):
        """Get human-readable role name."""
        return dict(self.ROLE_CHOICES).get(self.role, 'Unknown')

    def set_password(self, raw_password):
        """Hash and set the admin's password using bcrypt."""
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

    def can_manage_users(self):
        """Check if admin can manage regular users."""
        return self.is_super_admin

    def can_manage_admins(self):
        """Check if admin can manage other admins."""
        return self.is_system_superadmin

    def can_view_admin_list(self):
        """
        Permission check for viewing admin list.
        Only super_admin and system_superadmin can view admin list.
        Regular admins cannot see other admins.
        """
        return self.is_super_admin

    def can_change_admin_role(self, target_admin, new_role):
        """
        Check if this admin can change another admin's role.

        Rules:
        - Only system_superadmin can change admin roles
        - Cannot demote the last system_superadmin
        - Cannot change own role (protection)
        """
        if not self.is_system_superadmin:
            return False

        # Cannot change own role
        if self.id == target_admin.id:
            return False

        # Cannot demote last system_superadmin
        if target_admin.is_system_superadmin and new_role != self.ROLE_SYSTEM_SUPERADMIN:
            sys_admin_count = AtlasAdmin.objects.filter(
                role=self.ROLE_SYSTEM_SUPERADMIN,
                is_active=True
            ).exclude(id=target_admin.id).count()
            if sys_admin_count == 0:
                return False

        return True


# =============================================================================
# Message - In-app announcements
# =============================================================================

class Message(models.Model):
    """
    In-app messages/announcements for users.

    Admins can create messages that appear in user dashboards.
    Messages can be targeted to all users or specific roles.
    """

    PRIORITY_LOW = 'low'
    PRIORITY_NORMAL = 'normal'
    PRIORITY_HIGH = 'high'

    PRIORITY_CHOICES = (
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_NORMAL, 'Normal'),
        (PRIORITY_HIGH, 'High'),
    )

    title = models.CharField(max_length=255)
    content = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_NORMAL)

    # Targeting
    target_all_users = models.BooleanField(default=True)
    target_roles = models.ManyToManyField(Role, blank=True, related_name='messages')

    # Status
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)

    # Tracking
    created_by = models.ForeignKey(
        AtlasAdmin,
        on_delete=models.SET_NULL,
        null=True,
        related_name='messages_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'atlas_message'
        ordering = ['-priority', '-created_at']
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'

    def __str__(self):
        return self.title

    @property
    def is_visible(self):
        """Check if message should be displayed."""
        now = timezone.now()
        if not self.is_active:
            return False
        if self.starts_at > now:
            return False
        if self.expires_at and self.expires_at < now:
            return False
        return True

    def is_visible_to_user(self, user):
        """Check if message should be shown to a specific user."""
        if not self.is_visible:
            return False
        if self.target_all_users:
            return True
        # Check if user has any of the target roles
        user_role_ids = set(user.roles.values_list('id', flat=True))
        target_role_ids = set(self.target_roles.values_list('id', flat=True))
        return bool(user_role_ids & target_role_ids)


class MessageDismissal(models.Model):
    """Tracks which users have dismissed which messages."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dismissed_messages')
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='dismissals')
    dismissed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'atlas_message_dismissal'
        unique_together = ['user', 'message']
        verbose_name = 'Message Dismissal'
        verbose_name_plural = 'Message Dismissals'


# =============================================================================
# AuditLog - Comprehensive audit trail
# =============================================================================

class AuditLog(models.Model):
    """
    Comprehensive audit trail for tracking all significant system actions.

    Records:
    - User creation/updates
    - Role changes (grants/revokes)
    - Password resets
    - Login/logout events
    - Admin actions
    - SEC sync events
    """

    ACTION_LOGIN = 'login'
    ACTION_LOGOUT = 'logout'
    ACTION_LOGIN_FAILED = 'login_failed'
    ACTION_USER_CREATED = 'user_created'
    ACTION_USER_UPDATED = 'user_updated'
    ACTION_USER_DEACTIVATED = 'user_deactivated'
    ACTION_USER_ACTIVATED = 'user_activated'
    ACTION_ROLE_GRANTED = 'role_granted'
    ACTION_ROLE_REVOKED = 'role_revoked'
    ACTION_ROLE_BULK_GRANT = 'role_bulk_grant'
    ACTION_PASSWORD_CHANGED = 'password_changed'
    ACTION_PASSWORD_RESET_REQUESTED = 'password_reset_requested'
    ACTION_PASSWORD_RESET_COMPLETED = 'password_reset_completed'
    ACTION_PROFILE_UPDATED = 'profile_updated'
    ACTION_ADMIN_LOGIN = 'admin_login'
    ACTION_ADMIN_LOGOUT = 'admin_logout'
    ACTION_ADMIN_CREATED = 'admin_created'
    ACTION_ADMIN_ROLE_CHANGED = 'admin_role_changed'
    ACTION_SEC_SYNC = 'sec_sync'
    ACTION_MESSAGE_CREATED = 'message_created'
    ACTION_MESSAGE_UPDATED = 'message_updated'

    ACTION_CHOICES = (
        (ACTION_LOGIN, 'User Login'),
        (ACTION_LOGOUT, 'User Logout'),
        (ACTION_LOGIN_FAILED, 'Login Failed'),
        (ACTION_USER_CREATED, 'User Created'),
        (ACTION_USER_UPDATED, 'User Updated'),
        (ACTION_USER_DEACTIVATED, 'User Deactivated'),
        (ACTION_USER_ACTIVATED, 'User Activated'),
        (ACTION_ROLE_GRANTED, 'Role Granted'),
        (ACTION_ROLE_REVOKED, 'Role Revoked'),
        (ACTION_ROLE_BULK_GRANT, 'Bulk Role Grant'),
        (ACTION_PASSWORD_CHANGED, 'Password Changed'),
        (ACTION_PASSWORD_RESET_REQUESTED, 'Password Reset Requested'),
        (ACTION_PASSWORD_RESET_COMPLETED, 'Password Reset Completed'),
        (ACTION_PROFILE_UPDATED, 'Profile Updated'),
        (ACTION_ADMIN_LOGIN, 'Admin Login'),
        (ACTION_ADMIN_LOGOUT, 'Admin Logout'),
        (ACTION_ADMIN_CREATED, 'Admin Created'),
        (ACTION_ADMIN_ROLE_CHANGED, 'Admin Role Changed'),
        (ACTION_SEC_SYNC, 'SEC Sync'),
        (ACTION_MESSAGE_CREATED, 'Message Created'),
        (ACTION_MESSAGE_UPDATED, 'Message Updated'),
    )

    # Who performed the action (can be User or Admin)
    actor_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='actions_performed'
    )
    actor_admin = models.ForeignKey(
        AtlasAdmin,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='actions_performed'
    )
    actor_email = models.EmailField(blank=True, default='')

    # Target of the action (if applicable)
    target_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='actions_received'
    )
    target_admin = models.ForeignKey(
        AtlasAdmin,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='actions_received'
    )
    target_email = models.EmailField(blank=True, default='')

    # Action details
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField(blank=True, default='')

    # State changes
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
            models.Index(fields=['actor_user', 'created_at']),
            models.Index(fields=['actor_admin', 'created_at']),
            models.Index(fields=['target_user', 'created_at']),
        ]

    def __str__(self):
        actor_str = self.actor_email or 'System'
        return f"{actor_str} - {self.get_action_display()} - {self.created_at}"

    @classmethod
    def log(cls, action, actor_user=None, actor_admin=None, target_user=None,
            target_admin=None, description='', previous_state='', new_state='', request=None):
        """
        Create an audit log entry.

        Args:
            action: One of the ACTION_* constants
            actor_user: User who performed the action (for user actions)
            actor_admin: Admin who performed the action (for admin actions)
            target_user: User who was affected
            target_admin: Admin who was affected
            description: Human-readable description
            previous_state: State before the action
            new_state: State after the action
            request: HTTP request for IP/user agent extraction
        """
        ip_address = None
        user_agent = ''

        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0].strip()
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]

        # Determine actor email
        actor_email = ''
        if actor_admin:
            actor_email = actor_admin.email
        elif actor_user:
            actor_email = actor_user.email

        # Determine target email
        target_email = ''
        if target_admin:
            target_email = target_admin.email
        elif target_user:
            target_email = target_user.email

        return cls.objects.create(
            actor_user=actor_user,
            actor_admin=actor_admin,
            actor_email=actor_email,
            target_user=target_user,
            target_admin=target_admin,
            target_email=target_email,
            action=action,
            description=description,
            previous_state=previous_state,
            new_state=new_state,
            ip_address=ip_address,
            user_agent=user_agent
        )


# =============================================================================
# PasswordResetToken
# =============================================================================

class PasswordResetToken(models.Model):
    """
    Secure token for password reset functionality.

    Works for both User and AtlasAdmin accounts.
    """

    # Can be for either User or Admin
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='password_reset_tokens'
    )
    admin = models.ForeignKey(
        AtlasAdmin,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='password_reset_tokens'
    )

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
        if self.user:
            return f"Reset token for user {self.user.email}"
        elif self.admin:
            return f"Reset token for admin {self.admin.email}"
        return f"Reset token {self.token[:8]}..."

    @classmethod
    def create_for_user(cls, user):
        """Create a new password reset token for a user."""
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        token = secrets.token_urlsafe(48)
        timeout_hours = getattr(settings, 'PASSWORD_RESET_TIMEOUT_HOURS', 24)
        expires_at = timezone.now() + timedelta(hours=timeout_hours)
        return cls.objects.create(user=user, token=token, expires_at=expires_at)

    @classmethod
    def create_for_admin(cls, admin):
        """Create a new password reset token for an admin."""
        cls.objects.filter(admin=admin, is_used=False).update(is_used=True)
        token = secrets.token_urlsafe(48)
        timeout_hours = getattr(settings, 'PASSWORD_RESET_TIMEOUT_HOURS', 24)
        expires_at = timezone.now() + timedelta(hours=timeout_hours)
        return cls.objects.create(admin=admin, token=token, expires_at=expires_at)

    @property
    def is_valid(self):
        """Check if the token is still valid."""
        if self.is_used:
            return False
        if timezone.now() > self.expires_at:
            return False
        return True

    @property
    def account(self):
        """Return the user or admin this token belongs to."""
        return self.user or self.admin

    def use(self):
        """Mark the token as used."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])

    @classmethod
    def get_valid_token(cls, token):
        """Retrieve a valid token by its string value."""
        try:
            reset_token = cls.objects.select_related('user', 'admin').get(token=token)
            if reset_token.is_valid:
                return reset_token
        except cls.DoesNotExist:
            pass
        return None
