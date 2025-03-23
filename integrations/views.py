from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
import requests
import json
import logging
from .models import UserIntegration, Activity
from .services.strava import StravaService
from .services.whoop import WhoopService
from django.core.management import call_command
from threading import Thread
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
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
    client_id = settings.SOCIAL_AUTH_STRAVA_KEY
    redirect_uri = request.build_absolute_uri('/complete/strava/')
    
    # Define the desired scope
    scope = 'read,activity:read_all'
    
    # Construct the authorization URL
    auth_url = f"https://www.strava.com/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope={scope}"
    
    # Redirect the user to the Strava authorization page
    return redirect(auth_url)

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
                'token_expires_at': timezone.make_aware(datetime.fromtimestamp(data.get('expires_at', 0)))
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
        
        # Use the appropriate redirect URI based on environment
        if os.getenv('RENDER'):
            redirect_uri = settings.SOCIAL_AUTH_WHOOP_REDIRECT_URI
            logger.info(f"Using Render redirect URI for token exchange: {redirect_uri}")
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
                'token_expires_at': timezone.now() + timedelta(seconds=data.get('expires_in', 3600)),
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

@login_required
def full_resync_strava(request):
    try:
        # Instead of using subprocess, directly call the resync functionality
        from django.core.management import call_command
        from threading import Thread
        
        # Set up a background thread to run the command
        def run_resync():
            try:
                # Call the command with the current user only
                logger.info(f"Starting background resync for user {request.user.username}")
                call_command('resync_strava_activities', user=request.user.username)
                logger.info(f"Completed background resync for user {request.user.username}")
            except Exception as e:
                logger.error(f"Error in background resync thread: {str(e)}", exc_info=True)
        
        # Start the thread
        thread = Thread(target=run_resync)
        thread.daemon = True  # This ensures the thread won't block server shutdown
        thread.start()
        logger.info(f"Background resync thread started for user {request.user.username}")
        
        # Show a message to the user that the resync has been triggered
        return render(request, 'info.html', {
            'title': 'Full Resync Started',
            'message': 'A full resync of all your Strava activities has been started. This process may take a few minutes. The heart rate and cadence data will be updated as it becomes available.',
            'redirect_url': '/strava/',
            'redirect_text': 'Return to Strava Activities'
        })
    except Exception as e:
        logger.error(f"Error triggering full Strava resync: {str(e)}", exc_info=True)
        return render(request, 'error.html', {'error': str(e)})

@login_required
def direct_sync_strava(request):
    """
    Direct sync view that doesn't use a background thread - useful for testing and debugging
    This will resync the most recent 30 days of activities and show results directly.
    """
    try:
        # Get the user's integration
        integration = UserIntegration.objects.get(user=request.user, provider='strava')
        
        # First, check if we can directly get activities from the API
        headers = {
            'Authorization': f'Bearer {integration.access_token}'
        }
        
        # Make a direct API call to /athlete/activities with no filters
        logger.info("Making direct API call to check for Strava activities")
        activities_response = requests.get(
            'https://www.strava.com/api/v3/athlete/activities', 
            headers=headers,
            params={"per_page": 10}  # Get a few recent activities
        )
        
        api_check_results = ""
        if activities_response.status_code == 200:
            activities = activities_response.json()
            api_check_results = f"<p>Direct API call found {len(activities)} activities.</p>"
            if activities:
                api_check_results += "<p>Most recent activities:</p><ul>"
                for act in activities[:3]:  # Show first 3
                    name = act.get('name', 'Unnamed')
                    date = act.get('start_date', 'Unknown date')
                    type = act.get('type', 'Unknown type')
                    has_hr = 'Yes' if act.get('average_heartrate') else 'No'
                    has_cadence = 'Yes' if act.get('average_cadence') else 'No'
                    api_check_results += f"<li>{name} ({type}) on {date} - Has heart rate: {has_hr}, Has cadence: {has_cadence}</li>"
                api_check_results += "</ul>"
        else:
            api_check_results = f"<p>Direct API call failed with status {activities_response.status_code}: {activities_response.text}</p>"
        
        # Create service
        service = StravaService(request.user)
        
        # Store current last_sync
        old_last_sync = integration.last_sync
        
        # Set last_sync to None to get all activities (not just new ones)
        integration.last_sync = None
        integration.save()
        
        # Log what we're doing
        logger.info(f"Running direct sync for user {request.user.username} with no timestamp filter")
        
        # Run the sync
        results = service.sync_activities()
        
        # Restore original last_sync
        integration.last_sync = old_last_sync
        integration.save()
        
        # Check heart rate and cadence data
        total = results['total']
        heart_rate = results['heart_rate']
        cadence = results['cadence']
        
        hr_percentage = (heart_rate / total * 100) if total > 0 else 0
        cadence_percentage = (cadence / total * 100) if total > 0 else 0
        
        # Prepare detailed response
        message = f"""
        <h3>Sync Results</h3>
        <p>Synced {total} activities from your Strava account.</p>
        <p>Heart rate data available for {heart_rate} activities ({hr_percentage:.1f}%).</p>
        <p>Cadence data available for {cadence} activities ({cadence_percentage:.1f}%).</p>
        
        <h3>Direct API Check</h3>
        {api_check_results}
        
        <h3>About the Data</h3>
        <p>This sync was done directly and should show results immediately.</p>
        <p>If you still don't see heart rate or cadence data, your Strava activities may not contain this information.</p>
        <p>Heart rate data requires a heart rate monitor connected to your device during the activity.</p>
        <p>Cadence data is typically only available for running and cycling activities with appropriate sensors.</p>
        """
        
        return render(request, 'info.html', {
            'title': 'Direct Strava Sync Results',
            'message': message,
            'redirect_url': '/strava/',
            'redirect_text': 'Return to Strava Activities'
        })
        
    except UserIntegration.DoesNotExist:
        return redirect('settings')
    except Exception as e:
        logger.error(f"Error in direct Strava sync: {str(e)}", exc_info=True)
        return render(request, 'error.html', {'error': str(e)})

@login_required
def strava_diagnostic(request):
    """Diagnostic view to check Strava API connection and permissions"""
    try:
        # Get the user's integration
        integration = UserIntegration.objects.get(user=request.user, provider='strava')
        
        # Step 1: Check token details
        token_status = {
            "access_token_exists": bool(integration.access_token),
            "refresh_token_exists": bool(integration.refresh_token),
            "token_expires_at": integration.token_expires_at,
            "token_expired": integration.token_expires_at <= timezone.now() if integration.token_expires_at else True,
            "last_sync": integration.last_sync
        }
        
        # Step 2: Try to refresh the token (will log issues if they occur)
        try:
            service = StravaService(request.user)
            service.refresh_token_if_needed()
            token_refresh_result = "Success" 
        except Exception as e:
            token_refresh_result = f"Failed: {str(e)}"
        
        # Step 3: Make a direct API call to /athlete to check basic access
        headers = {
            'Authorization': f'Bearer {integration.access_token}'
        }
        athlete_response = requests.get('https://www.strava.com/api/v3/athlete', headers=headers)
        
        athlete_result = {
            "status_code": athlete_response.status_code,
            "response": athlete_response.json() if athlete_response.status_code == 200 else athlete_response.text
        }
        
        # Step 4: Make a direct API call to /athlete/activities with no filters
        activities_response = requests.get(
            'https://www.strava.com/api/v3/athlete/activities', 
            headers=headers,
            params={"per_page": 5}  # Just get a few to check
        )
        
        if activities_response.status_code == 200:
            activities = activities_response.json()
            activities_result = {
                "status_code": activities_response.status_code,
                "count": len(activities),
                "first_few": activities[:3] if activities else []
            }
        else:
            activities_result = {
                "status_code": activities_response.status_code,
                "response": activities_response.text
            }
        
        # Step 5: Check scopes/permissions
        scopes = integration.scopes if hasattr(integration, 'scopes') else "Unknown - not stored"
        
        # Compile results
        diagnostic_results = {
            "token_status": token_status,
            "token_refresh_result": token_refresh_result,
            "athlete_result": athlete_result,
            "activities_result": activities_result,
            "scopes": scopes
        }
        
        # Format results for display
        formatted_results = json.dumps(diagnostic_results, indent=2, default=str)
        
        return render(request, 'info.html', {
            'title': 'Strava API Diagnostic Results',
            'message': f"<pre>{formatted_results}</pre>",
            'redirect_url': '/strava/',
            'redirect_text': 'Return to Strava Activities'
        })
        
    except UserIntegration.DoesNotExist:
        return redirect('settings')
    except Exception as e:
        logger.error(f"Error in Strava diagnostic view: {str(e)}", exc_info=True)
        return render(request, 'error.html', {'error': str(e)})

@login_required
def strava_debug(request):
    """
    Debug view to directly test Strava API connectivity and permissions
    """
    try:
        # Get the user's integration
        integration = UserIntegration.objects.get(user=request.user, provider='strava')
        
        # Check if token is valid
        if integration.token_expires_at <= timezone.now():
            return render(request, 'info.html', {
                'title': 'Strava Debug - Token Expired',
                'message': f"Your Strava access token has expired. Last valid until: {integration.token_expires_at}",
                'redirect_url': '/strava/',
                'redirect_text': 'Back to Strava Activities'
            })
        
        # Define headers with access token
        headers = {
            'Authorization': f'Bearer {integration.access_token}'
        }
        
        # Test different API endpoints
        results = []
        
        # 1. Test athlete profile
        athlete_url = 'https://www.strava.com/api/v3/athlete'
        logger.info(f"Testing Strava API: {athlete_url}")
        athlete_response = requests.get(athlete_url, headers=headers)
        athlete_result = {
            'endpoint': 'Athlete Profile',
            'url': athlete_url,
            'status_code': athlete_response.status_code,
            'success': athlete_response.status_code == 200
        }
        
        if athlete_response.status_code == 200:
            athlete_data = athlete_response.json()
            athlete_result['data'] = {
                'id': athlete_data.get('id'),
                'username': athlete_data.get('username'),
                'firstname': athlete_data.get('firstname'),
                'lastname': athlete_data.get('lastname')
            }
        else:
            athlete_result['error'] = athlete_response.text[:200]
        
        results.append(athlete_result)
        
        # 2. Test athlete activities with different time ranges
        activities_url = 'https://www.strava.com/api/v3/athlete/activities'
        
        # Last 7 days
        week_ago = int((timezone.now() - timedelta(days=7)).timestamp())
        params_week = {'after': week_ago, 'per_page': 100}
        logger.info(f"Testing Strava API: {activities_url} with params {params_week}")
        week_response = requests.get(activities_url, headers=headers, params=params_week)
        
        week_result = {
            'endpoint': 'Activities (Last 7 days)',
            'url': activities_url,
            'params': params_week,
            'status_code': week_response.status_code,
            'success': week_response.status_code == 200
        }
        
        if week_response.status_code == 200:
            activities = week_response.json()
            week_result['count'] = len(activities)
            if activities:
                week_result['sample'] = {
                    'id': activities[0].get('id'),
                    'name': activities[0].get('name'),
                    'type': activities[0].get('type'),
                    'start_date': activities[0].get('start_date'),
                    'has_heartrate': 'average_heartrate' in activities[0] or 'average_heart_rate' in activities[0],
                    'has_cadence': 'average_cadence' in activities[0]
                }
        else:
            week_result['error'] = week_response.text[:200]
            
        results.append(week_result)
        
        # Last 90 days
        ninety_days_ago = int((timezone.now() - timedelta(days=90)).timestamp())
        params_ninety = {'after': ninety_days_ago, 'per_page': 100}
        logger.info(f"Testing Strava API: {activities_url} with params {params_ninety}")
        ninety_response = requests.get(activities_url, headers=headers, params=params_ninety)
        
        ninety_result = {
            'endpoint': 'Activities (Last 90 days)',
            'url': activities_url,
            'params': params_ninety,
            'status_code': ninety_response.status_code,
            'success': ninety_response.status_code == 200
        }
        
        if ninety_response.status_code == 200:
            activities = ninety_response.json()
            ninety_result['count'] = len(activities)
            if activities:
                ninety_result['sample'] = {
                    'id': activities[0].get('id'),
                    'name': activities[0].get('name'),
                    'type': activities[0].get('type'),
                    'start_date': activities[0].get('start_date')
                }
        else:
            ninety_result['error'] = ninety_response.text[:200]
            
        results.append(ninety_result)
        
        # All time (no after param)
        params_all = {'per_page': 100}
        logger.info(f"Testing Strava API: {activities_url} with params {params_all}")
        all_response = requests.get(activities_url, headers=headers, params=params_all)
        
        all_result = {
            'endpoint': 'Activities (All time)',
            'url': activities_url,
            'params': params_all,
            'status_code': all_response.status_code,
            'success': all_response.status_code == 200
        }
        
        if all_response.status_code == 200:
            activities = all_response.json()
            all_result['count'] = len(activities)
            if activities:
                all_result['sample'] = {
                    'id': activities[0].get('id'),
                    'name': activities[0].get('name'),
                    'type': activities[0].get('type'),
                    'start_date': activities[0].get('start_date')
                }
        else:
            all_result['error'] = all_response.text[:200]
            
        results.append(all_result)
        
        # 3. Check our database records
        db_activities = Activity.objects.filter(
            user=request.user,
            source='strava'
        ).count()
        
        db_activities_with_hr = Activity.objects.filter(
            user=request.user,
            source='strava',
            average_heart_rate__isnull=False
        ).count()
        
        db_activities_with_cadence = Activity.objects.filter(
            user=request.user,
            source='strava',
            average_cadence__isnull=False
        ).count()
        
        # Prepare results message
        message = f"""
        # Strava API Diagnostic Results
        
        ## OAuth Status
        - Token Valid Until: {integration.token_expires_at}
        - Current Time: {timezone.now()}
        
        ## Database Status
        - Total Strava Activities: {db_activities}
        - Activities with Heart Rate: {db_activities_with_hr}
        - Activities with Cadence: {db_activities_with_cadence}
        
        ## API Test Results
        """
        
        for result in results:
            message += f"\n### {result['endpoint']}\n"
            message += f"- Status: {'✅ Success' if result['success'] else '❌ Failed'} ({result['status_code']})\n"
            
            if 'count' in result:
                message += f"- Activities Found: {result['count']}\n"
                
            if 'sample' in result:
                message += f"- Sample Activity: {result['sample']}\n"
                
            if 'error' in result:
                message += f"- Error: {result['error']}\n"
        
        message += """
        ## What Next?
        
        If all API tests are successful but 0 activities are returned, check:
        1. Do you have any activities in your Strava account?
        2. Have you granted the necessary permissions during OAuth?
        3. Are your activities private? (This shouldn't matter but good to check)
        
        You can try reconnecting your Strava account to refresh permissions.
        """
        
        return render(request, 'info.html', {
            'title': 'Strava API Diagnostic Results',
            'message': message,
            'redirect_url': '/strava/',
            'redirect_text': 'Back to Strava Activities'
        })
        
    except UserIntegration.DoesNotExist:
        return redirect('settings')
    except Exception as e:
        logger.error(f"Error in Strava debug view: {str(e)}", exc_info=True)
        return render(request, 'error.html', {'error': str(e)}) 