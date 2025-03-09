from django import forms
from django.contrib.auth.models import User
from .models import UserSettings

class UserPreferencesForm(forms.ModelForm):
    class Meta:
        model = UserSettings
        fields = ['sync_frequency', 'distance_unit']
        widgets = {
            'sync_frequency': forms.Select(choices=[
                ('hourly', 'Hourly'),
                ('daily', 'Daily'),
                ('weekly', 'Weekly')
            ]),
            'distance_unit': forms.Select(choices=[
                ('mi', 'Miles'),
                ('km', 'Kilometers')
            ])
        } 