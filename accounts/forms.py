"""
Atlas Config - Forms

Forms for authentication, user management, role assignment, and profile updates.
Supports both User (username-based) and AtlasAdmin (email-based) authentication.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import User, AtlasAdmin, Role, Category, Prefix, UserRole, Message


# =============================================================================
# User Authentication Forms
# =============================================================================

class UserLoginForm(forms.Form):
    """
    Login form for regular users.
    Accepts username or email for flexibility.
    """

    username = forms.CharField(
        label='Username or Email',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username or email',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        username_or_email = cleaned_data.get('username', '').strip().lower()
        password = cleaned_data.get('password')

        if username_or_email and password:
            # Try to find user by username first, then by email
            user = None
            try:
                if '@' in username_or_email:
                    user = User.objects.get(email=username_or_email)
                else:
                    user = User.objects.get(username=username_or_email)
            except User.DoesNotExist:
                # Also try email if username lookup failed
                try:
                    user = User.objects.get(email=username_or_email)
                except User.DoesNotExist:
                    pass

            if not user:
                raise ValidationError('Invalid username/email or password.')
            if not user.is_active:
                raise ValidationError('This account has been deactivated. Please contact an administrator.')
            if not user.check_password(password):
                raise ValidationError('Invalid username/email or password.')

            cleaned_data['user'] = user

        return cleaned_data


class UserSignupForm(forms.Form):
    """
    Registration form for new users.
    Includes username field which is synced to SEC.
    """

    username = forms.CharField(
        label='Username',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a username (lowercase)',
            'autofocus': True,
        }),
        help_text='Letters, numbers, and underscores only. Will be converted to lowercase.'
    )
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'you@example.com',
        })
    )
    first_name = forms.CharField(
        label='First Name',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'John',
        })
    )
    last_name = forms.CharField(
        label='Last Name',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Doe',
        })
    )
    affiliation = forms.CharField(
        label='Affiliation',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'University / Organization (optional)',
        })
    )
    category = forms.ModelChoiceField(
        label='Category',
        queryset=Category.objects.none(),
        required=False,
        empty_label='Select a category',
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    prefix = forms.ModelChoiceField(
        label='Prefix',
        queryset=Prefix.objects.none(),
        required=False,
        empty_label='Select a prefix',
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'At least 8 characters',
        })
    )
    password_confirm = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repeat your password',
        })
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '').lower().strip()

        # Validate format
        if not username:
            raise ValidationError('Username is required.')

        # Only allow alphanumeric and underscores
        import re
        if not re.match(r'^[a-z0-9_]+$', username):
            raise ValidationError('Username can only contain lowercase letters, numbers, and underscores.')

        # Check uniqueness
        if User.objects.filter(username=username).exists():
            raise ValidationError('This username is already taken.')

        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        if email and User.objects.filter(email=email).exists():
            raise ValidationError('An account with this email already exists.')
        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['prefix'].queryset = Prefix.objects.filter(is_active=True).order_by('sort_order', 'display_name')
        self.fields['category'].queryset = Category.objects.filter(is_active=True).order_by('sort_order', 'display_name')

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            try:
                validate_password(password)
            except ValidationError as e:
                raise ValidationError(e.messages)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'Passwords do not match.')

        return cleaned_data

    def save(self):
        """Create and return a new user."""
        user = User(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            prefix=self.cleaned_data.get('prefix'),
            affiliation=self.cleaned_data.get('affiliation', ''),
            category=self.cleaned_data.get('category'),
        )
        user.set_password(self.cleaned_data['password'])
        user.save()
        return user


# =============================================================================
# Admin Authentication Forms
# =============================================================================

class AdminLoginForm(forms.Form):
    """
    Login form for administrators (AtlasAdmin).
    Uses email-based authentication.
    """

    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'admin@example.com',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email', '').lower().strip()
        password = cleaned_data.get('password')

        if email and password:
            try:
                admin = AtlasAdmin.objects.get(email=email)
                if not admin.is_active:
                    raise ValidationError('This admin account has been deactivated.')
                if not admin.check_password(password):
                    raise ValidationError('Invalid email or password.')
                cleaned_data['admin'] = admin
            except AtlasAdmin.DoesNotExist:
                raise ValidationError('Invalid email or password.')

        return cleaned_data


# =============================================================================
# Password Forms
# =============================================================================

class ForgotPasswordForm(forms.Form):
    """Password reset request form."""

    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'you@example.com',
        })
    )


class ResetPasswordForm(forms.Form):
    """Password reset form (with token)."""

    password = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password',
        })
    )
    password_confirm = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repeat new password',
        })
    )

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            try:
                validate_password(password)
            except ValidationError as e:
                raise ValidationError(e.messages)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'Passwords do not match.')

        return cleaned_data


class ChangePasswordForm(forms.Form):
    """Change password form for authenticated users/admins."""

    current_password = forms.CharField(
        label='Current Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter current password',
        })
    )
    new_password = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password',
        })
    )
    new_password_confirm = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repeat new password',
        })
    )

    def __init__(self, account, *args, **kwargs):
        """Account can be either User or AtlasAdmin."""
        super().__init__(*args, **kwargs)
        self.account = account

    def clean_current_password(self):
        current_password = self.cleaned_data.get('current_password')
        if current_password and not self.account.check_password(current_password):
            raise ValidationError('Current password is incorrect.')
        return current_password

    def clean_new_password(self):
        password = self.cleaned_data.get('new_password')
        if password:
            try:
                validate_password(password)
            except ValidationError as e:
                raise ValidationError(e.messages)
        return password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        new_password_confirm = cleaned_data.get('new_password_confirm')

        if new_password and new_password_confirm and new_password != new_password_confirm:
            self.add_error('new_password_confirm', 'Passwords do not match.')

        return cleaned_data

    def save(self):
        """Update the account's password."""
        self.account.set_password(self.cleaned_data['new_password'])
        self.account.save()
        return self.account


# =============================================================================
# Profile Forms
# =============================================================================

class UserProfileForm(forms.ModelForm):
    """User profile update form."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'prefix', 'category', 'affiliation']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'prefix': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'affiliation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'University / Organization',
            }),
        }


class AdminProfileForm(forms.ModelForm):
    """Admin profile update form."""

    class Meta:
        model = AtlasAdmin
        fields = ['first_name', 'last_name']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }


# =============================================================================
# User Management Forms (Admin)
# =============================================================================

class UserEditForm(forms.ModelForm):
    """Admin form for editing user details."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'prefix', 'category', 'affiliation', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'prefix': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'affiliation': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        if email:
            existing = User.objects.filter(email=email)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError('A user with this email already exists.')
        return email


# =============================================================================
# Role Management Forms
# =============================================================================

class RoleForm(forms.ModelForm):
    """Form for creating/editing roles."""

    class Meta:
        model = Role
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Role name',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Human-friendly description of this role',
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class RoleDescriptionForm(forms.Form):
    """Form for updating role description only (AJAX)."""

    role_id = forms.IntegerField(widget=forms.HiddenInput())
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Enter a description for this role',
        }),
        required=False
    )

    def save(self):
        role = Role.objects.get(id=self.cleaned_data['role_id'])
        role.description = self.cleaned_data['description']
        role.save()
        return role


class UserRoleAssignForm(forms.Form):
    """Form for assigning a single role to a user."""

    user_id = forms.IntegerField(widget=forms.HiddenInput())
    role_id = forms.IntegerField(widget=forms.HiddenInput())

    def clean(self):
        cleaned_data = super().clean()
        try:
            cleaned_data['user'] = User.objects.get(id=cleaned_data['user_id'])
        except User.DoesNotExist:
            raise ValidationError('User not found.')

        try:
            cleaned_data['role'] = Role.objects.get(id=cleaned_data['role_id'])
        except Role.DoesNotExist:
            raise ValidationError('Role not found.')

        return cleaned_data


class UserRoleRevokeForm(forms.Form):
    """Form for revoking a role from a user."""

    user_id = forms.IntegerField(widget=forms.HiddenInput())
    role_id = forms.IntegerField(widget=forms.HiddenInput())

    def clean(self):
        cleaned_data = super().clean()
        try:
            cleaned_data['user'] = User.objects.get(id=cleaned_data['user_id'])
        except User.DoesNotExist:
            raise ValidationError('User not found.')

        try:
            role = Role.objects.get(id=cleaned_data['role_id'])
            cleaned_data['role'] = role
        except Role.DoesNotExist:
            raise ValidationError('Role not found.')

        return cleaned_data


class BulkRoleAssignForm(forms.Form):
    """Form for bulk assigning roles to multiple users."""

    user_ids = forms.CharField(widget=forms.HiddenInput())
    role_ids = forms.CharField(widget=forms.HiddenInput())

    def clean_user_ids(self):
        user_ids_str = self.cleaned_data.get('user_ids', '')
        try:
            user_ids = [int(x.strip()) for x in user_ids_str.split(',') if x.strip()]
        except ValueError:
            raise ValidationError('Invalid user IDs format.')

        users = User.objects.filter(id__in=user_ids)
        if users.count() != len(user_ids):
            raise ValidationError('Some users not found.')

        return list(users)

    def clean_role_ids(self):
        role_ids_str = self.cleaned_data.get('role_ids', '')
        try:
            role_ids = [int(x.strip()) for x in role_ids_str.split(',') if x.strip()]
        except ValueError:
            raise ValidationError('Invalid role IDs format.')

        roles = Role.objects.filter(id__in=role_ids)
        if roles.count() != len(role_ids):
            raise ValidationError('Some roles not found.')

        return list(roles)


# =============================================================================
# Admin Management Forms (System Superadmin)
# =============================================================================

class AdminCreateForm(forms.Form):
    """Form for creating new admin accounts (system_superadmin only)."""

    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'admin@example.com',
        })
    )
    first_name = forms.CharField(
        label='First Name',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'John',
        })
    )
    last_name = forms.CharField(
        label='Last Name',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Doe',
        })
    )
    role = forms.ChoiceField(
        label='Admin Role',
        choices=AtlasAdmin.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Strong password',
        })
    )
    password_confirm = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repeat password',
        })
    )

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor

        # Limit role choices based on actor's permissions
        if actor and not actor.is_system_superadmin:
            # Non-system superadmins can only create regular admins
            self.fields['role'].choices = [
                (AtlasAdmin.ROLE_ADMIN, 'Admin'),
            ]

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        if AtlasAdmin.objects.filter(email=email).exists():
            raise ValidationError('An admin with this email already exists.')
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            try:
                validate_password(password)
            except ValidationError as e:
                raise ValidationError(e.messages)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'Passwords do not match.')

        # Check if actor can create this role
        new_role = cleaned_data.get('role')
        if self.actor and new_role == AtlasAdmin.ROLE_SYSTEM_SUPERADMIN:
            if not self.actor.is_system_superadmin:
                raise ValidationError('Only System Super Admins can create other System Super Admins.')

        return cleaned_data

    def save(self):
        admin = AtlasAdmin(
            email=self.cleaned_data['email'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            role=self.cleaned_data['role'],
        )
        admin.set_password(self.cleaned_data['password'])
        admin.save()
        return admin


class AdminRoleChangeForm(forms.Form):
    """Form for changing admin roles (system_superadmin only)."""

    admin_id = forms.IntegerField(widget=forms.HiddenInput())
    new_role = forms.ChoiceField(
        choices=AtlasAdmin.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.target_admin = None

    def clean_admin_id(self):
        admin_id = self.cleaned_data.get('admin_id')
        try:
            self.target_admin = AtlasAdmin.objects.get(id=admin_id)
        except AtlasAdmin.DoesNotExist:
            raise ValidationError('Admin not found.')
        return admin_id

    def clean(self):
        cleaned_data = super().clean()
        new_role = cleaned_data.get('new_role')

        if self.target_admin and new_role and self.actor:
            if not self.actor.can_change_admin_role(self.target_admin, new_role):
                if not self.actor.is_system_superadmin:
                    raise ValidationError('Only System Super Admins can change admin roles.')
                elif self.target_admin.id == self.actor.id:
                    raise ValidationError('You cannot change your own role.')
                elif self.target_admin.is_system_superadmin:
                    # Check if last system superadmin
                    sys_count = AtlasAdmin.objects.filter(
                        role=AtlasAdmin.ROLE_SYSTEM_SUPERADMIN,
                        is_active=True
                    ).exclude(id=self.target_admin.id).count()
                    if sys_count == 0:
                        raise ValidationError('Cannot demote the last System Super Admin.')
                else:
                    raise ValidationError('You do not have permission to make this change.')

        return cleaned_data

    def save(self):
        old_role = self.target_admin.role
        self.target_admin.role = self.cleaned_data['new_role']
        self.target_admin.save()
        return self.target_admin, old_role, self.cleaned_data['new_role']


# =============================================================================
# Message Forms
# =============================================================================

class MessageForm(forms.ModelForm):
    """Form for creating/editing messages."""

    class Meta:
        model = Message
        fields = ['title', 'content', 'priority', 'target_all_users', 'target_roles', 'target_users',
                  'is_active', 'starts_at', 'expires_at']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Message title',
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Message content...',
            }),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'target_all_users': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'target_roles': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': 5,
            }),
            'target_users': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': 6,
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'starts_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
            }),
            'expires_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['target_roles'].queryset = Role.objects.filter(is_active=True).order_by('name')
        self.fields['target_users'].queryset = User.objects.filter(is_active=True).order_by('username')
        self.fields['target_roles'].required = False
        self.fields['target_users'].required = False
        self.fields['expires_at'].required = False
        self.fields['starts_at'].required = False


    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('target_all_users') and not cleaned_data.get('target_roles') and not cleaned_data.get('target_users'):
            raise ValidationError('Please target all users, at least one role, or at least one user.')
        return cleaned_data


# =============================================================================
# Search/Filter Forms
# =============================================================================

class UserSearchForm(forms.Form):
    """Form for searching/filtering users."""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by username, email, or name...',
        })
    )
    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        required=False,
        empty_label='All Roles',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_active = forms.ChoiceField(
        choices=[('', 'All'), ('true', 'Active'), ('false', 'Inactive')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
