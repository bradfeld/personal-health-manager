from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from .services.strava import StravaService
from .services.whoop import WhoopService
from .models import UserIntegration
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import hmac
import hashlib
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@login_required
def sync_strava(request):
    try:
        integration = UserIntegration.objects.get(user=request.user, provider='strava')
        service = StravaService(request.user)
        service.sync_activities()
        messages.success(request, 'Successfully synced Strava activities!')
    except UserIntegration.DoesNotExist:
        messages.error(request, 'Strava is not connected.')
    except Exception as e:
        messages.error(request, f'Error syncing activities: {str(e)}')
    
    return redirect('dashboard') 

@login_required
def sync_whoop(request):
    try:
        integration = UserIntegration.objects.get(user=request.user, provider='whoop')
        service = WhoopService(request.user)
        service.sync_data()
        messages.success(request, 'Successfully synced Whoop data!')
    except UserIntegration.DoesNotExist:
        messages.error(request, 'Whoop is not connected.')
    except Exception as e:
        messages.error(request, f'Error syncing data: {str(e)}')
    
    return redirect('metrics') 

@csrf_exempt
@require_POST
def whoop_webhook(request):
    logger.info("Received Whoop webhook request")
    logger.debug(f"Headers: {dict(request.headers)}")
    
    try:
        # Log raw request body
        body = request.body.decode('utf-8')
        logger.debug(f"Raw body: {body}")
        
        # Check if body is empty
        if not body:
            logger.error("Empty request body")
            return HttpResponse("Empty request body", status=400)
        
        # Parse webhook data
        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in request body: {str(e)}")
            return HttpResponse("Invalid JSON format", status=400)
        
        logger.info(f"Webhook data: {data}")
        
        # Validate required fields
        user_id = data.get('user_id')
        event_type = data.get('event_type')
        
        if not user_id:
            logger.error("Missing user_id in webhook data")
            return HttpResponse("Missing user_id", status=400)
            
        if not event_type:
            logger.error("Missing event_type in webhook data")
            return HttpResponse("Missing event_type", status=400)
        
        logger.info(f"Processing event type: {event_type} for user: {user_id}")
        
        # Handle different event types
        if event_type in ['workout.created', 'sleep.created', 'recovery.created']:
            logger.info(f"Triggering sync for user {user_id}")
            try:
                from .tasks import sync_user_data
                sync_user_data.delay(user_id)
                logger.info("Successfully scheduled sync task")
                return HttpResponse("Webhook processed successfully", status=200)
            except Exception as e:
                logger.error(f"Error scheduling sync task: {str(e)}", exc_info=True)
                return HttpResponse(f"Error scheduling sync: {str(e)}", status=500)
        else:
            logger.warning(f"Unhandled event type: {event_type}")
            return HttpResponse("Unhandled event type", status=200)
            
    except Exception as e:
        logger.error(f"Unexpected error processing webhook: {str(e)}", exc_info=True)
        return HttpResponse(f"Server error: {str(e)}", status=500) 