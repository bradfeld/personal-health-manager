from django.contrib import admin
from .models import UserIntegration

@admin.register(UserIntegration)
class UserIntegrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'last_sync', 'token_expires_at')
    list_filter = ('provider',)
    search_fields = ('user__username', 'external_id') 