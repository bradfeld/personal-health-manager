from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Activity, HealthMetrics
from django.db.models import Avg, Sum
from datetime import timedelta
from django.utils import timezone
from integrations.models import UserIntegration
from django.db.models.functions import TruncMonth

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get user's preferred distance unit
        try:
            user_settings = self.request.user.usersettings
            context['distance_unit'] = user_settings.distance_unit
            context['conversion_factor'] = 0.621371 if user_settings.distance_unit == 'mi' else 1  # mi/km conversion
        except:
            context['distance_unit'] = 'km'
            context['conversion_factor'] = 1
        
        # Get Strava last sync time
        try:
            strava_integration = UserIntegration.objects.get(
                user=self.request.user,
                provider='strava'
            )
            context['last_sync'] = strava_integration.last_sync
        except UserIntegration.DoesNotExist:
            context['last_sync'] = None
        
        # Get last 30 days of activities
        thirty_days_ago = timezone.now() - timedelta(days=30)
        activities = Activity.objects.filter(
            user=self.request.user,
            date__gte=thirty_days_ago
        ).order_by('-date')
        
        context['recent_activities'] = activities[:5]  # Last 5 activities
        
        # Activity stats with unit conversion
        total_distance = activities.aggregate(Sum('distance'))['distance__sum'] or 0
        context['activity_stats'] = {
            'total_activities': activities.count(),
            'total_distance': total_distance * context['conversion_factor'],
            'total_duration': activities.aggregate(Sum('duration'))['duration__sum'] or timedelta(),
            'total_calories': activities.aggregate(Sum('calories'))['calories__sum'] or 0,
        }
        
        # Group activities by type
        activity_types = {}
        for activity in activities:
            if activity.activity_type not in activity_types:
                activity_types[activity.activity_type] = 1
            else:
                activity_types[activity.activity_type] += 1
        context['activity_types'] = activity_types
        
        return context

class ActivityListView(LoginRequiredMixin, ListView):
    model = Activity
    template_name = 'core/activity_list.html'
    context_object_name = 'months'
    paginate_by = 1

    def get_queryset(self):
        # Get all activities grouped by month
        activities = Activity.objects.filter(
            user=self.request.user
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
                        'total_calories': 0,
                        'activity_types': {}
                    }
                }
            
            months[month_key]['activities'].append(activity)
            
            # Update month stats
            months[month_key]['stats']['total_activities'] += 1
            months[month_key]['stats']['total_distance'] += activity.distance or 0
            months[month_key]['stats']['total_duration'] += activity.duration
            months[month_key]['stats']['total_calories'] += activity.calories or 0
            
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
    context_object_name = 'metrics'
    paginate_by = 20

    def get_queryset(self):
        return HealthMetrics.objects.filter(user=self.request.user).order_by('-date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add metrics trends
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        recent_metrics = HealthMetrics.objects.filter(
            user=self.request.user,
            date__gte=thirty_days_ago
        )
        
        context['trends'] = {
            'avg_hrv': recent_metrics.aggregate(Avg('hrv'))['hrv__avg'],
            'avg_recovery': recent_metrics.aggregate(Avg('recovery_score'))['recovery_score__avg'],
            'avg_rhr': recent_metrics.aggregate(Avg('resting_heart_rate'))['resting_heart_rate__avg'],
        }
        
        return context 