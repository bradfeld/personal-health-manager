from django.views.generic.edit import UpdateView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from .models import UserSettings
from integrations.models import UserIntegration
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import UserPreferencesForm

class UserSettingsView(LoginRequiredMixin, UpdateView):
    model = UserSettings
    fields = ['sync_frequency', 'distance_unit']
    template_name = 'users/settings.html'
    success_url = reverse_lazy('metrics')
    
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

@login_required
def settings(request):
    # Get or create user settings
    user_settings, created = UserSettings.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = UserPreferencesForm(request.POST, instance=user_settings)
        if form.is_valid():
            form.save()
            return redirect('settings')
    else:
        form = UserPreferencesForm(instance=user_settings)
    
    # Check integration status
    strava_connected = UserIntegration.objects.filter(
        user=request.user, 
        provider='strava'
    ).exists()
    
    whoop_connected = UserIntegration.objects.filter(
        user=request.user, 
        provider='whoop'
    ).exists()
    
    return render(request, 'settings.html', {
        'form': form,
        'strava_connected': strava_connected,
        'whoop_connected': whoop_connected,
    }) 