"""
Atlas Config - Serializers

REST API serializers for User, AtlasAdmin, Role, Prefix, and related models.
"""

from rest_framework import serializers
from .models import User, AtlasAdmin, Role, Prefix, Category, UserRole


# =============================================================================
# Prefix Serializers
# =============================================================================

class PrefixSerializer(serializers.ModelSerializer):
    """Serializer for Prefix model."""
    
    class Meta:
        model = Prefix
        fields = ['id', 'name', 'display_name', 'is_active', 'sort_order', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class PrefixCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating prefixes."""
    
    class Meta:
        model = Prefix
        fields = ['name', 'display_name', 'is_active', 'sort_order']
    
    def validate_name(self, value):
        """Ensure name is lowercase and unique."""
        value = value.lower().strip()
        instance = self.instance
        if instance:
            # Update - check uniqueness excluding current instance
            if Prefix.objects.exclude(pk=instance.pk).filter(name=value).exists():
                raise serializers.ValidationError("A prefix with this name already exists.")
        else:
            # Create - check uniqueness
            if Prefix.objects.filter(name=value).exists():
                raise serializers.ValidationError("A prefix with this name already exists.")
        return value


# =============================================================================
# Category Serializers
# =============================================================================

class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model."""

    user_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Category
        fields = ['id', 'name', 'display_name', 'description', 'is_active', 'sort_order', 'created_at', 'updated_at', 'user_count']
        read_only_fields = ['created_at', 'updated_at']


class CategoryCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating categories."""

    class Meta:
        model = Category
        fields = ['name', 'display_name', 'description', 'is_active', 'sort_order']

    def validate_name(self, value):
        """Ensure name is lowercase and unique."""
        value = value.lower().strip()
        instance = self.instance
        if instance:
            if Category.objects.exclude(pk=instance.pk).filter(name=value).exists():
                raise serializers.ValidationError("A category with this name already exists.")
        else:
            if Category.objects.filter(name=value).exists():
                raise serializers.ValidationError("A category with this name already exists.")
        return value


# =============================================================================
# Role Serializers
# =============================================================================

class RoleSerializer(serializers.ModelSerializer):
    """Serializer for Role model."""
    
    user_count = serializers.IntegerField(read_only=True, required=False)
    
    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'is_active', 'sort_order', 'created_at', 'updated_at', 'user_count']
        read_only_fields = ['created_at', 'updated_at']


class RoleCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating roles."""
    
    class Meta:
        model = Role
        fields = ['name', 'description', 'is_active', 'sort_order']
    
    def validate_name(self, value):
        """Ensure name is lowercase and unique."""
        value = value.lower().strip()
        instance = self.instance
        if instance:
            # Update - check uniqueness excluding current instance
            if Role.objects.exclude(pk=instance.pk).filter(name=value).exists():
                raise serializers.ValidationError("A role with this name already exists.")
        else:
            # Create - check uniqueness
            if Role.objects.filter(name=value).exists():
                raise serializers.ValidationError("A role with this name already exists.")
        return value


# =============================================================================
# User Serializers
# =============================================================================

class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""

    roles = RoleSerializer(many=True, read_only=True)
    prefix_display = serializers.CharField(source='prefix.display_name', read_only=True, allow_null=True)
    category_display = serializers.CharField(source='category.display_name', read_only=True, allow_null=True)
    role_names = serializers.ListField(source='role_names', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'prefix', 'prefix_display', 'category', 'category_display',
            'affiliation', 'is_active',
            'roles', 'role_names', 'created_at', 'updated_at', 'last_login'
        ]
        read_only_fields = ['created_at', 'updated_at', 'last_login']


class UserCreateSerializer(serializers.Serializer):
    """Serializer for user signup/creation."""
    
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    prefix = serializers.PrimaryKeyRelatedField(
        queryset=Prefix.objects.filter(is_active=True),
        required=False,
        allow_null=True
    )
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(is_active=True),
        required=False,
        allow_null=True
    )
    affiliation = serializers.CharField(max_length=255, required=False, allow_blank=True)
    role = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.filter(is_active=True),
        required=False,
        allow_null=True
    )
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    def validate_username(self, value):
        """Validate username is unique and lowercase."""
        value = value.lower().strip()
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value
    
    def validate_email(self, value):
        """Validate email is unique."""
        value = value.lower().strip()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value
    
    def validate(self, data):
        """Validate passwords match."""
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({'password_confirm': "Passwords do not match."})
        return data


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'prefix', 'category', 'affiliation', 'email']
    
    def validate_email(self, value):
        """Validate email is unique (excluding current user)."""
        value = value.lower().strip()
        if self.instance:
            if User.objects.exclude(pk=self.instance.pk).filter(email=value).exists():
                raise serializers.ValidationError("This email is already registered.")
        return value


# =============================================================================
# Admin Serializers
# =============================================================================

class AtlasAdminSerializer(serializers.ModelSerializer):
    """Serializer for AtlasAdmin model."""
    
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = AtlasAdmin
        fields = [
            'id', 'email', 'first_name', 'last_name', 'role', 'role_display',
            'is_active', 'created_at', 'updated_at', 'last_login'
        ]
        read_only_fields = ['created_at', 'updated_at', 'last_login']


# =============================================================================
# Authentication Serializers
# =============================================================================

class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class AdminLoginSerializer(serializers.Serializer):
    """Serializer for admin login."""
    
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class SignupSerializer(serializers.Serializer):
    """Serializer for user signup (frontend API)."""

    username = serializers.CharField(max_length=150)
    display_name = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    affiliation = serializers.CharField(max_length=255, required=False, allow_blank=True)
    prefix = serializers.CharField(max_length=20, required=False, allow_blank=True)
    category = serializers.CharField(max_length=100, required=False, allow_blank=True)
    role = serializers.CharField(max_length=50)
    password1 = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True)
    
    def validate_username(self, value):
        """Validate username."""
        value = value.lower().strip()
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value
    
    def validate_email(self, value):
        """Validate email."""
        value = value.lower().strip()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value
    
    def validate(self, data):
        """Validate passwords match."""
        if data.get('password1') != data.get('password2'):
            raise serializers.ValidationError({'password2': "Passwords do not match."})
        return data


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change."""
    
    current_password = serializers.CharField(write_only=True)
    new_password1 = serializers.CharField(write_only=True, min_length=8)
    new_password2 = serializers.CharField(write_only=True)
    
    def validate(self, data):
        """Validate new passwords match."""
        if data.get('new_password1') != data.get('new_password2'):
            raise serializers.ValidationError({'new_password2': "Passwords do not match."})
        return data


class AuthSessionSerializer(serializers.Serializer):
    """Serializer for authentication session."""
    
    user_id = serializers.IntegerField()
    username = serializers.CharField(allow_null=True)
    role = serializers.CharField()
    is_admin = serializers.BooleanField()
    is_super_admin = serializers.BooleanField()
    display_name = serializers.CharField(allow_null=True)
    email = serializers.CharField(allow_null=True)


# =============================================================================
# Utility Serializers
# =============================================================================

class ProfileUpdateSerializer(serializers.Serializer):
    """Serializer for profile updates (frontend API)."""
    
    display_name = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    affiliation = serializers.CharField(max_length=255, required=False, allow_blank=True)
    prefix = serializers.CharField(max_length=20, required=False, allow_blank=True)


class BulkRoleAssignSerializer(serializers.Serializer):
    """Serializer for bulk role assignment."""
    
    user_ids = serializers.ListField(child=serializers.IntegerField())
    role_ids = serializers.ListField(child=serializers.IntegerField())


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for admin dashboard stats."""
    
    total_users = serializers.IntegerField()
    admin_users = serializers.IntegerField()
    roles_count = serializers.IntegerField()
    active_users = serializers.IntegerField()
    disabled_users = serializers.IntegerField()


class PaginatedResponseSerializer(serializers.Serializer):
    """Generic paginated response serializer."""
    
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    results = serializers.ListField()
