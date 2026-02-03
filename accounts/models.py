from django.db import models
import bcrypt

class AtlasUser(models.Model):
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128)

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