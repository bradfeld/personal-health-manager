from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from .services.strava import StravaService
from .services.whoop import WhoopService
from .models import UserIntegration

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