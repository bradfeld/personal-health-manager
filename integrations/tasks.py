from celery import shared_task
from django.contrib.auth import get_user_model
from .services.strava import StravaService
from .services.whoop import WhoopService
from .models import UserIntegration
from core.utils import handle_integration_errors
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task
@handle_integration_errors
def sync_user_data(user_id):
    user = User.objects.get(id=user_id)
    
    # Sync Strava data
    try:
        integration = UserIntegration.objects.get(user=user, provider='strava')
        StravaService(user).sync_activities()
    except UserIntegration.DoesNotExist:
        pass
    
    # Sync Whoop data
    try:
        integration = UserIntegration.objects.get(user=user, provider='whoop')
        WhoopService(user).sync_data()
    except UserIntegration.DoesNotExist:
        pass

@shared_task
def sync_all_users():
    """Sync data for all users with active integrations"""
    logger.info("Starting sync for all users")
    
    # Sync Strava
    strava_integrations = UserIntegration.objects.filter(provider='strava')
    for integration in strava_integrations:
        sync_strava_user.delay(integration.user_id)
    
    # Sync Whoop
    whoop_integrations = UserIntegration.objects.filter(provider='whoop')
    for integration in whoop_integrations:
        sync_whoop_user.delay(integration.user_id)
    
    logger.info("Finished queueing sync tasks for all users")

@shared_task
def sync_strava_user(user_id):
    """Sync Strava data for a specific user"""
    try:
        user = User.objects.get(id=user_id)
        logger.info(f"Starting Strava sync for user {user.username}")
        
        service = StravaService(user)
        service.sync_activities()
        
        logger.info(f"Completed Strava sync for user {user.username}")
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found")
    except UserIntegration.DoesNotExist:
        logger.error(f"No Strava integration found for user ID {user_id}")
    except Exception as e:
        logger.error(f"Error syncing Strava data for user ID {user_id}: {str(e)}")

@shared_task
def sync_whoop_user(user_id):
    """Sync Whoop data for a specific user"""
    try:
        user = User.objects.get(id=user_id)
        logger.info(f"Starting Whoop sync for user {user.username}")
        
        service = WhoopService(user)
        service.sync_data()
        
        logger.info(f"Completed Whoop sync for user {user.username}")
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found")
    except UserIntegration.DoesNotExist:
        logger.error(f"No Whoop integration found for user ID {user_id}")
    except Exception as e:
        logger.error(f"Error syncing Whoop data for user ID {user_id}: {str(e)}") 