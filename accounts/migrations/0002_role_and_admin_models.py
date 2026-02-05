"""
Migration: Add Role model, AtlasAdmin model, Messages, and update User model.

This migration:
1. Creates the Role model for SEC role management
2. Creates the UserRole junction table
3. Creates the AtlasAdmin model for separate admin authentication
4. Adds username and sec_user_id fields to User (if not exist)
5. Creates Message and MessageDismissal models for announcements
6. Updates AuditLog to support both User and Admin actors/targets
7. Updates PasswordResetToken to support both User and Admin
"""

from django.db import migrations, models, connection
import django.db.models.deletion
import django.utils.timezone


def column_exists(table_name, column_name):
    """Check if a column exists in a table."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
        """, [table_name, column_name])
        return cursor.fetchone() is not None


def table_exists(table_name):
    """Check if a table exists."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_name = %s
        """, [table_name])
        return cursor.fetchone() is not None


def add_username_if_not_exists(apps, schema_editor):
    """Add username column if it doesn't exist."""
    if not table_exists('atlas_user'):
        return  # Table doesn't exist, skip
    if not column_exists('atlas_user', 'username'):
        with connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE atlas_user
                ADD COLUMN username VARCHAR(150) NOT NULL DEFAULT ''
            """)


def add_sec_user_id_if_not_exists(apps, schema_editor):
    """Add sec_user_id column if it doesn't exist."""
    if not table_exists('atlas_user'):
        return  # Table doesn't exist, skip
    if not column_exists('atlas_user', 'sec_user_id'):
        with connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE atlas_user
                ADD COLUMN sec_user_id INTEGER NULL
            """)


def remove_role_if_exists(apps, schema_editor):
    """Remove role column from User if it exists."""
    if not table_exists('atlas_user'):
        return  # Table doesn't exist, skip
    if column_exists('atlas_user', 'role'):
        with connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE atlas_user DROP COLUMN role
            """)


def make_username_unique(apps, schema_editor):
    """Make username unique if not already."""
    if not table_exists('atlas_user'):
        return  # Table doesn't exist, skip
    if not column_exists('atlas_user', 'username'):
        return  # Column doesn't exist, skip
    # First, populate empty usernames with email prefix
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE atlas_user
            SET username = LOWER(SPLIT_PART(email, '@', 1))
            WHERE username = '' OR username IS NULL
        """)
        # Handle duplicates by appending id
        cursor.execute("""
            UPDATE atlas_user u1
            SET username = username || '_' || u1.id::text
            WHERE EXISTS (
                SELECT 1 FROM atlas_user u2
                WHERE u2.username = u1.username AND u2.id < u1.id
            )
        """)
        # Check if unique constraint already exists
        cursor.execute("""
            SELECT constraint_name FROM information_schema.table_constraints
            WHERE table_name = 'atlas_user'
            AND constraint_type = 'UNIQUE'
            AND constraint_name LIKE '%username%'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                ALTER TABLE atlas_user
                ADD CONSTRAINT atlas_user_username_unique UNIQUE (username)
            """)


def rename_audit_log_fields(apps, schema_editor):
    """Rename actor/target to actor_user/target_user if needed."""
    if not table_exists('atlas_audit_log'):
        return  # Table doesn't exist, skip
    if column_exists('atlas_audit_log', 'actor_id') and not column_exists('atlas_audit_log', 'actor_user_id'):
        with connection.cursor() as cursor:
            cursor.execute('ALTER TABLE atlas_audit_log RENAME COLUMN actor_id TO actor_user_id')
    if column_exists('atlas_audit_log', 'target_id') and not column_exists('atlas_audit_log', 'target_user_id'):
        with connection.cursor() as cursor:
            cursor.execute('ALTER TABLE atlas_audit_log RENAME COLUMN target_id TO target_user_id')


def add_audit_log_admin_fields(apps, schema_editor):
    """Add actor_admin_id and target_admin_id to audit log if not exist."""
    if not table_exists('atlas_audit_log'):
        return  # Table doesn't exist, skip
    if not column_exists('atlas_audit_log', 'actor_admin_id'):
        with connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE atlas_audit_log
                ADD COLUMN actor_admin_id BIGINT NULL REFERENCES atlas_admin(id) ON DELETE SET NULL
            """)
    if not column_exists('atlas_audit_log', 'target_admin_id'):
        with connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE atlas_audit_log
                ADD COLUMN target_admin_id BIGINT NULL REFERENCES atlas_admin(id) ON DELETE SET NULL
            """)


def update_password_reset_token(apps, schema_editor):
    """Update password reset token table for admin support."""
    if not table_exists('atlas_password_reset_token'):
        return  # Table doesn't exist, skip
    # Make user_id nullable
    if column_exists('atlas_password_reset_token', 'user_id'):
        with connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE atlas_password_reset_token
                ALTER COLUMN user_id DROP NOT NULL
            """)
    # Add admin_id if not exists
    if not column_exists('atlas_password_reset_token', 'admin_id'):
        with connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE atlas_password_reset_token
                ADD COLUMN admin_id BIGINT NULL REFERENCES atlas_admin(id) ON DELETE CASCADE
            """)


def noop(apps, schema_editor):
    """No-op for reverse migrations."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        # =====================================================================
        # Role Model - Local representation of SEC roles
        # =====================================================================
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('description', models.TextField(blank=True, default='')),
                ('external_id', models.IntegerField(blank=True, db_index=True, help_text='Links to sec_role.id in the WebAPI schema', null=True)),
                ('is_system_role', models.BooleanField(default=False, help_text="System roles like 'public' cannot be removed from users")),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Role',
                'verbose_name_plural': 'Roles',
                'db_table': 'atlas_role',
                'ordering': ['name'],
            },
        ),

        # =====================================================================
        # AtlasAdmin Model - Separate admin authentication
        # =====================================================================
        migrations.CreateModel(
            name='AtlasAdmin',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('password', models.CharField(max_length=128)),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('role', models.CharField(choices=[('admin', 'Admin'), ('super_admin', 'Super Admin'), ('system_superadmin', 'System Super Admin')], default='admin', max_length=30)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('last_login', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Atlas Admin',
                'verbose_name_plural': 'Atlas Admins',
                'db_table': 'atlas_admin',
                'ordering': ['-role', '-created_at'],
            },
        ),

        # =====================================================================
        # Update User Model - using RunPython to handle existing columns
        # =====================================================================
        migrations.RunPython(add_username_if_not_exists, noop),
        migrations.RunPython(add_sec_user_id_if_not_exists, noop),
        migrations.RunPython(remove_role_if_exists, noop),

        # =====================================================================
        # UserRole Junction Model
        # =====================================================================
        migrations.CreateModel(
            name='UserRole',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('origin', models.CharField(choices=[('ATLAS', 'Atlas Admin'), ('SEC', 'SEC System'), ('SYSTEM', 'System')], default='ATLAS', max_length=20)),
                ('granted_at', models.DateTimeField(auto_now_add=True)),
                ('granted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='roles_granted', to='accounts.atlasadmin')),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_roles', to='accounts.role')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_roles', to='accounts.user')),
            ],
            options={
                'verbose_name': 'User Role',
                'verbose_name_plural': 'User Roles',
                'db_table': 'atlas_user_role',
                'ordering': ['role__name'],
                'unique_together': {('user', 'role')},
            },
        ),

        # =====================================================================
        # Message Model - In-app announcements
        # =====================================================================
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('content', models.TextField()),
                ('priority', models.CharField(choices=[('low', 'Low'), ('normal', 'Normal'), ('high', 'High')], default='normal', max_length=20)),
                ('target_all_users', models.BooleanField(default=True)),
                ('is_active', models.BooleanField(default=True)),
                ('starts_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='messages_created', to='accounts.atlasadmin')),
                ('target_roles', models.ManyToManyField(blank=True, related_name='messages', to='accounts.role')),
            ],
            options={
                'verbose_name': 'Message',
                'verbose_name_plural': 'Messages',
                'db_table': 'atlas_message',
                'ordering': ['-priority', '-created_at'],
            },
        ),

        # MessageDismissal
        migrations.CreateModel(
            name='MessageDismissal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dismissed_at', models.DateTimeField(auto_now_add=True)),
                ('message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dismissals', to='accounts.message')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dismissed_messages', to='accounts.user')),
            ],
            options={
                'verbose_name': 'Message Dismissal',
                'verbose_name_plural': 'Message Dismissals',
                'db_table': 'atlas_message_dismissal',
                'unique_together': {('user', 'message')},
            },
        ),

        # =====================================================================
        # Update AuditLog - using RunPython for safety
        # =====================================================================
        migrations.RunPython(rename_audit_log_fields, noop),
        migrations.RunPython(add_audit_log_admin_fields, noop),

        # =====================================================================
        # Update PasswordResetToken - using RunPython for safety
        # =====================================================================
        migrations.RunPython(update_password_reset_token, noop),

        # =====================================================================
        # Make username unique after data migration
        # =====================================================================
        migrations.RunPython(make_username_unique, noop),
    ]
