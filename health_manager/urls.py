from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from core.views import ActivityListView, ActivityDetailView, MetricsListView, PrivacyPolicyView, RootView
from users.views import RegisterView, settings, delete_user
from integrations.views import (
    sync_strava, sync_whoop, whoop_webhook, 
    connect_strava, complete_strava,
    connect_whoop
)

urlpatterns = [
    # Root URL redirects to metrics if authenticated, login if not
    path('', RootView.as_view(), name='root'),
    
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(
        next_page='login',
        template_name='registration/logged_out.html'
    ), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('strava/', ActivityListView.as_view(), name='activities'),
    path('strava/<int:pk>/', ActivityDetailView.as_view(), name='activity_detail'),
    path('whoop/', MetricsListView.as_view(), name='metrics'),
    path('settings/', settings, name='settings'),
    path('delete-account/', delete_user, name='delete_user'),
    path('privacy/', PrivacyPolicyView.as_view(), name='privacy_policy'),
    
    # Social Auth URLs - move these before other URLs to ensure proper routing
    path('', include('social_django.urls', namespace='social')),
    
    # Custom auth URLs
    path('connect/strava/', connect_strava, name='connect_strava'),
    path('complete_strava/', complete_strava, name='complete_strava'),
    path('connect/whoop/', connect_whoop, name='connect_whoop'),
    
    # Other URLs
    path('sync/strava/', sync_strava, name='sync_strava'),
    path('sync/whoop/', sync_whoop, name='sync_whoop'),
    path('webhooks/whoop/', whoop_webhook, name='whoop_webhook'),
] 