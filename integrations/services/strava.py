import requests
from datetime import datetime, timedelta
from ..models import UserIntegration
from core.models import Activity
from django.conf import settings
from django.utils import timezone
import logging
import json

logger = logging.getLogger(__name__)

class StravaService:
    BASE_URL = 'https://www.strava.com/api/v3'
    
    def __init__(self, user):
        self.user = user
        self.integration = UserIntegration.objects.get(user=user, provider='strava')
    
    def refresh_token_if_needed(self):
        if self.integration.token_expires_at <= timezone.now():
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
                # Convert from timestamp to timezone-aware datetime
                expires_at = datetime.fromtimestamp(data['expires_at'])
                self.integration.token_expires_at = timezone.make_aware(expires_at)
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
        logger.info(f"Syncing activities after timestamp: {after_timestamp}, last_sync: {self.integration.last_sync}")
        
        params = {
            'after': after_timestamp,
            'per_page': 100
        }
        
        logger.info(f"Making request to {self.BASE_URL}/athlete/activities with params: {params}")
        response = requests.get(f'{self.BASE_URL}/athlete/activities', headers=headers, params=params)
        if response.status_code != 200:
            error_msg = f"Failed to get activities from Strava. Status: {response.status_code}, Response: {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # Log the raw response for debugging
        try:
            response_text = response.text
            logger.info(f"Raw response from Strava (first 500 chars): {response_text[:500]}")
        except Exception as e:
            logger.error(f"Error logging raw response: {str(e)}")
            
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
                logger.info(f"Getting detailed data for activity: {activity_id}")
                detailed_url = f"{self.BASE_URL}/activities/{activity_id}"
                logger.info(f"Making request to {detailed_url}")
                detailed_response = requests.get(detailed_url, headers=headers)
                
                detailed_data = {}
                if detailed_response.status_code == 200:
                    try:
                        detailed_data = detailed_response.json()
                        # Log detailed response for debugging (truncate if too large)
                        detailed_json = json.dumps(detailed_data)
                        if len(detailed_json) > 500:
                            logger.info(f"Detailed activity data for {activity_id} (truncated): {detailed_json[:500]}...")
                        else:
                            logger.info(f"Detailed activity data for {activity_id}: {detailed_json}")
                        
                        # Merge the detailed data with the basic data, with detailed data taking precedence
                        activity_data.update(detailed_data)
                    except Exception as e:
                        logger.error(f"Error parsing detailed activity data: {str(e)}, raw response: {detailed_response.text[:200]}")
                else:
                    logger.warning(f"Failed to get detailed data for activity {activity_id}. Status: {detailed_response.status_code}, Response: {detailed_response.text[:200]}")
                
                # Extract heart rate and cadence from the data
                heart_rate = activity_data.get('average_heartrate')
                if heart_rate is None:
                    # Try alternative field names
                    heart_rate = activity_data.get('average_heart_rate')
                    
                    # Log all keys that might be related to heart rate
                    hr_related_keys = [k for k in activity_data.keys() if 'heart' in k.lower()]
                    if hr_related_keys:
                        logger.info(f"Found heart rate related keys: {hr_related_keys}")
                        for key in hr_related_keys:
                            logger.info(f"Value for {key}: {activity_data.get(key)}")
                    
                    if heart_rate is None and ('heartrate' in str(activity_data) or 'heart_rate' in str(activity_data)):
                        logger.warning(f"Heart rate data might be available with a different field name. Activity keys: {list(activity_data.keys())}")
                
                cadence = activity_data.get('average_cadence')
                # Log all keys that might be related to cadence
                cadence_related_keys = [k for k in activity_data.keys() if 'cadence' in k.lower()]
                if cadence_related_keys:
                    logger.info(f"Found cadence related keys: {cadence_related_keys}")
                    for key in cadence_related_keys:
                        logger.info(f"Value for {key}: {activity_data.get(key)}")
                        
                if cadence is None and 'cadence' in str(activity_data):
                    logger.warning(f"Cadence data might be available with a different field name. Activity keys: {list(activity_data.keys())}")
                
                # Log what we found
                logger.info(f"Activity {activity_id} heart rate: {heart_rate}, cadence: {cadence}")
                
                # Add device info if available
                device_name = None
                if 'device_name' in activity_data:
                    device_name = activity_data.get('device_name')
                    logger.info(f"Activity {activity_id} recorded with device: {device_name}")
                
                # Update the activity in our database
                # Parse the datetime and make it timezone-aware
                start_date = datetime.strptime(activity_data['start_date'], '%Y-%m-%dT%H:%M:%SZ')
                start_date_aware = timezone.make_aware(start_date)
                
                activity, created = Activity.objects.update_or_create(
                    user=self.user,
                    source='strava',
                    external_id=str(activity_id),
                    defaults={
                        'date': start_date_aware,
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
        
        self.integration.last_sync = timezone.now()
        self.integration.save()
        
        return {
            'total': activities_updated,
            'heart_rate': activities_with_hr,
            'cadence': activities_with_cadence
        } 