import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
import requests
from core.models import Activity
from integrations.models import UserIntegration
from integrations.services.strava import StravaService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fix heart rate and cadence data for existing Strava activities'

    def handle(self, *args, **options):
        self.stdout.write('Starting to fix heart rate and cadence data for existing Strava activities')
        
        # Get all user integrations for Strava
        integrations = UserIntegration.objects.filter(provider='strava')
        self.stdout.write(f'Found {len(integrations)} Strava integrations')
        
        total_fixed = 0
        
        for integration in integrations:
            user = integration.user
            self.stdout.write(f'Processing user: {user.username}')
            
            try:
                # Create Strava service
                service = StravaService(user)
                
                # Refresh token if needed
                service.refresh_token_if_needed()
                
                # Get activities without heart rate or cadence
                activities = Activity.objects.filter(
                    user=user,
                    source='strava',
                    average_heart_rate__isnull=True
                )
                
                self.stdout.write(f'Found {len(activities)} activities without heart rate data')
                
                headers = {
                    'Authorization': f'Bearer {integration.access_token}'
                }
                
                fixed_count = 0
                
                for activity in activities:
                    try:
                        activity_id = activity.external_id
                        self.stdout.write(f'Fixing data for activity: {activity_id}')
                        
                        # Get detailed activity data
                        detailed_url = f"{service.BASE_URL}/activities/{activity_id}"
                        self.stdout.write(f'Making request to {detailed_url}')
                        
                        detailed_response = requests.get(detailed_url, headers=headers)
                        
                        if detailed_response.status_code == 200:
                            detailed_data = detailed_response.json()
                            
                            # Extract heart rate - check for 'average_heartrate' (Strava API format)
                            heart_rate = None
                            if 'average_heartrate' in detailed_data and detailed_data['average_heartrate'] is not None:
                                heart_rate = detailed_data['average_heartrate']
                                self.stdout.write(f'Found heart rate: {heart_rate}')
                            
                            # Extract cadence
                            cadence = None
                            if 'average_cadence' in detailed_data and detailed_data['average_cadence'] is not None:
                                cadence = detailed_data['average_cadence']
                                self.stdout.write(f'Found cadence: {cadence}')
                            
                            # Update activity
                            updated = False
                            if heart_rate is not None:
                                activity.average_heart_rate = heart_rate
                                updated = True
                            
                            if cadence is not None:
                                activity.average_cadence = cadence
                                updated = True
                            
                            if updated:
                                activity.save()
                                fixed_count += 1
                                self.stdout.write(f'Updated activity {activity_id}')
                            else:
                                self.stdout.write(f'No heart rate or cadence data found for activity {activity_id}')
                        else:
                            self.stdout.write(self.style.ERROR(f'Failed to get detailed data for activity {activity_id}. Status: {detailed_response.status_code}'))
                    
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Error processing activity {activity.external_id}: {str(e)}'))
                
                self.stdout.write(self.style.SUCCESS(f'Fixed {fixed_count} activities for user {user.username}'))
                total_fixed += fixed_count
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error processing user {user.username}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully fixed {total_fixed} activities')) 