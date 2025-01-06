from datetime import datetime, timezone, timedelta
from .models import UserIntegration

def save_strava_token(backend, user, response, *args, **kwargs):
    if backend.name == 'strava':
        # Get or create UserIntegration for this user and Strava
        integration, created = UserIntegration.objects.update_or_create(
            user=user,
            provider='strava',
            defaults={
                'access_token': response.get('access_token'),
                'refresh_token': response.get('refresh_token'),
                'token_expires_at': datetime.fromtimestamp(
                    response.get('expires_at', 0),
                    tz=timezone.utc
                )
            }
        ) 

def save_whoop_token(backend, user, response, *args, **kwargs):
    if backend.name == 'whoop':
        integration, created = UserIntegration.objects.update_or_create(
            user=user,
            provider='whoop',
            defaults={
                'access_token': response.get('access_token'),
                'refresh_token': response.get('refresh_token'),
                'expires_at': timezone.now() + timedelta(seconds=response.get('expires_in', 0)),
                'token_type': response.get('token_type', 'Bearer')
            }
        ) 