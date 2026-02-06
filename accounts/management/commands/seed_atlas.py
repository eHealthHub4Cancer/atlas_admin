"""
Seed command for Atlas Admin system.

Creates default:
- Prefixes (Mr., Mrs., Ms., Dr., Prof.)
- Roles (guest, student, researcher, clinician)
- Super Admin account
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import Prefix, Role, AtlasAdmin


class Command(BaseCommand):
    help = "Seed default prefixes, roles, and super admin for Atlas Admin."

    def handle(self, *args, **options):
        with transaction.atomic():
            # Seed Prefixes
            prefixes_data = [
                {'name': 'mr', 'display_name': 'Mr.', 'sort_order': 1},
                {'name': 'mrs', 'display_name': 'Mrs.', 'sort_order': 2},
                {'name': 'ms', 'display_name': 'Ms.', 'sort_order': 3},
                {'name': 'dr', 'display_name': 'Dr.', 'sort_order': 4},
                {'name': 'prof', 'display_name': 'Prof.', 'sort_order': 5},
            ]
            
            created_prefixes = []
            for prefix_data in prefixes_data:
                prefix, created = Prefix.objects.get_or_create(
                    name=prefix_data['name'],
                    defaults={
                        'display_name': prefix_data['display_name'],
                        'sort_order': prefix_data['sort_order'],
                        'is_active': True,
                    }
                )
                if created:
                    created_prefixes.append(prefix.display_name)
            
            # Seed Roles
            roles_data = [
                {
                    'name': 'guest',
                    'description': 'Guest user with limited access to view public data',
                    'sort_order': 1
                },
                {
                    'name': 'student',
                    'description': 'Student user with access to educational resources',
                    'sort_order': 2
                },
                {
                    'name': 'researcher',
                    'description': 'Researcher with access to research data and tools',
                    'sort_order': 3
                },
                {
                    'name': 'clinician',
                    'description': 'Clinical professional with access to clinical data',
                    'sort_order': 4
                },
            ]
            
            created_roles = []
            for role_data in roles_data:
                role, created = Role.objects.get_or_create(
                    name=role_data['name'],
                    defaults={
                        'description': role_data['description'],
                        'sort_order': role_data['sort_order'],
                        'is_active': True,
                    }
                )
                if created:
                    created_roles.append(role.name)
            
            # Seed Super Admin
            admin_email = 'admin@ehealthatlas.org'
            admin, admin_created = AtlasAdmin.objects.get_or_create(
                email=admin_email,
                defaults={
                    'first_name': 'System',
                    'last_name': 'Administrator',
                    'role': AtlasAdmin.ROLE_SYSTEM_SUPERADMIN,
                    'is_active': True,
                }
            )
            
            if admin_created:
                admin.set_password('Admin@123')  # Default password - MUST be changed
                admin.save()
                self.stdout.write(self.style.SUCCESS(
                    f'\n✓ Super Admin created: {admin_email}'
                ))
                self.stdout.write(self.style.WARNING(
                    f'  Default password: Admin@123 (CHANGE THIS IMMEDIATELY!)'
                ))
            
            # Summary
            self.stdout.write(self.style.SUCCESS('\n=== Seed Summary ==='))
            
            if created_prefixes:
                self.stdout.write(self.style.SUCCESS(
                    f'✓ Prefixes created: {", ".join(created_prefixes)}'
                ))
            else:
                self.stdout.write('  Prefixes: Already exist')
            
            if created_roles:
                self.stdout.write(self.style.SUCCESS(
                    f'✓ Roles created: {", ".join(created_roles)}'
                ))
            else:
                self.stdout.write('  Roles: Already exist')
            
            self.stdout.write(self.style.SUCCESS(
                f'\nTotal Prefixes: {Prefix.objects.count()}'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'Total Roles: {Role.objects.count()}'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'Total Admins: {AtlasAdmin.objects.count()}\n'
            ))
