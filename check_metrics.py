#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'health_manager.settings')
django.setup()

from core.models import HealthMetrics

print('Recent Whoop metrics:')
for metric in HealthMetrics.objects.filter(source='whoop').order_by('-date')[:5]:
    print(f'Date: {metric.date}')
    print(f'  RHR: {metric.resting_heart_rate}')
    print(f'  HRV: {int(metric.hrv) if metric.hrv is not None else None}')
    print(f'  Recovery: {int(metric.recovery_score) if metric.recovery_score is not None else None}')
    print(f'  Sleep: {metric.sleep_duration}')
    print('---') 