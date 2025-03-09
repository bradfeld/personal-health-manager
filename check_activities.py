#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'health_manager.settings')
django.setup()

from core.models import Activity

print('Total activities:', Activity.objects.count())
print('Whoop activities:', Activity.objects.filter(source='whoop').count())
print('Strava activities:', Activity.objects.filter(source='strava').count())

print('\nRecent Whoop activities:')
for activity in Activity.objects.filter(source='whoop').order_by('-date')[:5]:
    print(f'Date: {activity.date}')
    print(f'  Type: {activity.activity_type}')
    print(f'  Duration: {activity.duration}')
    print(f'  Distance: {activity.distance}')
    print(f'  Calories: {activity.calories}')
    print('---') 