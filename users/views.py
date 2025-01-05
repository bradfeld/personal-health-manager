from django.views.generic.edit import UpdateView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from .models import UserSettings
from integrations.models import UserIntegration

class UserSettingsView(LoginRequiredMixin, UpdateView):
    model = UserSettings
    fields = ['sync_frequency', 'email_notifications', 'distance_unit']
    template_name = 'users/settings.html'
    success_url = reverse_lazy('dashboard')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Check if user has a valid Strava integration
        try:
            strava_integration = UserIntegration.objects.get(
                user=self.request.user,
                provider='strava'
            )
            context['strava_connected'] = True
            context['strava_last_sync'] = strava_integration.last_sync
        except UserIntegration.DoesNotExist:
            context['strava_connected'] = False
            context['strava_last_sync'] = None
        return context
    
    def get_object(self, queryset=None):
        settings, created = UserSettings.objects.get_or_create(user=self.request.user)
        return settings

class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login') 