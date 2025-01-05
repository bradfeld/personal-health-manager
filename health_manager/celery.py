from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'health_manager.settings')

app = Celery('health_manager')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks() 