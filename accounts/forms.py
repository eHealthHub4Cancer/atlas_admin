"""
Atlas Config - Forms

Forms for authentication, user management, and profile updates.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import User


class LoginForm(forms.Form):
    """User login form."""

    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'you@example.com',
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
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            try:
                user = User.objects.get(email=email.lower())
                if not user.is_active:
                    raise ValidationError('This account has been deactivated.')
                if not user.check_password(password):
                    raise ValidationError('Invalid email or password.')
                cleaned_data['user'] = user
            except User.DoesNotExist:
                raise ValidationError('Invalid email or password.')

        return cleaned_data


class SignupForm(forms.Form):
    """User registration form."""

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
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'you@example.com',
        })
    )
    affiliation = forms.CharField(
        label='Affiliation',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'University / Organization',
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

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower()
            if User.objects.filter(email=email).exists():
                raise ValidationError('An account with this email already exists.')
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

        return cleaned_data

    def save(self):
        """Create and return a new user."""
        user = User(
            email=self.cleaned_data['email'].lower(),
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            affiliation=self.cleaned_data.get('affiliation', ''),
            role=User.ROLE_USER,
        )
        user.set_password(self.cleaned_data['password'])
        user.save()
        return user


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
    """Change password form for authenticated users."""

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

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_current_password(self):
        current_password = self.cleaned_data.get('current_password')
        if current_password and not self.user.check_password(current_password):
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
        """Update the user's password."""
        self.user.set_password(self.cleaned_data['new_password'])
        self.user.save()
        return self.user


class ProfileForm(forms.ModelForm):
    """User profile update form."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'prefix', 'affiliation']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'prefix': forms.Select(attrs={
                'class': 'form-select',
            }),
            'affiliation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'University / Organization',
            }),
        }


class UserEditForm(forms.ModelForm):
    """Admin form for editing user details."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'prefix', 'affiliation', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'prefix': forms.Select(attrs={'class': 'form-select'}),
            'affiliation': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower()
            existing = User.objects.filter(email=email)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError('A user with this email already exists.')
        return email


class RoleChangeForm(forms.Form):
    """Form for changing user roles (super_admin only)."""

    user_id = forms.IntegerField(widget=forms.HiddenInput())
    new_role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.target_user = None

    def clean_user_id(self):
        user_id = self.cleaned_data.get('user_id')
        try:
            self.target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ValidationError('User not found.')
        return user_id

    def clean(self):
        cleaned_data = super().clean()
        new_role = cleaned_data.get('new_role')

        if self.target_user and new_role and self.actor:
            if not self.actor.can_change_role(self.target_user, new_role):
                if not self.actor.is_super_admin:
                    raise ValidationError('Only Super Admins can change user roles.')
                elif self.target_user.is_super_admin and new_role != User.ROLE_SUPER_ADMIN:
                    # Check if this is the last super admin
                    super_admin_count = User.objects.filter(
                        role=User.ROLE_SUPER_ADMIN,
                        is_active=True
                    ).exclude(id=self.target_user.id).count()
                    if super_admin_count == 0:
                        raise ValidationError('Cannot demote the last Super Admin.')
                else:
                    raise ValidationError('You do not have permission to make this change.')

        return cleaned_data

    def save(self):
        """Update the user's role."""
        old_role = self.target_user.role
        new_role = self.cleaned_data['new_role']

        self.target_user.role = new_role
        self.target_user.save()

        return self.target_user, old_role, new_role
