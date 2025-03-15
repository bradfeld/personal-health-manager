from django.contrib import admin
from .models import Activity, HealthMetrics

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'activity_type', 'duration', 'distance', 'source')
    list_filter = ('activity_type', 'source', 'date')
    search_fields = ('user__username', 'activity_type', 'external_id')
    date_hierarchy = 'date'

@admin.register(HealthMetrics)
class HealthMetricsAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'resting_heart_rate', 'hrv', 'recovery_score', 'source')
    list_filter = ('source', 'date')
    search_fields = ('user__username',)
    date_hierarchy = 'date' 