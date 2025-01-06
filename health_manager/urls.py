from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from core.views import DashboardView, ActivityListView, ActivityDetailView, MetricsListView
from users.views import RegisterView, settings
from integrations.views import sync_strava, sync_whoop, whoop_webhook

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', DashboardView.as_view(), name='dashboard'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(
        next_page='login',
        template_name='registration/logged_out.html'
    ), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('activities/', ActivityListView.as_view(), name='activities'),
    path('activities/<int:pk>/', ActivityDetailView.as_view(), name='activity_detail'),
    path('metrics/', MetricsListView.as_view(), name='metrics'),
    path('settings/', settings, name='settings'),
    
    # Social Auth URLs - move these before other URLs to ensure proper routing
    path('', include('social_django.urls', namespace='social')),
    
    # Other URLs
    path('sync/strava/', sync_strava, name='sync_strava'),
    path('sync/whoop/', sync_whoop, name='sync_whoop'),
    path('webhooks/whoop/', whoop_webhook, name='whoop_webhook'),
] 