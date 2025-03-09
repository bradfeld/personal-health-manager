from django.db import models
from django.conf import settings

class UserIntegration(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    provider = models.CharField(max_length=20)  # 'strava' or 'whoop'
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    token_expires_at = models.DateTimeField()
    last_sync = models.DateTimeField(null=True, blank=True)
    external_id = models.CharField(max_length=100, null=True, blank=True)  # For storing provider-specific user IDs

    class Meta:
        unique_together = ('user', 'provider') 