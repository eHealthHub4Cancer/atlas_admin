from django.db import models
import bcrypt


class Permission(models.Model):
    name = models.CharField(max_length=100, unique=True)
    external_id = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'atlas_permission'
        managed = True
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'

    def __str__(self):
        return self.name

class AtlasUser(models.Model):
    ROLE_RESEARCHER = 'researcher'
    ROLE_GUEST = 'guest'
    ROLE_STUDENT = 'student'

    ROLE_CHOICES = (
        (ROLE_RESEARCHER, 'Researcher'),
        (ROLE_GUEST, 'Guest'),
        (ROLE_STUDENT, 'Student'),
    )

    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_GUEST)
    is_disabled = models.BooleanField(default=False)
    permissions = models.ManyToManyField(Permission, blank=True, related_name='users')

    def set_password(self, raw_password):
        # OHDSI compatibility: prefix=b"2a" and rounds=10
        salt = bcrypt.gensalt(rounds=10, prefix=b"2a")
        self.password = bcrypt.hashpw(raw_password.encode('utf-8'), salt).decode('utf-8')

    def check_password(self, raw_password):
        return bcrypt.checkpw(raw_password.encode('utf-8'), self.password.encode('utf-8'))
    
    class Meta:
        db_table = 'atlas_user'
        managed = True
        verbose_name = 'Atlas User'
        verbose_name_plural = 'Atlas Users'

    def __str__(self):
        return self.username


class UserProfile(models.Model):
    PREFIX_CHOICES = (
        ("mr", "Mr."),
        ("mrs", "Mrs."),
        ("ms", "Ms."),
        ("dr", "Dr."),
        ("prof", "Prof."),
    )

    user = models.OneToOneField(AtlasUser, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    prefix = models.CharField(max_length=10, choices=PREFIX_CHOICES, blank=True)

    class Meta:
        db_table = "atlas_user_profile"
        managed = True
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return self.display_name
