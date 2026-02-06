# Migration to add Category model and User.category FK

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_add_prefix_update_models'),
    ]

    operations = [
        # Create Category model
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text="Category name (e.g., 'student', 'researcher')", max_length=100, unique=True)),
                ('display_name', models.CharField(help_text="Display text for the category (e.g., 'Student', 'Researcher')", max_length=150)),
                ('description', models.TextField(blank=True, default='', help_text='Description of this category')),
                ('is_active', models.BooleanField(default=True, help_text='Whether this category is available for selection')),
                ('sort_order', models.IntegerField(default=0, help_text='Order in which to display this category')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Category',
                'verbose_name_plural': 'Categories',
                'db_table': 'atlas_category',
                'ordering': ['sort_order', 'display_name'],
            },
        ),

        # Add category FK to User
        migrations.AddField(
            model_name='user',
            name='category',
            field=models.ForeignKey(
                blank=True,
                help_text='User category (Student, Researcher, etc.)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='users',
                to='accounts.category',
            ),
        ),
    ]
