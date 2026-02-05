# Generated migration for Atlas Config

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('password', models.CharField(max_length=128)),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('prefix', models.CharField(blank=True, choices=[('', ''), ('mr', 'Mr.'), ('mrs', 'Mrs.'), ('ms', 'Ms.'), ('dr', 'Dr.'), ('prof', 'Prof.')], default='', max_length=10)),
                ('affiliation', models.CharField(blank=True, default='', max_length=255)),
                ('role', models.CharField(choices=[('user', 'User'), ('admin', 'Admin'), ('super_admin', 'Super Admin')], default='user', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('last_login', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'User',
                'verbose_name_plural': 'Users',
                'db_table': 'atlas_user',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PasswordResetToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=64, unique=True)),
                ('is_used', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='password_reset_tokens', to='accounts.user')),
            ],
            options={
                'verbose_name': 'Password Reset Token',
                'verbose_name_plural': 'Password Reset Tokens',
                'db_table': 'atlas_password_reset_token',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('actor_email', models.EmailField(blank=True, default='', max_length=254)),
                ('target_email', models.EmailField(blank=True, default='', max_length=254)),
                ('action', models.CharField(choices=[('login', 'User Login'), ('logout', 'User Logout'), ('login_failed', 'Login Failed'), ('user_created', 'User Created'), ('user_updated', 'User Updated'), ('user_deactivated', 'User Deactivated'), ('user_activated', 'User Activated'), ('role_changed', 'Role Changed'), ('password_changed', 'Password Changed'), ('password_reset_requested', 'Password Reset Requested'), ('password_reset_completed', 'Password Reset Completed'), ('profile_updated', 'Profile Updated')], max_length=50)),
                ('description', models.TextField(blank=True, default='')),
                ('previous_state', models.TextField(blank=True, default='')),
                ('new_state', models.TextField(blank=True, default='')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='actions_performed', to='accounts.user')),
                ('target', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='actions_received', to='accounts.user')),
            ],
            options={
                'verbose_name': 'Audit Log',
                'verbose_name_plural': 'Audit Logs',
                'db_table': 'atlas_audit_log',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['action', 'created_at'], name='atlas_audit_action_d45c5c_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['actor', 'created_at'], name='atlas_audit_actor_i_f39de9_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['target', 'created_at'], name='atlas_audit_target__fafaa6_idx'),
        ),
    ]
