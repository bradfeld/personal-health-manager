from django.db import models
from django.conf import settings

class UserSettings(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    sync_frequency = models.IntegerField(
        choices=[
            (1, 'Every hour'),
            (6, 'Every 6 hours'),
            (24, 'Daily'),
        ],
        default=24
    )
    distance_unit = models.CharField(
        max_length=2,
        choices=[('km', 'Kilometers'), ('mi', 'Miles')],
        default='mi'
    )
    
    def __str__(self):
        return f'Settings for {self.user.username}' 