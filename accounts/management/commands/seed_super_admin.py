"""
Atlas Config - Seed Super Admin Command

Creates the initial super admin user from environment variables.
"""

import os
from django.core.management.base import BaseCommand, CommandError
from accounts.models import User, AuditLog


class Command(BaseCommand):
    help = 'Create the initial super admin user from environment variables'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if super admin already exists',
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

    def handle(self, *args, **options):
        # Get credentials from environment or arguments
        email = options.get('email') or os.environ.get('SUPER_ADMIN_EMAIL')
        password = options.get('password') or os.environ.get('SUPER_ADMIN_PASSWORD')
        first_name = os.environ.get('SUPER_ADMIN_FIRST_NAME', 'Admin')
        last_name = os.environ.get('SUPER_ADMIN_LAST_NAME', 'User')

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

        # Check if super admin already exists
        existing_super_admin = User.objects.filter(role=User.ROLE_SUPER_ADMIN).first()
        if existing_super_admin and not options['force']:
            self.stdout.write(
                self.style.WARNING(
                    f'A super admin already exists: {existing_super_admin.email}\n'
                    f'Use --force to create another one.'
                )
            )
            return

        # Check if email already exists
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            if existing_user.role == User.ROLE_SUPER_ADMIN:
                self.stdout.write(
                    self.style.SUCCESS(f'Super admin already exists: {email}')
                )
                return

            if options['force']:
                # Promote existing user to super admin
                old_role = existing_user.role
                existing_user.role = User.ROLE_SUPER_ADMIN
                existing_user.set_password(password)
                existing_user.save()

                AuditLog.log(
                    action=AuditLog.ACTION_ROLE_CHANGED,
                    target=existing_user,
                    description=f'User promoted to super_admin via seed command',
                    previous_state=f'role={old_role}',
                    new_state=f'role={User.ROLE_SUPER_ADMIN}'
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Existing user {email} promoted to super admin and password updated.'
                    )
                )
                return
            else:
                raise CommandError(
                    f'User with email {email} already exists with role: {existing_user.role}. '
                    f'Use --force to promote them to super admin.'
                )

        # Create new super admin
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=User.ROLE_SUPER_ADMIN,
            is_active=True,
        )
        user.set_password(password)
        user.save()

        # Log the creation
        AuditLog.log(
            action=AuditLog.ACTION_USER_CREATED,
            target=user,
            description='Super admin created via seed command',
            new_state=f'role={User.ROLE_SUPER_ADMIN}'
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Super admin created successfully!\n'
                f'  Email: {email}\n'
                f'  Name: {first_name} {last_name}\n'
                f'  Role: Super Admin'
            )
        )
