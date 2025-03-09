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
                        'avg_hrv': 0,
                        'avg_recovery': 0,
                        'avg_rhr': 0,
                        'count': 0
                    }
                }
            
            months[month_key]['metrics'].append(metric)
            
            # Update month stats (only count metrics with values)
            if metric.hrv is not None:
                months[month_key]['stats']['avg_hrv'] += metric.hrv
                months[month_key]['stats']['count'] += 1
            if metric.recovery_score is not None:
                months[month_key]['stats']['avg_recovery'] += metric.recovery_score
            if metric.resting_heart_rate is not None:
                months[month_key]['stats']['avg_rhr'] += metric.resting_heart_rate
        
        # Calculate averages for each month
        for month_data in months.values():
            count = month_data['stats']['count']
            if count > 0:
                month_data['stats']['avg_hrv'] = month_data['stats']['avg_hrv'] / count
                month_data['stats']['avg_recovery'] = month_data['stats']['avg_recovery'] / count
                month_data['stats']['avg_rhr'] = month_data['stats']['avg_rhr'] / count
            
            # Sort metrics by date
            month_data['metrics'].sort(key=lambda x: x.date, reverse=True)
        
        return sorted(months.items(), key=lambda x: x[0], reverse=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context 

class PrivacyPolicyView(TemplateView):
    template_name = 'core/privacy_policy.html' 