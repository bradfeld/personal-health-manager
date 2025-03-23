import requests
from datetime import datetime, timedelta
from ..models import UserIntegration
from core.models import HealthMetrics, Activity
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class WhoopService:
    BASE_URL = 'https://api.prod.whoop.com/developer/v1'
    
    def __init__(self, user):
        self.user = user
        self.integration = UserIntegration.objects.get(user=user, provider='whoop')
    
    def refresh_token_if_needed(self):
        """Refresh the access token if it's expired or about to expire"""
        # Add a buffer of 5 minutes to avoid edge cases
        if self.integration.token_expires_at <= timezone.now() + timedelta(minutes=5):
            logger.info(f"Refreshing Whoop token for user {self.user.username}")
            try:
                response = requests.post(
                    'https://api.prod.whoop.com/oauth/oauth2/token',
                    data={
                        'grant_type': 'refresh_token',
                        'refresh_token': self.integration.refresh_token,
                        'client_id': settings.SOCIAL_AUTH_WHOOP_KEY,
                        'client_secret': settings.SOCIAL_AUTH_WHOOP_SECRET,
                    }
                )
                
                if response.status_code != 200:
                    error_msg = f"Failed to refresh Whoop token. Status: {response.status_code}, Response: {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                
                try:
                    data = response.json()
                    self.integration.access_token = data['access_token']
                    self.integration.refresh_token = data['refresh_token']
                    self.integration.token_expires_at = timezone.now() + timedelta(seconds=data['expires_in'])
                    self.integration.save()
                    logger.info(f"Successfully refreshed Whoop token for user {self.user.username}")
                except (KeyError, ValueError) as e:
                    error_msg = f"Invalid response format from Whoop: {str(e)}, Response: {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
            except Exception as e:
                logger.error(f"Error refreshing Whoop token: {str(e)}")
                raise
    
    def sync_data(self):
        """Sync all Whoop data for the user"""
        self.refresh_token_if_needed()
        
        # Sync workouts, recovery, and sleep data
        self.sync_workouts()
        self.sync_recovery()
        self.sync_sleep()
        
        # Update last sync time
        self.integration.last_sync = timezone.now()
        self.integration.save()
        logger.info(f"Completed Whoop sync for user {self.user.username}")
    
    def get_headers(self):
        """Get the headers for API requests"""
        return {
            'Authorization': f'Bearer {self.integration.access_token}',
            'Content-Type': 'application/json'
        }
    
    def sync_workouts(self):
        """Sync workout data from Whoop"""
        logger.info(f"Syncing Whoop workouts for user {self.user.username}")
        try:
            # Get data since last sync or last 30 days
            start_date = self.integration.last_sync or (timezone.now() - timedelta(days=30))
            start_date_str = start_date.isoformat()
            
            logger.info(f"Using start date: {start_date_str}")
            
            # Use the correct workout endpoint with the proper parameters
            logger.info(f"Making request to {self.BASE_URL}/activity/workout")
            response = requests.get(
                f'{self.BASE_URL}/activity/workout',
                headers=self.get_headers(),
                params={
                    'start': start_date_str,
                    'limit': 25  # Maximum allowed limit per documentation
                }
            )
            
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response headers: {response.headers}")
            
            if response.status_code != 200:
                logger.error(f"Error fetching Whoop workouts: {response.status_code} - {response.text}")
                return
            
            workouts_data = response.json()
            logger.info(f"Response data type: {type(workouts_data)}")
            logger.info(f"Response data: {workouts_data}")
            
            # The API returns records in a 'records' field
            workouts = workouts_data.get('records', [])
            logger.info(f"Retrieved {len(workouts)} Whoop workouts")
            
            for workout in workouts:
                # Convert Whoop workout to Activity model
                try:
                    start_time = datetime.fromisoformat(workout.get('start', '').replace('Z', '+00:00'))
                    
                    # Extract sport type from the workout data
                    sport_name = "Workout"  # Default value
                    if 'sport' in workout:
                        sport_name = workout.get('sport', {}).get('name', 'Workout')
                    
                    # Calculate duration from start and end times if duration not provided
                    duration_seconds = 0
                    if 'end' in workout and 'start' in workout:
                        end_time = datetime.fromisoformat(workout.get('end', '').replace('Z', '+00:00'))
                        duration = end_time - start_time
                        duration_seconds = duration.total_seconds()
                    
                    Activity.objects.update_or_create(
                        user=self.user,
                        source='whoop',
                        external_id=str(workout.get('id')),
                        defaults={
                            'date': start_time,
                            'activity_type': sport_name,
                            'duration': timedelta(seconds=duration_seconds),
                            'distance': workout.get('distance_meter', 0) / 1000,  # Convert to km
                            'calories': workout.get('calories'),
                        }
                    )
                except Exception as e:
                    logger.error(f"Error processing Whoop workout: {str(e)}")
                    logger.exception("Exception details:")
        except Exception as e:
            logger.error(f"Error syncing Whoop workouts: {str(e)}")
            logger.exception("Exception details:")
    
    def sync_recovery(self):
        """Sync recovery data from Whoop"""
        logger.info(f"Syncing Whoop recovery data for user {self.user.username}")
        try:
            # Get data since last sync or last 30 days
            start_date = self.integration.last_sync or (timezone.now() - timedelta(days=30))
            start_date_str = start_date.isoformat()
            
            logger.info(f"Using start date: {start_date_str}")
            
            # Use the correct recovery endpoint with the proper parameters
            logger.info(f"Making request to {self.BASE_URL}/recovery")
            response = requests.get(
                f'{self.BASE_URL}/recovery',
                headers=self.get_headers(),
                params={
                    'start': start_date_str,
                    'limit': 25  # Maximum allowed limit per documentation
                }
            )
            
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response headers: {response.headers}")
            
            if response.status_code != 200:
                logger.error(f"Error fetching Whoop recovery data: {response.status_code} - {response.text}")
                return
            
            recoveries_data = response.json()
            logger.info(f"Response data type: {type(recoveries_data)}")
            logger.info(f"Response data: {recoveries_data}")
            
            # The API returns records in a 'records' field
            recoveries = recoveries_data.get('records', [])
            logger.info(f"Retrieved {len(recoveries)} Whoop recovery records")
            
            for recovery in recoveries:
                try:
                    # Get the cycle_id from the recovery data
                    cycle_id = recovery.get('cycle_id')
                    
                    # Get the score data
                    score = recovery.get('score', {})
                    
                    # Parse date from the recovery data - use created_at as fallback
                    recovery_date = None
                    if 'created_at' in recovery:
                        recovery_date = datetime.fromisoformat(recovery.get('created_at', '').replace('Z', '+00:00')).date()
                    
                    if not recovery_date:
                        logger.warning(f"Could not determine date for recovery record: {recovery}")
                        continue
                    
                    # Update or create health metrics
                    HealthMetrics.objects.update_or_create(
                        user=self.user,
                        date=recovery_date,
                        defaults={
                            'resting_heart_rate': score.get('resting_heart_rate'),
                            'hrv': score.get('hrv_rmssd_milli'),
                            'recovery_score': score.get('recovery_score', 0),  # Already in percentage (0-100)
                            'source': 'whoop'
                        }
                    )
                except Exception as e:
                    logger.error(f"Error processing Whoop recovery: {str(e)}")
                    logger.exception("Exception details:")
        except Exception as e:
            logger.error(f"Error syncing Whoop recovery data: {str(e)}")
            logger.exception("Exception details:")
    
    def sync_sleep(self):
        """Sync sleep data from Whoop"""
        logger.info(f"Syncing Whoop sleep data for user {self.user.username}")
        try:
            # Get data since last sync or last 30 days
            start_date = self.integration.last_sync or (timezone.now() - timedelta(days=30))
            start_date_str = start_date.isoformat()
            
            logger.info(f"Using start date: {start_date_str}")
            
            # Use the correct sleep endpoint with the proper parameters
            logger.info(f"Making request to {self.BASE_URL}/activity/sleep")
            response = requests.get(
                f'{self.BASE_URL}/activity/sleep',
                headers=self.get_headers(),
                params={
                    'start': start_date_str,
                    'limit': 25  # Maximum allowed limit per documentation
                }
            )
            
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response headers: {response.headers}")
            
            if response.status_code != 200:
                logger.error(f"Error fetching Whoop sleep data: {response.status_code} - {response.text}")
                return
            
            sleeps_data = response.json()
            logger.info(f"Response data type: {type(sleeps_data)}")
            logger.info(f"Response data: {sleeps_data}")
            
            # The API returns records in a 'records' field
            sleeps = sleeps_data.get('records', [])
            logger.info(f"Retrieved {len(sleeps)} Whoop sleep records")
            
            for sleep in sleeps:
                try:
                    # Parse date from the sleep data - updated to match API response format
                    start_time = datetime.fromisoformat(sleep.get('start', '').replace('Z', '+00:00'))
                    end_time = datetime.fromisoformat(sleep.get('end', '').replace('Z', '+00:00'))
                    sleep_date = end_time.date()
                    
                    # Get sleep duration from the score data
                    score = sleep.get('score', {})
                    stage_summary = score.get('stage_summary', {})
                    
                    # Calculate total sleep time in milliseconds, then convert to seconds
                    total_sleep_ms = (
                        stage_summary.get('total_light_sleep_time_milli', 0) +
                        stage_summary.get('total_slow_wave_sleep_time_milli', 0) +
                        stage_summary.get('total_rem_sleep_time_milli', 0)
                    )
                    sleep_duration_seconds = total_sleep_ms / 1000
                    
                    # Update or create health metrics
                    metrics, created = HealthMetrics.objects.get_or_create(
                        user=self.user,
                        date=sleep_date,
                        defaults={
                            'sleep_duration': timedelta(seconds=sleep_duration_seconds),
                            'source': 'whoop'
                        }
                    )
                    
                    if not created:
                        metrics.sleep_duration = timedelta(seconds=sleep_duration_seconds)
                        metrics.save(update_fields=['sleep_duration'])
                except Exception as e:
                    logger.error(f"Error processing Whoop sleep: {str(e)}")
                    logger.exception("Exception details:")
        except Exception as e:
            logger.error(f"Error syncing Whoop sleep data: {str(e)}")
            logger.exception("Exception details:") 