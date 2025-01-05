from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from core.views import DashboardView, ActivityListView, ActivityDetailView, MetricsListView
from users.views import UserSettingsView, RegisterView
from integrations.views import sync_strava, sync_whoop

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
    path('settings/', UserSettingsView.as_view(), name='settings'),
    path('auth/', include('social_django.urls', namespace='social')),
    path('sync/strava/', sync_strava, name='sync_strava'),
    path('sync/whoop/', sync_whoop, name='sync_whoop'),
] 