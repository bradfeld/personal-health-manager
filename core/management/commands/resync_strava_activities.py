from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from integrations.models import UserIntegration
from integrations.services.strava import StravaService
from core.models import Activity
import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = 'Resync all existing Strava activities with detailed data'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, help='Number of days to go back for resync, defaults to all activities')
        parser.add_argument('--user', type=str, help='Username to sync, defaults to all users')

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting full Strava activities resync with detailed data...')
        logger.info('Starting full Strava activities resync with detailed data')
        
        days = kwargs.get('days')
        username = kwargs.get('user')
        
        # Find users with Strava integration
        strava_integrations = UserIntegration.objects.filter(provider='strava')
        if username:
            try:
                user = User.objects.get(username=username)
                strava_integrations = strava_integrations.filter(user=user)
                self.stdout.write(f'Filtering for user: {username}')
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User {username} not found'))
                return
        
        total_users = strava_integrations.count()
        self.stdout.write(f'Found {total_users} user(s) with Strava integration')
        
        for i, integration in enumerate(strava_integrations, 1):
            user = integration.user
            self.stdout.write(f'Processing user {i}/{total_users}: {user.username}')
            
            try:
                # Get the service
                service = StravaService(user)
                
                # Store original last_sync
                old_last_sync = integration.last_sync
                
                # Determine how far back to sync
                if days:
                    # Set last_sync to specified days ago
                    cutoff_date = datetime.now() - timedelta(days=days)
                    integration.last_sync = cutoff_date
                    self.stdout.write(f'Syncing activities from {cutoff_date} onwards')
                else:
                    # Set to None to get all activities
                    integration.last_sync = None
                    self.stdout.write('Syncing all activities (no date limit)')
                
                integration.save()
                
                # Get full activity history
                start_time = time.time()
                result = service.sync_activities()
                end_time = time.time()
                
                # Restore the original last_sync time
                integration.last_sync = old_last_sync
                integration.save()
                
                # Report results
                self.stdout.write(f'User {user.username}: {result["total"]} activities processed')
                self.stdout.write(f'Heart rate data available for {result["heart_rate"]} activities')
                self.stdout.write(f'Cadence data available for {result["cadence"]} activities')
                self.stdout.write(f'Sync took {end_time - start_time:.2f} seconds')
                
                # Count activities with heart rate and cadence data
                total_activities = Activity.objects.filter(user=user, source='strava').count()
                hr_activities = Activity.objects.filter(user=user, source='strava', average_heart_rate__isnull=False).count()
                cadence_activities = Activity.objects.filter(user=user, source='strava', average_cadence__isnull=False).count()
                
                self.stdout.write(f'Total Strava activities in database: {total_activities}')
                
                # Calculate percentages safely
                hr_percentage = (hr_activities / total_activities * 100) if total_activities > 0 else 0
                cadence_percentage = (cadence_activities / total_activities * 100) if total_activities > 0 else 0
                
                self.stdout.write(f'Activities with heart rate data: {hr_activities} ({hr_percentage:.1f}%)')
                self.stdout.write(f'Activities with cadence data: {cadence_activities} ({cadence_percentage:.1f}%)')
                
            except Exception as e:
                logger.error(f'Error resyncing Strava activities for user {user.username}: {str(e)}', exc_info=True)
                self.stdout.write(self.style.ERROR(f'Error processing user {user.username}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS('Strava activities resync completed!')) 