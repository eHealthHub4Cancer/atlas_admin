"""
Atlas Config - Migrate and Seed Command

Runs migrations and seeds the super admin in one command.
Useful for Docker entrypoints.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Run migrations and seed the super admin'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-seed',
            action='store_true',
            help='Skip seeding the super admin',
        )

    def handle(self, *args, **options):
        self.stdout.write('Running database migrations...')
        call_command('migrate', verbosity=1)
        self.stdout.write(self.style.SUCCESS('Migrations complete.'))

        if not options['no_seed']:
            self.stdout.write('\nSeeding super admin...')
            try:
                call_command('seed_super_admin')
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Super admin seeding skipped: {e}')
                )

        self.stdout.write(self.style.SUCCESS('\nSetup complete!'))
