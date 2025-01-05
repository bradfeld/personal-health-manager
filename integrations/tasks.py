from celery import shared_task
from django.contrib.auth import get_user_model
from .services.strava import StravaService
from .services.whoop import WhoopService
from .models import UserIntegration
from core.utils import handle_integration_errors

@shared_task
@handle_integration_errors
def sync_user_data(user_id):
    user = get_user_model().objects.get(id=user_id)
    
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
    for user in get_user_model().objects.filter(is_active=True):
        sync_user_data.delay(user.id) 