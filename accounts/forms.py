# forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import AtlasUser, Permission

class AtlasSignUpForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
        help_text='Your password must contain at least 8 characters.'
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}),
        help_text='Enter the same password as before, for verification.'
    )

    class Meta:
        model = AtlasUser
        fields = ('username', 'role')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Username'
            }),
            'role': forms.Select(attrs={
                'class': 'form-select',
            }),
        }

    def clean_username(self):
        """Ensure username is unique"""
        username = self.cleaned_data.get('username')
        if AtlasUser.objects.filter(username=username).exists():
            raise ValidationError('A user with that username already exists.')
        return username

    def clean_password1(self):
        """Validate password strength"""
        password1 = self.cleaned_data.get('password1')
        if password1:
            try:
                validate_password(password1)
            except ValidationError as e:
                raise ValidationError(e.messages)
        return password1

    def clean_password2(self):
        """Check that the two password entries match"""
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError("The two password fields didn't match.")
        return password2

    def save(self, commit=True):
        """Save the user with bcrypt-hashed password"""
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class PasswordChangeForm(forms.Form):
    current_password = forms.CharField(
        label='Current Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Current password'})
    )
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New password'})
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'})
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_current_password(self):
        current_password = self.cleaned_data.get('current_password')
        if current_password and not self.user.check_password(current_password):
            raise ValidationError('Current password is incorrect.')
        return current_password

    def clean_new_password1(self):
        password1 = self.cleaned_data.get('new_password1')
        if password1:
            try:
                validate_password(password1)
            except ValidationError as e:
                raise ValidationError(e.messages)
        return password1

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError("The two password fields didn't match.")
        return password2

    def save(self, commit=True):
        self.user.set_password(self.cleaned_data['new_password1'])
        if commit:
            self.user.save()
        return self.user


class AdminUserPermissionsForm(forms.Form):
    user_id = forms.IntegerField(widget=forms.HiddenInput)
    is_disabled = forms.BooleanField(required=False)
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select form-select-sm'})
    )

    def __init__(self, *args, **kwargs):
        permissions_queryset = kwargs.pop('permissions_queryset', Permission.objects.none())
        super().__init__(*args, **kwargs)
        self.fields['permissions'].queryset = permissions_queryset


class BulkGrantPermissionsForm(forms.Form):
    user_ids = forms.ModelMultipleChoiceField(
        queryset=AtlasUser.objects.none(),
        required=True,
        widget=forms.SelectMultiple(attrs={'class': 'form-select'})
    )
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.none(),
        required=True,
        widget=forms.SelectMultiple(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        users_queryset = kwargs.pop('users_queryset', AtlasUser.objects.none())
        permissions_queryset = kwargs.pop('permissions_queryset', Permission.objects.none())
        super().__init__(*args, **kwargs)
        self.fields['user_ids'].queryset = users_queryset
        self.fields['permissions'].queryset = permissions_queryset
