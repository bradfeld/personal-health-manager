from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from integrations.models import UserIntegration
from integrations.services.strava import StravaService
from core.models import Activity
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = 'Resync all existing Strava activities with detailed data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting full Strava activities resync with detailed data...')
        
        # Find all users with Strava integration
        strava_integrations = UserIntegration.objects.filter(provider='strava')
        
        for integration in strava_integrations:
            user = integration.user
            self.stdout.write(f'Processing user: {user.username}')
            
            try:
                # Get the service
                service = StravaService(user)
                
                # Reset last_sync to None to force full resync
                old_last_sync = integration.last_sync
                integration.last_sync = None
                integration.save()
                
                # Get full activity history
                service.sync_activities()
                
                # Restore the original last_sync time
                integration.last_sync = old_last_sync
                integration.save()
                
                # Count activities with heart rate and cadence data
                activities_count = Activity.objects.filter(user=user, source='strava').count()
                heart_rate_count = Activity.objects.filter(user=user, source='strava', average_heart_rate__isnull=False).count()
                cadence_count = Activity.objects.filter(user=user, source='strava', average_cadence__isnull=False).count()
                
                self.stdout.write(f'User {user.username}: {activities_count} activities processed')
                self.stdout.write(f'Heart rate data available for {heart_rate_count} activities')
                self.stdout.write(f'Cadence data available for {cadence_count} activities')
                
            except Exception as e:
                logger.error(f'Error resyncing Strava activities for user {user.username}: {str(e)}')
                self.stdout.write(self.style.ERROR(f'Error processing user {user.username}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS('Strava activities resync completed!')) 