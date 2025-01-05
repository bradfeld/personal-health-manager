from django.db import models
from django.conf import settings

class Activity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateTimeField()
    activity_type = models.CharField(max_length=50)
    duration = models.DurationField()
    distance = models.FloatField(null=True, blank=True)
    calories = models.IntegerField(null=True, blank=True)
    source = models.CharField(max_length=20)  # 'strava' or 'whoop'
    external_id = models.CharField(max_length=100)
    
    class Meta:
        verbose_name_plural = 'activities'

class HealthMetrics(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField()
    resting_heart_rate = models.IntegerField(null=True, blank=True)
    hrv = models.FloatField(null=True, blank=True)  # Heart Rate Variability
    sleep_duration = models.DurationField(null=True, blank=True)
    recovery_score = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=20)  # 'whoop'
    
    class Meta:
        verbose_name_plural = 'health metrics' 