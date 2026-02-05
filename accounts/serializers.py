from rest_framework import serializers
from .models import AtlasUser, UserProfile, AdminUser, Permission


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'external_id', 'description']


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['id', 'display_name', 'email', 'affiliation', 'prefix', 'created_at', 'updated_at']


class AtlasUserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    permissions = PermissionSerializer(many=True, read_only=True)

    class Meta:
        model = AtlasUser
        fields = ['id', 'username', 'role', 'is_disabled', 'created_at', 'updated_at', 'profile', 'permissions']


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminUser
        fields = ['id', 'name', 'email', 'affiliation', 'is_admin', 'is_super_admin']


class CombinedUserSerializer(serializers.Serializer):
    """Serializer for combined atlas + admin users view"""
    id = serializers.IntegerField()
    username = serializers.CharField(allow_null=True)
    display_name = serializers.CharField()
    email = serializers.CharField()
    role = serializers.CharField()
    is_disabled = serializers.BooleanField()
    is_admin = serializers.BooleanField()
    is_super_admin = serializers.BooleanField()
    user_type = serializers.CharField()
    permissions = PermissionSerializer(many=True)


class ActivityLogSerializer(serializers.Serializer):
    """Serializer for activity log entries"""
    id = serializers.IntegerField()
    action = serializers.CharField()
    summary = serializers.CharField()
    timestamp = serializers.DateTimeField()
    status = serializers.CharField()


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for admin dashboard stats"""
    total_users = serializers.IntegerField()
    admin_users = serializers.IntegerField()
    roles_count = serializers.IntegerField()
    active_users = serializers.IntegerField()
    disabled_users = serializers.IntegerField()


class AuthSessionSerializer(serializers.Serializer):
    """Serializer for authentication session"""
    user_id = serializers.IntegerField()
    username = serializers.CharField(allow_null=True)
    role = serializers.CharField()
    is_admin = serializers.BooleanField()
    is_super_admin = serializers.BooleanField()
    display_name = serializers.CharField(allow_null=True)
    email = serializers.CharField(allow_null=True)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class SignupSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    display_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    affiliation = serializers.CharField(max_length=255, required=False, allow_blank=True)
    prefix = serializers.ChoiceField(choices=['', 'Mr.', 'Mrs.', 'Ms.', 'Dr.', 'Prof.'], required=False)
    role = serializers.ChoiceField(choices=['researcher', 'guest', 'student'], default='guest')
    password1 = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True)

    def validate_username(self, value):
        if AtlasUser.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_email(self, value):
        if UserProfile.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def validate(self, data):
        if data.get('password1') != data.get('password2'):
            raise serializers.ValidationError({'password2': "Passwords do not match."})
        return data


class ProfileUpdateSerializer(serializers.Serializer):
    display_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    affiliation = serializers.CharField(max_length=255, required=False, allow_blank=True)
    prefix = serializers.ChoiceField(choices=['', 'Mr.', 'Mrs.', 'Ms.', 'Dr.', 'Prof.'], required=False)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password1 = serializers.CharField(write_only=True, min_length=8)
    new_password2 = serializers.CharField(write_only=True)

    def validate(self, data):
        if data.get('new_password1') != data.get('new_password2'):
            raise serializers.ValidationError({'new_password2': "Passwords do not match."})
        return data


class BulkGrantSerializer(serializers.Serializer):
    user_ids = serializers.ListField(child=serializers.IntegerField())
    permission_ids = serializers.ListField(child=serializers.IntegerField())


class UserUpdateSerializer(serializers.Serializer):
    is_disabled = serializers.BooleanField(required=False)
    permissions = serializers.ListField(child=serializers.IntegerField(), required=False)
    type = serializers.ChoiceField(choices=['atlas', 'admin'])
