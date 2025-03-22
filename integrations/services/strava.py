import requests
from datetime import datetime, timezone, timedelta
from ..models import UserIntegration
from core.models import Activity
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class StravaService:
    BASE_URL = 'https://www.strava.com/api/v3'
    
    def __init__(self, user):
        self.user = user
        self.integration = UserIntegration.objects.get(user=user, provider='strava')
    
    def refresh_token_if_needed(self):
        if self.integration.token_expires_at <= datetime.now(timezone.utc):
            logger.info("Strava token needs refresh")
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
                error_msg = f"Failed to refresh Strava token. Status: {response.status_code}, Response: {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            try:
                data = response.json()
                self.integration.access_token = data['access_token']
                self.integration.refresh_token = data['refresh_token']
                self.integration.token_expires_at = datetime.fromtimestamp(
                    data['expires_at'],
                    tz=timezone.utc
                )
                self.integration.save()
                logger.info("Successfully refreshed Strava token")
            except (KeyError, ValueError) as e:
                error_msg = f"Invalid response format from Strava: {str(e)}, Response: {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
    
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
                    'average_heart_rate': activity_data.get('average_heartrate'),
                    'average_cadence': activity_data.get('average_cadence'),
                }
            )
        
        self.integration.last_sync = datetime.now(timezone.utc)
        self.integration.save() 