"""
Atlas Config - Seed System Superadmin Command

Creates the initial system superadmin (AtlasAdmin) from environment variables.
This is the highest level administrator who can manage all other admins.

Usage:
    python manage.py seed_super_admin
    python manage.py seed_super_admin --email=admin@example.com --password=secret
    python manage.py seed_super_admin --force
"""

import os
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse
from accounts.models import AtlasAdmin, AuditLog


class Command(BaseCommand):
    help = 'Create the initial system superadmin from environment variables'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if a system superadmin already exists',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Override SUPER_ADMIN_EMAIL environment variable',
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Override SUPER_ADMIN_PASSWORD environment variable',
        )
        parser.add_argument(
            '--first-name',
            type=str,
            help='Override SUPER_ADMIN_FIRST_NAME environment variable',
        )
        parser.add_argument(
            '--last-name',
            type=str,
            help='Override SUPER_ADMIN_LAST_NAME environment variable',
        )

    def handle(self, *args, **options):
        # Get credentials from environment or arguments
        email = options.get('email') or os.environ.get('SUPER_ADMIN_EMAIL')
        password = options.get('password') or os.environ.get('SUPER_ADMIN_PASSWORD')
        first_name = options.get('first_name') or os.environ.get('SUPER_ADMIN_FIRST_NAME', 'System')
        last_name = options.get('last_name') or os.environ.get('SUPER_ADMIN_LAST_NAME', 'Admin')

        if not email:
            raise CommandError(
                'SUPER_ADMIN_EMAIL environment variable is not set. '
                'Set it in .env or pass --email argument.'
            )

        if not password:
            raise CommandError(
                'SUPER_ADMIN_PASSWORD environment variable is not set. '
                'Set it in .env or pass --password argument.'
            )

        email = email.lower().strip()

        # Check if system superadmin already exists
        existing_system_superadmin = AtlasAdmin.objects.filter(
            role=AtlasAdmin.ROLE_SYSTEM_SUPERADMIN
        ).first()

        if existing_system_superadmin and not options['force']:
            self.stdout.write(
                self.style.WARNING(
                    f'A system superadmin already exists: {existing_system_superadmin.email}\n'
                    f'Use --force to create another one.'
                )
            )
            return

        # Check if admin with this email already exists
        existing_admin = AtlasAdmin.objects.filter(email=email).first()
        if existing_admin:
            if existing_admin.role == AtlasAdmin.ROLE_SYSTEM_SUPERADMIN:
                self.stdout.write(
                    self.style.SUCCESS(f'System superadmin already exists: {email}')
                )
                return

            if options['force']:
                # Promote existing admin to system superadmin
                old_role = existing_admin.role
                existing_admin.role = AtlasAdmin.ROLE_SYSTEM_SUPERADMIN
                existing_admin.set_password(password)
                existing_admin.save()

                # Log the promotion
                AuditLog.log(
                    action=AuditLog.ACTION_ADMIN_ROLE_CHANGED,
                    target_admin=existing_admin,
                    description=(
                        f'Admin promoted to system_superadmin via seed command (from {old_role})'
                    ),
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Existing admin {email} promoted to system superadmin and password updated.'
                    )
                )
                return
            else:
                raise CommandError(
                    f'Admin with email {email} already exists with role: {existing_admin.role}. '
                    f'Use --force to promote them to system superadmin.'
                )

        # Create new system superadmin
        admin = AtlasAdmin(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=AtlasAdmin.ROLE_SYSTEM_SUPERADMIN,
            is_active=True,
        )
        admin.set_password(password)
        admin.save()

        # Log the creation
        AuditLog.log(
            action=AuditLog.ACTION_ADMIN_CREATED,
            target_admin=admin,
            description='System superadmin created via seed command',
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n{"="*50}\n'
                f'System Superadmin created successfully!\n'
                f'{"="*50}\n'
                f'  Email:      {email}\n'
                f'  Name:       {first_name} {last_name}\n'
                f'  Role:       System Superadmin\n'
                f'{"="*50}\n'
                f"\nYou can now log in at {reverse('admin_login')}\n"
            )
        )
