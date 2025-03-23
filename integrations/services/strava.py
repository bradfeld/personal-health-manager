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
                        # Log the keys in detailed data for debugging
                        logger.info(f"Detailed activity data keys for {activity_id}: {list(detailed_data.keys())}")
                        
                        # Merge the detailed data with the basic data, with detailed data taking precedence
                        activity_data.update(detailed_data)
                    except Exception as e:
                        logger.error(f"Error parsing detailed activity data: {str(e)}, raw response: {detailed_response.text[:200]}")
                else:
                    logger.warning(f"Failed to get detailed data for activity {activity_id}. Status: {detailed_response.status_code}, Response: {detailed_response.text[:200]}")
                
                # Log all keys that might be related to heart rate and cadence
                for key in activity_data.keys():
                    if 'heart' in key.lower() or 'cadence' in key.lower():
                        logger.info(f"Found metric key: {key}, value: {activity_data.get(key)}")
                
                # Extract heart rate - check for 'average_heartrate' (Strava API format)
                heart_rate = None
                if 'average_heartrate' in activity_data and activity_data['average_heartrate'] is not None:
                    heart_rate = activity_data['average_heartrate']
                    logger.info(f"Found heart rate from 'average_heartrate': {heart_rate}")
                elif 'has_heartrate' in activity_data and activity_data['has_heartrate']:
                    logger.warning(f"Activity {activity_id} has heart rate data but 'average_heartrate' is missing")
                
                # Extract cadence
                cadence = None
                if 'average_cadence' in activity_data and activity_data['average_cadence'] is not None:
                    cadence = activity_data['average_cadence']
                    logger.info(f"Found cadence from 'average_cadence': {cadence}")
                
                # Log the final values we're using
                logger.info(f"Activity {activity_id} final values - heart rate: {heart_rate}, cadence: {cadence}")
                
                # Update the activity in our database
                # Parse the datetime and make it timezone-aware
                start_date = datetime.strptime(activity_data['start_date'], '%Y-%m-%dT%H:%M:%SZ')
                start_date_aware = timezone.make_aware(start_date)
                
                # Prepare defaults dict with non-null values only
                defaults = {
                    'date': start_date_aware,
                    'activity_type': activity_data['type'],
                    'duration': timedelta(seconds=activity_data['moving_time']),
                    'distance': activity_data['distance'] / 1000,
                    'source': 'strava'
                }
                
                # Add optional fields only if they have values
                if 'calories' in activity_data and activity_data['calories'] is not None:
                    defaults['calories'] = activity_data['calories']
                
                if heart_rate is not None:
                    defaults['average_heart_rate'] = heart_rate
                
                if cadence is not None:
                    defaults['average_cadence'] = cadence
                
                activity, created = Activity.objects.update_or_create(
                    user=self.user,
                    source='strava',
                    external_id=str(activity_id),
                    defaults=defaults
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
                import traceback
                logger.error(traceback.format_exc())
        
        logger.info(f"Sync completed. Updated {activities_updated} activities. Heart rate data for {activities_with_hr}, cadence data for {activities_with_cadence}")
        
        self.integration.last_sync = timezone.now()
        self.integration.save()
        
        return {
            'total': activities_updated,
            'heart_rate': activities_with_hr,
            'cadence': activities_with_cadence
        } 