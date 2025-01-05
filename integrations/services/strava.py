import requests
from datetime import datetime, timezone, timedelta
from ..models import UserIntegration
from core.models import Activity
from django.conf import settings

class StravaService:
    BASE_URL = 'https://www.strava.com/api/v3'
    
    def __init__(self, user):
        self.user = user
        self.integration = UserIntegration.objects.get(user=user, provider='strava')
    
    def refresh_token_if_needed(self):
        if self.integration.token_expires_at <= datetime.now(timezone.utc):
            response = requests.post(
                'https://www.strava.com/oauth/token',
                data={
                    'client_id': settings.SOCIAL_AUTH_STRAVA_KEY,
                    'client_secret': settings.SOCIAL_AUTH_STRAVA_SECRET,
                    'grant_type': 'refresh_token',
                    'refresh_token': self.integration.refresh_token
                }
            )
            
            if response.status_code != 200:
                raise Exception('Failed to refresh Strava token')
            
            data = response.json()
            self.integration.access_token = data['access_token']
            self.integration.refresh_token = data['refresh_token']
            self.integration.token_expires_at = datetime.fromtimestamp(
                data['expires_at'],
                tz=timezone.utc
            )
            self.integration.save()
    
    def sync_activities(self):
        self.refresh_token_if_needed()
        
        headers = {
            'Authorization': f'Bearer {self.integration.access_token}'
        }
        
        # Get activities after last sync
        params = {
            'after': int(self.integration.last_sync.timestamp()) if self.integration.last_sync else None,
            'per_page': 100
        }
        
        response = requests.get(f'{self.BASE_URL}/athlete/activities', headers=headers, params=params)
        activities = response.json()
        
        for activity_data in activities:
            Activity.objects.update_or_create(
                user=self.user,
                source='strava',
                external_id=str(activity_data['id']),
                defaults={
                    'date': datetime.strptime(activity_data['start_date'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc),
                    'activity_type': activity_data['type'],
                    'duration': timedelta(seconds=activity_data['moving_time']),
                    'distance': activity_data['distance'] / 1000,
                    'calories': activity_data.get('calories'),
                }
            )
        
        self.integration.last_sync = datetime.now(timezone.utc)
        self.integration.save() 