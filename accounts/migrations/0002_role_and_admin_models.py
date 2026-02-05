"""
Migration: Add Role model, AtlasAdmin model, Messages, and update User model.

This migration:
1. Creates the Role model for SEC role management
2. Creates the UserRole junction table
3. Creates the AtlasAdmin model for separate admin authentication
4. Adds username and sec_user_id fields to User
5. Creates Message and MessageDismissal models for announcements
6. Updates AuditLog to support both User and Admin actors/targets
7. Updates PasswordResetToken to support both User and Admin
"""

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


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
        # Update User Model
        # =====================================================================
        # Add username field
        migrations.AddField(
            model_name='user',
            name='username',
            field=models.CharField(default='', help_text='Lowercase username, synced to sec_user.login', max_length=150),
            preserve_default=False,
        ),
        # Add sec_user_id for SEC sync
        migrations.AddField(
            model_name='user',
            name='sec_user_id',
            field=models.IntegerField(blank=True, help_text='Links to sec_user.id in the WebAPI schema', null=True),
        ),
        # Remove the old role field from User (now managed separately via AtlasAdmin)
        migrations.RemoveField(
            model_name='user',
            name='role',
        ),

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

        # Add roles M2M to User
        migrations.AddField(
            model_name='user',
            name='roles',
            field=models.ManyToManyField(related_name='users', through='accounts.UserRole', to='accounts.role'),
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
        # Update AuditLog to support User and Admin actors/targets
        # =====================================================================
        migrations.RenameField(
            model_name='auditlog',
            old_name='actor',
            new_name='actor_user',
        ),
        migrations.RenameField(
            model_name='auditlog',
            old_name='target',
            new_name='target_user',
        ),
        migrations.AddField(
            model_name='auditlog',
            name='actor_admin',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='actions_performed', to='accounts.atlasadmin'),
        ),
        migrations.AddField(
            model_name='auditlog',
            name='target_admin',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='actions_received', to='accounts.atlasadmin'),
        ),

        # =====================================================================
        # Update PasswordResetToken to support Admin
        # =====================================================================
        migrations.RenameField(
            model_name='passwordresettoken',
            old_name='user',
            new_name='user',
        ),
        migrations.AlterField(
            model_name='passwordresettoken',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='password_reset_tokens', to='accounts.user'),
        ),
        migrations.AddField(
            model_name='passwordresettoken',
            name='admin',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='password_reset_tokens', to='accounts.atlasadmin'),
        ),

        # =====================================================================
        # Make username unique after initial data migration
        # =====================================================================
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(help_text='Lowercase username, synced to sec_user.login', max_length=150, unique=True),
        ),
    ]
