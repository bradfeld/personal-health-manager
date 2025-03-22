import requests
from datetime import datetime, timezone, timedelta
from ..models import UserIntegration
from core.models import Activity
from django.conf import settings
import logging
import json

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
        logger.info(f"Starting sync activities for user {self.user.username}")
        self.refresh_token_if_needed()
        
        headers = {
            'Authorization': f'Bearer {self.integration.access_token}'
        }
        
        # Get activities after last sync
        after_timestamp = int(self.integration.last_sync.timestamp()) if self.integration.last_sync else None
        logger.info(f"Syncing activities after timestamp: {after_timestamp}")
        
        params = {
            'after': after_timestamp,
            'per_page': 100
        }
        
        response = requests.get(f'{self.BASE_URL}/athlete/activities', headers=headers, params=params)
        if response.status_code != 200:
            error_msg = f"Failed to get activities from Strava. Status: {response.status_code}, Response: {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
            
        activities = response.json()
        logger.info(f"Found {len(activities)} activities to sync")
        
        activities_updated = 0
        activities_with_hr = 0
        activities_with_cadence = 0
        
        for activity_data in activities:
            try:
                # Log basic activity info
                activity_id = activity_data.get('id')
                activity_name = activity_data.get('name', 'Unknown')
                activity_type = activity_data.get('type', 'Unknown')
                activity_date = activity_data.get('start_date', 'Unknown')
                
                logger.info(f"Processing activity: {activity_id} - {activity_name} ({activity_type}) on {activity_date}")
                
                # Get detailed activity data to access heart rate and cadence
                detailed_response = requests.get(f'{self.BASE_URL}/activities/{activity_id}', headers=headers)
                
                detailed_data = {}
                if detailed_response.status_code == 200:
                    detailed_data = detailed_response.json()
                    # Log detailed response for debugging (truncate if too large)
                    detailed_json = json.dumps(detailed_data)
                    if len(detailed_json) > 500:
                        logger.info(f"Detailed activity data for {activity_id} (truncated): {detailed_json[:500]}...")
                    else:
                        logger.info(f"Detailed activity data for {activity_id}: {detailed_json}")
                    
                    # Merge the detailed data with the basic data, with detailed data taking precedence
                    activity_data.update(detailed_data)
                else:
                    logger.warning(f"Failed to get detailed data for activity {activity_id}. Status: {detailed_response.status_code}, Response: {detailed_response.text}")
                
                # Extract heart rate and cadence from the data
                heart_rate = activity_data.get('average_heartrate')
                if heart_rate is None:
                    # Try alternative field names
                    heart_rate = activity_data.get('average_heart_rate')
                    if heart_rate is None and 'heartrate' in str(activity_data):
                        logger.warning(f"Heart rate data might be available with a different field name: {str(activity_data)[:200]}")
                
                cadence = activity_data.get('average_cadence')
                if cadence is None and 'cadence' in str(activity_data):
                    logger.warning(f"Cadence data might be available with a different field name: {str(activity_data)[:200]}")
                
                # Log what we found
                logger.info(f"Activity {activity_id} heart rate: {heart_rate}, cadence: {cadence}")
                
                # Add device info if available
                device_name = None
                if 'device_name' in activity_data:
                    device_name = activity_data.get('device_name')
                    logger.info(f"Activity {activity_id} recorded with device: {device_name}")
                
                # Update the activity in our database
                activity, created = Activity.objects.update_or_create(
                    user=self.user,
                    source='strava',
                    external_id=str(activity_id),
                    defaults={
                        'date': datetime.strptime(activity_data['start_date'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc),
                        'activity_type': activity_data['type'],
                        'duration': timedelta(seconds=activity_data['moving_time']),
                        'distance': activity_data['distance'] / 1000,
                        'calories': activity_data.get('calories'),
                        'average_heart_rate': heart_rate,
                        'average_cadence': cadence,
                    }
                )
                
                activities_updated += 1
                if heart_rate is not None:
                    activities_with_hr += 1
                if cadence is not None:
                    activities_with_cadence += 1
                
                if created:
                    logger.info(f"Created new activity: {activity_id}")
                else:
                    logger.info(f"Updated existing activity: {activity_id}")
                
            except Exception as e:
                logger.error(f"Error processing activity {activity_data.get('id', 'unknown')}: {str(e)}")
        
        logger.info(f"Sync completed. Updated {activities_updated} activities. Heart rate data for {activities_with_hr}, cadence data for {activities_with_cadence}")
        
        self.integration.last_sync = datetime.now(timezone.utc)
        self.integration.save()
        
        return {
            'total': activities_updated,
            'heart_rate': activities_with_hr,
            'cadence': activities_with_cadence
        } 