from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Avg
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta
from .models import Activity, HealthMetrics
from integrations.models import UserIntegration

class ActivityListView(LoginRequiredMixin, ListView):
    model = Activity
    template_name = 'core/activity_list.html'
    context_object_name = 'months'
    paginate_by = 1

    def get_queryset(self):
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
                months[month_key]['stats']['activity_types'][activity_type] = 1
            else:
                months[month_key]['stats']['activity_types'][activity_type] += 1

        # For each month, sort activities by exact datetime
        for month_data in months.values():
            month_data['activities'].sort(key=lambda x: x.date, reverse=True)

        return sorted(months.items(), key=lambda x: x[0], reverse=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get user's preferred distance unit
        try:
            user_settings = self.request.user.usersettings
            context['distance_unit'] = user_settings.distance_unit
            context['conversion_factor'] = 0.621371 if user_settings.distance_unit == 'mi' else 1
        except:
            context['distance_unit'] = 'km'
            context['conversion_factor'] = 1
        
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

    def get_queryset(self):
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
        
        return months
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Check if user has UserSettings, create if not
        from users.models import UserSettings
        user_settings, created = UserSettings.objects.get_or_create(user=self.request.user)
        
        # Add distance unit to context
        context['distance_unit'] = user_settings.distance_unit
        context['conversion_factor'] = 0.621371 if user_settings.distance_unit == 'mi' else 1
        
        # Check if user has Whoop integration
        from integrations.models import UserIntegration
        context['whoop_connected'] = UserIntegration.objects.filter(
            user=self.request.user,
            provider='whoop'
        ).exists()
        
        return context

class PrivacyPolicyView(TemplateView):
    template_name = 'core/privacy_policy.html' 