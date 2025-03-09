from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.contrib import messages
from .services.strava import StravaService
from .services.whoop import WhoopService
from .models import UserIntegration
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import hmac
import hashlib
from django.conf import settings
import logging
from social_django.utils import psa
import requests
from datetime import datetime, timezone, timedelta
import secrets
import string
import os

logger = logging.getLogger(__name__)

def generate_state(length=8):
    """Generate a random state parameter for OAuth"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

@login_required
def sync_strava(request):
    try:
        service = StravaService(request.user)
        service.sync_activities()
        return redirect('activities')
    except UserIntegration.DoesNotExist:
        return redirect('settings')
    except Exception as e:
        logger.error(f"Error syncing Strava activities: {str(e)}")
        return render(request, 'error.html', {'error': str(e)})

@login_required
def sync_whoop(request):
    try:
        service = WhoopService(request.user)
        service.sync_data()
        return redirect('metrics')
    except UserIntegration.DoesNotExist:
        return redirect('settings')
    except Exception as e:
        logger.error(f"Error syncing Whoop data: {str(e)}")
        return render(request, 'error.html', {'error': str(e)})

@login_required
def connect_strava(request):
    """Custom view to handle Strava authentication"""
    try:
        # Check if already connected
        if UserIntegration.objects.filter(user=request.user, provider='strava').exists():
            return redirect('settings')
        
        # Redirect to Strava OAuth
        auth_url = f"https://www.strava.com/oauth/authorize?client_id={settings.SOCIAL_AUTH_STRAVA_KEY}&redirect_uri={request.build_absolute_uri('/complete_strava/')}&response_type=code&scope=read,activity:read_all&approval_prompt=force"
        return redirect(auth_url)
    except Exception as e:
        logger.error(f"Error connecting to Strava: {str(e)}")
        return render(request, 'error.html', {'error': str(e)})

@login_required
def complete_strava(request):
    """Custom view to handle Strava OAuth callback"""
    try:
        # Get the authorization code from the request
        code = request.GET.get('code')
        if not code:
            logger.error("No code parameter in Strava callback")
            return render(request, 'error.html', {'error': 'No authorization code received from Strava'})
        
        # Exchange the code for an access token
        response = requests.post(
            'https://www.strava.com/oauth/token',
            data={
                'client_id': settings.SOCIAL_AUTH_STRAVA_KEY,
                'client_secret': settings.SOCIAL_AUTH_STRAVA_SECRET,
                'code': code,
                'grant_type': 'authorization_code'
            }
        )
        
        if response.status_code != 200:
            logger.error(f"Error exchanging code for token: {response.status_code} - {response.text}")
            return render(request, 'error.html', {'error': f'Error connecting to Strava: {response.text}'})
        
        # Parse the response
        data = response.json()
        
        # Save the tokens
        integration, created = UserIntegration.objects.update_or_create(
            user=request.user,
            provider='strava',
            defaults={
                'access_token': data.get('access_token'),
                'refresh_token': data.get('refresh_token'),
                'token_expires_at': datetime.fromtimestamp(data.get('expires_at', 0), tz=timezone.utc)
            }
        )
        
        logger.info(f"Successfully connected Strava for user {request.user.username}")
        
        # Redirect to settings page
        return redirect('settings')
    except Exception as e:
        logger.error(f"Error completing Strava authentication: {str(e)}")
        return render(request, 'error.html', {'error': str(e)})

@login_required
def connect_whoop(request):
    """Custom view to handle Whoop authentication"""
    try:
        # Check if already connected
        if UserIntegration.objects.filter(user=request.user, provider='whoop').exists():
            return redirect('settings')
        
        # Redirect to social auth login
        return redirect('social:begin', 'whoop')
    except Exception as e:
        logger.error(f"Error connecting to Whoop: {str(e)}")
        return render(request, 'error.html', {'error': str(e)})

@csrf_exempt
def complete_whoop(request):
    """Custom view to handle Whoop OAuth callback"""
    try:
        # Check if user is logged in
        if not request.user.is_authenticated:
            # If this is a callback from Whoop, store the code in session and redirect to login
            code = request.GET.get('code')
            state = request.GET.get('state')
            error = request.GET.get('error')
            
            if code or error:
                # This is a callback from Whoop
                if error:
                    logger.error(f"Whoop OAuth error: {error} - {request.GET.get('error_description')}")
                    return render(request, 'error.html', {'error': f'Error connecting to Whoop: {request.GET.get("error_description")}'})
                
                # Store the code in session
                request.session['whoop_oauth_code'] = code
                request.session['whoop_oauth_state'] = state
                
                # Redirect to login
                return redirect('login')
            else:
                # This is a regular request to the root URL, redirect to metrics if available
                return redirect('metrics')
        
        # Check if we have a code in session
        session_code = request.session.get('whoop_oauth_code')
        session_state = request.session.get('whoop_oauth_state')
        
        # Get the authorization code from the request or session
        code = request.GET.get('code') or session_code
        state = request.GET.get('state') or session_state
        error = request.GET.get('error')
        error_description = request.GET.get('error_description')
        
        # Clear session variables
        if 'whoop_oauth_code' in request.session:
            del request.session['whoop_oauth_code']
        if 'whoop_oauth_state' in request.session:
            del request.session['whoop_oauth_state']
        
        # Check for errors
        if error:
            logger.error(f"Whoop OAuth error: {error} - {error_description}")
            return render(request, 'error.html', {'error': f'Error connecting to Whoop: {error_description}'})
        
        # Check for code
        if not code:
            # If no code and no error, this is a regular request to the root URL
            return redirect('metrics')
        
        # Use the same redirect URI as in connect_whoop
        if os.getenv('RENDER'):
            redirect_uri = settings.SOCIAL_AUTH_WHOOP_REDIRECT_URI
            logger.info(f"Using Render redirect URI for token exchange: {redirect_uri}")
        elif 'ngrok' in request.build_absolute_uri('/'):
            redirect_uri = "https://ba2f-76-159-151-41.ngrok-free.app/complete/whoop"
            logger.info(f"Using ngrok redirect URI for token exchange: {redirect_uri}")
        else:
            redirect_uri = "http://127.0.0.1:8000/complete/whoop"
            logger.info(f"Using local redirect URI for token exchange: {redirect_uri}")
        
        # Exchange the code for an access token
        try:
            token_data = {
                'client_id': settings.SOCIAL_AUTH_WHOOP_KEY,
                'client_secret': settings.SOCIAL_AUTH_WHOOP_SECRET,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': redirect_uri
            }
            logger.info(f"Token exchange data: client_id={settings.SOCIAL_AUTH_WHOOP_KEY}, code={code[:5]}..., redirect_uri={redirect_uri}")
            
            response = requests.post(
                'https://api.prod.whoop.com/oauth/oauth2/token',
                data=token_data
            )
            
            if response.status_code != 200:
                logger.error(f"Error exchanging code for token: {response.status_code} - {response.text}")
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('error_description', response.text)
                return render(request, 'error.html', {'error': f'Error connecting to Whoop: {error_msg}'})
        except Exception as e:
            logger.error(f"Exception during token exchange: {str(e)}")
            return render(request, 'error.html', {'error': f'Error during token exchange: {str(e)}'})
        
        # Parse the response
        data = response.json()
        
        # Get the Whoop user ID
        user_id = None
        try:
            # Make a request to get the user profile
            profile_response = requests.get(
                'https://api.prod.whoop.com/developer-api/v1/user/profile',
                headers={
                    'Authorization': f'Bearer {data.get("access_token")}',
                    'Content-Type': 'application/json'
                }
            )
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                user_id = profile_data.get('user_id')
                logger.info(f"Retrieved Whoop user ID: {user_id}")
            else:
                logger.error(f"Error getting Whoop user profile: {profile_response.status_code} - {profile_response.text}")
        except Exception as e:
            logger.error(f"Error getting Whoop user profile: {str(e)}")
        
        # Save the tokens
        integration, created = UserIntegration.objects.update_or_create(
            user=request.user,
            provider='whoop',
            defaults={
                'access_token': data.get('access_token'),
                'refresh_token': data.get('refresh_token'),
                'token_expires_at': datetime.now(timezone.utc) + timedelta(seconds=data.get('expires_in', 3600)),
                'external_id': user_id
            }
        )
        
        logger.info(f"Successfully connected Whoop for user {request.user.username}")
        
        # Redirect to settings page
        return redirect('settings')
    except Exception as e:
        logger.error(f"Error completing Whoop authentication: {str(e)}")
        return render(request, 'error.html', {'error': str(e)})

@csrf_exempt
@require_POST
def whoop_webhook(request):
    """Handle Whoop webhook events"""
    try:
        # Log the raw request for debugging
        logger.debug(f"Received Whoop webhook: {request.body.decode('utf-8')}")
        
        # Parse the JSON payload
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook payload")
            return HttpResponse("Invalid JSON", status=400)
        
        # Validate required fields
        if 'user_id' not in data:
            logger.error("Missing user_id in webhook payload")
            return HttpResponse("Missing user_id", status=400)
        
        # Find the user integration
        try:
            integration = UserIntegration.objects.get(provider='whoop', external_id=data['user_id'])
            user = integration.user
        except UserIntegration.DoesNotExist:
            logger.error(f"No Whoop integration found for user_id: {data['user_id']}")
            return HttpResponse("User not found", status=404)
        
        # Process the webhook based on event type
        event_type = data.get('event_type')
        logger.info(f"Processing Whoop webhook event type: {event_type} for user {user.username}")
        
        # Import the sync task
        from .tasks import sync_whoop_user
        
        # Handle different event types
        if event_type in ['workout', 'sleep', 'recovery', 'cycle']:
            # Queue a task to sync the specific data type
            sync_whoop_user.delay(user.id)
            logger.info(f"Queued Whoop sync for user {user.username} due to {event_type} event")
        elif event_type == 'user.delete':
            # Handle user deletion event
            logger.info(f"Received user deletion event for Whoop user {data['user_id']}")
            integration.delete()
            logger.info(f"Deleted Whoop integration for user {user.username}")
            return HttpResponse("User integration deleted", status=200)
        else:
            logger.info(f"Received unknown Whoop event type: {event_type}")
            # Still sync data for unknown event types as a precaution
            sync_whoop_user.delay(user.id)
            logger.info(f"Queued Whoop sync for user {user.username} despite unknown event type")
        
        return HttpResponse("Webhook processed successfully", status=200)
    except Exception as e:
        logger.error(f"Error processing Whoop webhook: {str(e)}")
        logger.exception("Exception details:")
        return HttpResponse("Internal server error", status=500) 