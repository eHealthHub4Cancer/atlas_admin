# Generated migration for Prefix model and User/Role updates

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_role_and_admin_models'),
    ]

    operations = [
        # Create Prefix model
        migrations.CreateModel(
            name='Prefix',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text="Short code for the prefix (e.g., 'mr', 'dr')", max_length=20, unique=True)),
                ('display_name', models.CharField(help_text="Display text for the prefix (e.g., 'Mr.', 'Dr.')", max_length=50)),
                ('is_active', models.BooleanField(default=True, help_text='Whether this prefix is available for selection')),
                ('sort_order', models.IntegerField(default=0, help_text='Order in which to display this prefix')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Prefix',
                'verbose_name_plural': 'Prefixes',
                'db_table': 'atlas_prefix',
                'ordering': ['sort_order', 'display_name'],
            },
        ),
        
        # Update Role model - remove SEC sync fields
        migrations.RemoveField(
            model_name='role',
            name='external_id',
        ),
        migrations.RemoveField(
            model_name='role',
            name='is_system_role',
        ),
        
        # Add new fields to Role
        migrations.AddField(
            model_name='role',
            name='is_active',
            field=models.BooleanField(default=True, help_text='Whether this role is available for assignment'),
        ),
        migrations.AddField(
            model_name='role',
            name='sort_order',
            field=models.IntegerField(default=0, help_text='Order in which to display this role'),
        ),
        
        # Update Role meta ordering
        migrations.AlterModelOptions(
            name='role',
            options={'ordering': ['sort_order', 'name'], 'verbose_name': 'Role', 'verbose_name_plural': 'Roles'},
        ),
        
        # Update User model - remove sec_user_id
        migrations.RemoveField(
            model_name='user',
            name='sec_user_id',
        ),
        
        # Change User.prefix from CharField to ForeignKey
        # First, rename the old field
        migrations.RenameField(
            model_name='user',
            old_name='prefix',
            new_name='prefix_old',
        ),
        
        # Add new ForeignKey field
        migrations.AddField(
            model_name='user',
            name='prefix',
            field=models.ForeignKey(
                blank=True,
                help_text='Name prefix (Mr., Dr., etc.)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='users',
                to='accounts.prefix'
            ),
        ),
        
        # Remove old prefix field
        migrations.RemoveField(
            model_name='user',
            name='prefix_old',
        ),
    ]
