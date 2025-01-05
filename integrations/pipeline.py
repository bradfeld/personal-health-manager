from datetime import datetime, timezone
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