from django.views.generic.edit import UpdateView, CreateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.contrib import messages
from .models import UserSettings
from integrations.models import UserIntegration
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import UserPreferencesForm, CustomPasswordChangeForm

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

class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """Custom password change view with our template and form."""
    form_class = CustomPasswordChangeForm
    template_name = 'users/password_change.html'
    success_url = reverse_lazy('settings')
    
    def form_valid(self, form):
        # Add a success message
        messages.success(self.request, "Your password has been successfully updated!")
        return super().form_valid(form)

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
            messages.success(request, "Settings updated successfully!")
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
    
    strava_last_sync = None
    if strava_connected:
        try:
            strava_integration = UserIntegration.objects.get(
                user=request.user,
                provider='strava'
            )
            strava_last_sync = strava_integration.last_sync
        except:
            pass
    
    return render(request, 'settings.html', {
        'form': form,
        'strava_connected': strava_connected,
        'whoop_connected': whoop_connected,
        'strava_last_sync': strava_last_sync,
    })

@login_required
def delete_user(request):
    """View to handle user account deletion"""
    if request.method == 'POST':
        user = request.user
        # Log the user out
        from django.contrib.auth import logout
        logout(request)
        # Delete the user (this will cascade delete related data due to model relationships)
        user.delete()
        # Redirect to login page with a message
        messages.success(request, 'Your account has been successfully deleted.')
        return redirect('login')
    
    # If not POST, redirect to settings page
    return redirect('settings') 