import requests
from datetime import datetime, timezone, timedelta
from ..models import UserIntegration
from core.models import HealthMetrics
from django.conf import settings

class WhoopService:
    BASE_URL = 'https://api.whoop.com/v1'
    
    def __init__(self, user):
        self.user = user
        self.integration = UserIntegration.objects.get(user=user, provider='whoop')
    
    def refresh_token_if_needed(self):
        if self.integration.token_expires_at <= datetime.now(timezone.utc):
            response = requests.post(
                f'{self.BASE_URL}/oauth/token',
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': self.integration.refresh_token,
                    'client_id': settings.SOCIAL_AUTH_WHOOP_KEY,
                    'client_secret': settings.SOCIAL_AUTH_WHOOP_SECRET,
                }
            )
            data = response.json()
            
            self.integration.access_token = data['access_token']
            self.integration.refresh_token = data['refresh_token']
            self.integration.token_expires_at = datetime.now(timezone.utc) + \
                                              timedelta(seconds=data['expires_in'])
            self.integration.save()
    
    def sync_data(self):
        self.refresh_token_if_needed()
        
        headers = {
            'Authorization': f'Bearer {self.integration.access_token}'
        }
        
        # Get data since last sync
        start_date = self.integration.last_sync or (datetime.now() - timedelta(days=30))
        
        # Get recovery data
        response = requests.get(
            f'{self.BASE_URL}/recovery',
            headers=headers,
            params={'start': start_date.isoformat()}
        )
        
        for metric_data in response.json().get('records', []):
            HealthMetrics.objects.update_or_create(
                user=self.user,
                date=datetime.fromisoformat(metric_data['date']).date(),
                defaults={
                    'resting_heart_rate': metric_data.get('resting_heart_rate'),
                    'hrv': metric_data.get('hrv'),
                    'recovery_score': metric_data.get('recovery_score'),
                    'source': 'whoop'
                }
            )
        
        # Get sleep data
        response = requests.get(
            f'{self.BASE_URL}/sleep',
            headers=headers,
            params={'start': start_date.isoformat()}
        )
        
        for sleep_data in response.json().get('records', []):
            sleep_date = datetime.fromisoformat(sleep_data['end']).date()
            HealthMetrics.objects.update_or_create(
                user=self.user,
                date=sleep_date,
                defaults={
                    'sleep_duration': timedelta(seconds=sleep_data.get('duration', 0)),
                    'source': 'whoop'
                }
            )
        
        self.integration.last_sync = datetime.now(timezone.utc)
        self.integration.save() 