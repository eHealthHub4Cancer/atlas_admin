from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import AdminUser, AtlasUser, Permission, UserProfile


DEFAULT_PERMISSIONS = [
    "view_dashboards",
    "manage_profiles",
    "export_reports",
    "request_dataset",
]

DEFAULT_USERS = [
    {
        "username": "jordan.researcher",
        "role": AtlasUser.ROLE_RESEARCHER,
        "display_name": "Jordan Blake",
        "email": "jordan.researcher@ehealthhub.org",
        "affiliation": "Cancer Informatics Lab",
        "prefix": "dr",
        "password": "ChangeMe123!",
        "permissions": ["view_dashboards", "export_reports", "request_dataset"],
    },
    {
        "username": "sam.student",
        "role": AtlasUser.ROLE_STUDENT,
        "display_name": "Sam Carter",
        "email": "sam.student@ehealthhub.org",
        "affiliation": "Graduate Program",
        "prefix": "mr",
        "password": "ChangeMe123!",
        "permissions": ["view_dashboards"],
    },
    {
        "username": "taylor.guest",
        "role": AtlasUser.ROLE_GUEST,
        "display_name": "Taylor Reed",
        "email": "taylor.guest@ehealthhub.org",
        "affiliation": "Community Partner",
        "prefix": "ms",
        "password": "ChangeMe123!",
        "permissions": ["view_dashboards"],
    },
]

DEFAULT_ADMIN = {
    "name": "Alex Morgan",
    "email": "admin@ehealthhub.org",
    "password": "AdminChangeMe123!",
    "affiliation": "eHealthHub Operations",
    "is_super_admin": True,
}


class Command(BaseCommand):
    help = "Seed default permissions, users, and admin account for Atlas Admin."

    def handle(self, *args, **options):
        created_permissions = []
        created_users = []

        with transaction.atomic():
            for permission_name in DEFAULT_PERMISSIONS:
                permission, created = Permission.objects.get_or_create(name=permission_name)
                if created:
                    created_permissions.append(permission_name)

            permission_map = {permission.name: permission for permission in Permission.objects.all()}

            for user_data in DEFAULT_USERS:
                user, created = AtlasUser.objects.get_or_create(
                    username=user_data["username"],
                    defaults={
                        "role": user_data["role"],
                        "is_disabled": False,
                    },
                )
                if created:
                    user.set_password(user_data["password"])
                    user.role = user_data["role"]
                    user.save()
                    created_users.append(user.username)

                profile, _ = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        "display_name": user_data["display_name"],
                        "email": user_data["email"],
                        "affiliation": user_data["affiliation"],
                        "prefix": user_data["prefix"],
                    },
                )

                if profile.email != user_data["email"]:
                    profile.email = user_data["email"]
                    profile.display_name = user_data["display_name"]
                    profile.affiliation = user_data["affiliation"]
                    profile.prefix = user_data["prefix"]
                    profile.save()

                user.permissions.set([permission_map[name] for name in user_data["permissions"]])

            admin_user, admin_created = AdminUser.objects.get_or_create(
                email=DEFAULT_ADMIN["email"],
                defaults={
                    "name": DEFAULT_ADMIN["name"],
                    "affiliation": DEFAULT_ADMIN["affiliation"],
                    "is_admin": True,
                    "is_super_admin": DEFAULT_ADMIN["is_super_admin"],
                },
            )
            if admin_created:
                admin_user.set_password(DEFAULT_ADMIN["password"])
                admin_user.save()

        self.stdout.write(self.style.SUCCESS("Seed data complete."))
        if created_permissions:
            self.stdout.write(f"Permissions created: {', '.join(created_permissions)}")
        if created_users:
            self.stdout.write(f"Users created: {', '.join(created_users)}")
        if admin_created:
            self.stdout.write("Admin user created: admin@ehealthhub.org")
