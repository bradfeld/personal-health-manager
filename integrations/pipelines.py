import logging
from datetime import datetime, timedelta
from integrations.models import UserIntegration
import traceback

logger = logging.getLogger(__name__)

def save_strava_token(backend, user, response, *args, **kwargs):
    logger.debug(f"Starting save_strava_token pipeline for user {user.username}")
    logger.debug(f"Backend: {backend.name}")
    logger.debug(f"Response keys: {response.keys()}")
    
    if backend.name == 'strava':
        try:
            # Get or create the user's integration
            integration, created = UserIntegration.objects.get_or_create(
                user=user,
                provider='strava',
                defaults={
                    'access_token': response.get('access_token'),
                    'refresh_token': response.get('refresh_token'),
                    'token_expires_at': datetime.fromtimestamp(response.get('expires_at', 0))
                }
            )
            
            # If not created, update the tokens
            if not created:
                integration.access_token = response.get('access_token')
                integration.refresh_token = response.get('refresh_token')
                integration.token_expires_at = datetime.fromtimestamp(response.get('expires_at', 0))
                integration.save()
            
            # Log successful token save
            logger.info(f"Saved Strava token for user {user.username}")
            
            return {'user': user, 'is_new': created}
        except Exception as e:
            # Log the error with traceback
            logger.error(f"Error saving Strava token: {str(e)}")
            logger.error(traceback.format_exc())
            raise

def save_whoop_token(backend, user, response, *args, **kwargs):
    logger.debug(f"Starting save_whoop_token pipeline for user {user.username}")
    logger.debug(f"Backend: {backend.name}")
    logger.debug(f"Response keys: {response.keys()}")
    
    if backend.name == 'whoop':
        try:
            # Get or create the user's integration
            integration, created = UserIntegration.objects.get_or_create(
                user=user,
                provider='whoop',
                defaults={
                    'access_token': response.get('access_token'),
                    'refresh_token': response.get('refresh_token'),
                    'token_expires_at': datetime.now() + timedelta(seconds=response.get('expires_in', 3600)),
                    'external_id': response.get('user_id')
                }
            )
            
            # If not created, update the tokens
            if not created:
                integration.access_token = response.get('access_token')
                integration.refresh_token = response.get('refresh_token')
                integration.token_expires_at = datetime.now() + timedelta(seconds=response.get('expires_in', 3600))
                if response.get('user_id'):
                    integration.external_id = response.get('user_id')
                integration.save()
            
            # Log successful token save
            logger.info(f"Saved Whoop token for user {user.username}")
            
            return {'user': user, 'is_new': created}
        except Exception as e:
            # Log the error with traceback
            logger.error(f"Error saving Whoop token: {str(e)}")
            logger.error(traceback.format_exc())
            raise 