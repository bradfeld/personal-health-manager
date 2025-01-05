import logging
from functools import wraps
from django.core.exceptions import ValidationError
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

def handle_integration_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise ValidationError("Failed to communicate with the service")
        except Exception as e:
            logger.exception("Unexpected error during integration")
            raise ValidationError("An unexpected error occurred")
    return wrapper 