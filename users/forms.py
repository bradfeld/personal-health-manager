from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
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

class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Custom password change form with Bootstrap styling.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control' 