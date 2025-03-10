from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Avg
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta
from .models import Activity, HealthMetrics
from integrations.models import UserIntegration
import logging

logger = logging.getLogger(__name__)

class RootView(View):
    """
    Root view that redirects to metrics if user is authenticated,
    otherwise redirects to login page
    """
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('metrics')
        else:
            return redirect('login')

class LoginRedirectView(LoginRequiredMixin, View):
    """
    Custom view to handle login redirects.
    If user has no data, redirect to settings page.
    Otherwise, redirect to metrics page.
    """
    def get(self, request, *args, **kwargs):
        try:
            # Check if user has any data
            has_activities = Activity.objects.filter(user=request.user).exists()
            has_metrics = HealthMetrics.objects.filter(user=request.user).exists()
            
            if not has_activities and not has_metrics:
                logger.info(f"User {request.user.username} has no data, redirecting to settings")
                return redirect('settings')
            else:
                logger.info(f"User {request.user.username} has data, redirecting to metrics")
                return redirect('metrics')
        except Exception as e:
            logger.error(f"Error in LoginRedirectView: {e}")
            # Default to metrics page if there's an error
            return redirect('metrics')

class ActivityListView(LoginRequiredMixin, ListView):
    model = Activity
    template_name = 'core/activity_list.html'
    context_object_name = 'months'
    paginate_by = 1

    def dispatch(self, request, *args, **kwargs):
        # Create UserSettings for new users before any other processing
        # Only if the user is authenticated (should always be true due to LoginRequiredMixin)
        if request.user.is_authenticated:
            from users.models import UserSettings
            UserSettings.objects.get_or_create(user=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        try:
            # Get all Strava activities grouped by month
            activities = Activity.objects.filter(
                user=self.request.user,
                source='strava'  # Only show Strava activities
            ).annotate(
                month=TruncMonth('date')
            ).order_by('-date')

            # Group activities and calculate stats by month
            months = {}
            for activity in activities:
                month_key = activity.month
                if month_key not in months:
                    months[month_key] = {
                        'activities': [],
                        'stats': {
                            'total_activities': 0,
                            'total_distance': 0,
                            'total_duration': timedelta(),
                            'activity_types': {}
                        }
                    }
                
                months[month_key]['activities'].append(activity)
                
                # Update month stats
                months[month_key]['stats']['total_activities'] += 1
                months[month_key]['stats']['total_distance'] += activity.distance or 0
                months[month_key]['stats']['total_duration'] += activity.duration
                
                # Count activity types
                activity_type = activity.activity_type
                if activity_type not in months[month_key]['stats']['activity_types']:
                    months[month_key]['stats']['activity_types'][activity_type] = 0
                months[month_key]['stats']['activity_types'][activity_type] += 1
            
            # Sort activities by date
            for month_data in months.values():
                month_data['activities'].sort(key=lambda x: x.date, reverse=True)
            
            # Convert to list for pagination
            return [(k, v) for k, v in sorted(months.items(), key=lambda x: x[0], reverse=True)]
        except Exception as e:
            # Log the error but return an empty list to avoid 500 errors
            logger.error(f"Error in ActivityListView.get_queryset: {str(e)}")
            return []
    
    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            
            # Get user settings
            from users.models import UserSettings
            user_settings = UserSettings.objects.get(user=self.request.user)
            
            # Add distance unit to context
            context['distance_unit'] = user_settings.distance_unit
            context['conversion_factor'] = 0.621371 if user_settings.distance_unit == 'mi' else 1
            
            # Check if user has Strava integration
            from integrations.models import UserIntegration
            try:
                strava_integration = UserIntegration.objects.get(
                    user=self.request.user,
                    provider='strava'
                )
                context['strava_connected'] = True
                context['last_sync'] = strava_integration.last_sync
            except UserIntegration.DoesNotExist:
                context['strava_connected'] = False
                context['last_sync'] = None
            
            return context
        except Exception as e:
            # Log the error but provide a basic context to avoid 500 errors
            logger.error(f"Error in ActivityListView.get_context_data: {str(e)}")
            
            # Create a minimal context that won't cause template errors
            context = super().get_context_data(**kwargs)
            context['distance_unit'] = 'mi'
            context['conversion_factor'] = 0.621371
            context['strava_connected'] = False
            context['last_sync'] = None
            return context

class ActivityDetailView(LoginRequiredMixin, DetailView):
    model = Activity
    template_name = 'core/activity_detail.html'
    context_object_name = 'activity'

    def get_queryset(self):
        return Activity.objects.filter(user=self.request.user)

class MetricsListView(LoginRequiredMixin, ListView):
    model = HealthMetrics
    template_name = 'core/metrics_list.html'
    context_object_name = 'months'
    paginate_by = 1

    def dispatch(self, request, *args, **kwargs):
        # Create UserSettings for new users before any other processing
        # Only if the user is authenticated (should always be true due to LoginRequiredMixin)
        if request.user.is_authenticated:
            from users.models import UserSettings
            UserSettings.objects.get_or_create(user=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        try:
            # Get all Whoop metrics grouped by month
            metrics = HealthMetrics.objects.filter(
                user=self.request.user,
                source='whoop'  # Only show Whoop metrics
            ).annotate(
                month=TruncMonth('date')
            ).order_by('-date')
            
            # Group metrics by month
            months = {}
            for metric in metrics:
                month_key = metric.month
                if month_key not in months:
                    months[month_key] = {
                        'metrics': [],
                        'stats': {
                            'avg_rhr': 0,
                            'avg_hrv': 0,
                            'avg_recovery': 0,
                            'total_sleep': timedelta(),
                        }
                    }
                
                months[month_key]['metrics'].append(metric)
            
            # Calculate stats for each month
            for month_key, month_data in months.items():
                metrics_list = month_data['metrics']
                
                # Calculate averages
                rhr_values = [m.resting_heart_rate for m in metrics_list if m.resting_heart_rate is not None]
                hrv_values = [m.hrv for m in metrics_list if m.hrv is not None]
                recovery_values = [m.recovery_score for m in metrics_list if m.recovery_score is not None]
                
                month_data['stats']['avg_rhr'] = sum(rhr_values) / len(rhr_values) if rhr_values else 0
                month_data['stats']['avg_hrv'] = sum(hrv_values) / len(hrv_values) if hrv_values else 0
                month_data['stats']['avg_recovery'] = sum(recovery_values) / len(recovery_values) if recovery_values else 0
                
                # Calculate total sleep
                month_data['stats']['total_sleep'] = sum(
                    (m.sleep_duration for m in metrics_list if m.sleep_duration is not None),
                    timedelta()
                )
            
            # Convert the dictionary to a list of tuples for pagination
            months_list = [(k, v) for k, v in sorted(months.items(), key=lambda x: x[0], reverse=True)]
            return months_list
        except Exception as e:
            # Log the error but return an empty list to avoid 500 errors
            logger.error(f"Error in MetricsListView.get_queryset: {str(e)}")
            return []
    
    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            
            # Get user settings (should already be created in dispatch)
            from users.models import UserSettings
            user_settings = UserSettings.objects.get(user=self.request.user)
            
            # Add distance unit to context
            context['distance_unit'] = user_settings.distance_unit
            context['conversion_factor'] = 0.621371 if user_settings.distance_unit == 'mi' else 1
            
            # Check if user has Whoop integration
            from integrations.models import UserIntegration
            try:
                whoop_integration = UserIntegration.objects.get(
                    user=self.request.user,
                    provider='whoop'
                )
                context['whoop_connected'] = True
                context['last_sync'] = whoop_integration.last_sync
            except UserIntegration.DoesNotExist:
                context['whoop_connected'] = False
                context['last_sync'] = None
            
            return context
        except Exception as e:
            # Log the error but provide a basic context to avoid 500 errors
            logger.error(f"Error in MetricsListView.get_context_data: {str(e)}")
            
            # Create a minimal context that won't cause template errors
            context = super().get_context_data(**kwargs)
            context['distance_unit'] = 'mi'
            context['conversion_factor'] = 0.621371
            context['whoop_connected'] = False
            context['last_sync'] = None
            return context

class PrivacyPolicyView(TemplateView):
    template_name = 'core/privacy_policy.html' 