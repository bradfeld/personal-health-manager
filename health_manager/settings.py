import os
import dj_database_url
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_URLCONF = 'health_manager.urls'

# Use environment variables for sensitive data
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-default-key-for-dev')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'c251-76-159-151-41.ngrok-free.app', 'e845-76-159-151-41.ngrok-free.app']

# Add your render web service URL
if os.getenv('RENDER'):
    ALLOWED_HOSTS.append('personal-health-manager.onrender.com')
    ALLOWED_HOSTS.append('.onrender.com')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'social_django',
    
    # Local apps
    'core',
    'users',
    'integrations',
    'django_celery_beat',
    'django_celery_results',
    'whitenoise.runserver_nostatic',  # Add whitenoise for static files
]

AUTHENTICATION_BACKENDS = (
    'social_core.backends.strava.StravaOAuth',
    'integrations.oauth.WhoopOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

# Strava OAuth settings
SOCIAL_AUTH_STRAVA_KEY = os.environ.get('STRAVA_CLIENT_ID')
SOCIAL_AUTH_STRAVA_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')
SOCIAL_AUTH_STRAVA_SCOPE = ['read', 'activity:read_all']
SOCIAL_AUTH_STRAVA_AUTH_EXTRA_ARGUMENTS = {
    'approval_prompt': 'force',
    'response_type': 'code',
}
SOCIAL_AUTH_STRAVA_EXTRA_DATA = [
    ('refresh_token', 'refresh_token'),
    ('expires_in', 'expires_in'),
    ('token_type', 'token_type'),
]

# Social Auth general settings
SOCIAL_AUTH_RAISE_EXCEPTIONS = True
SOCIAL_AUTH_LOGIN_ERROR_URL = '/settings/'
SOCIAL_AUTH_REDIRECT_IS_HTTPS = os.getenv('RENDER', False) != False  # True in production
SOCIAL_AUTH_URL_NAMESPACE = 'social'

# Time zone setting (add this before Celery config)
TIME_ZONE = 'UTC'  # or your preferred timezone like 'America/New_York'
USE_TZ = True

# Celery Configuration
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Celery Beat Schedule
CELERY_BEAT_SCHEDULE = {
    'sync-all-users': {
        'task': 'integrations.tasks.sync_all_users',
        'schedule': timedelta(hours=1),
    },
}

# Whoop settings
SOCIAL_AUTH_WHOOP_KEY = os.getenv('WHOOP_CLIENT_ID')
SOCIAL_AUTH_WHOOP_SECRET = os.getenv('WHOOP_CLIENT_SECRET')
SOCIAL_AUTH_WHOOP_SCOPE = ['offline', 'read:profile', 'read:workout', 'read:sleep', 'read:recovery', 'read:body_measurement']

# Update redirect URI based on environment
if os.getenv('RENDER'):
    SOCIAL_AUTH_WHOOP_REDIRECT_URI = 'https://personal-health-manager.onrender.com/complete/whoop/'
    WHOOP_WEBHOOK_URL = 'https://personal-health-manager.onrender.com/webhooks/whoop/'
else:
    SOCIAL_AUTH_WHOOP_REDIRECT_URI = 'http://127.0.0.1:8000/complete/whoop/'
    WHOOP_WEBHOOK_URL = os.getenv('WHOOP_WEBHOOK_URL', 'https://e845-76-159-151-41.ngrok-free.app/webhooks/whoop/')

SOCIAL_AUTH_WHOOP_AUTH_EXTRA_ARGUMENTS = {
    'response_type': 'code',
}

# For development, allow both localhost and ngrok URLs
SOCIAL_AUTH_ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'c251-76-159-151-41.ngrok-free.app', 'personal-health-manager.onrender.com']

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'debug.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'core': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'integrations': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'social_core': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'social_django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Create logs directory if it doesn't exist
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

# Static files configuration
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Add whitenoise for static files in production
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add whitenoise middleware
    'django.contrib.sessions.middleware.SessionMiddleware',    # Required for admin
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware', # Required for admin
    'django.contrib.messages.middleware.MessageMiddleware',    # Required for admin
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'social_django.middleware.SocialAuthExceptionMiddleware',
]

# Whitenoise storage for static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'whoop'
LOGOUT_REDIRECT_URL = 'login'
LOGOUT_URL = 'logout'

SOCIAL_AUTH_LOGIN_REDIRECT_URL = 'whoop'
SOCIAL_AUTH_LOGIN_ERROR_URL = 'settings'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField' 

# Make sure TEMPLATES is properly configured
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],  # Add your templates directory
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',  # For social auth
                'social_django.context_processors.login_redirect',  # For social auth
            ],
        },
    },
] 

# Database configuration - use dj_database_url to parse DATABASE_URL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Use PostgreSQL in production
if os.getenv('DATABASE_URL'):
    DATABASES['default'] = dj_database_url.config(
        conn_max_age=600,
        conn_health_checks=True,
    )

# Add these settings for social auth pipeline
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
    'integrations.pipelines.save_strava_token',
    'integrations.pipelines.save_whoop_token',
)

# Security settings for production
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') 