from social_core.backends.oauth import BaseOAuth2
import logging
from urllib.parse import urljoin
from django.conf import settings

logger = logging.getLogger(__name__)

class WhoopOAuth2(BaseOAuth2):
    name = 'whoop'
    AUTHORIZATION_URL = 'https://api.prod.whoop.com/oauth/oauth2/auth'
    ACCESS_TOKEN_URL = 'https://api.prod.whoop.com/oauth/oauth2/token'
    ACCESS_TOKEN_METHOD = 'POST'
    REFRESH_TOKEN_URL = 'https://api.prod.whoop.com/oauth/oauth2/token'
    SCOPE_SEPARATOR = ' '
    DEFAULT_SCOPE = ['offline', 'read:profile', 'read:workout', 'read:sleep', 'read:recovery', 'read:body_measurement']
    EXTRA_DATA = [
        ('access_token', 'access_token'),
        ('refresh_token', 'refresh_token'),
        ('expires_in', 'expires_in'),
    ]
    
    def get_redirect_uri(self, state=None):
        """Return redirect URI exactly as registered in Whoop developer portal"""
        # Use the redirect URI from settings
        redirect_uri = settings.SOCIAL_AUTH_WHOOP_REDIRECT_URI
        logger.info(f"Using Whoop redirect URI: {redirect_uri}")
        return redirect_uri
    
    def auth_params(self, state=None):
        params = super().auth_params(state)
        # Explicitly set the redirect URI
        params['redirect_uri'] = self.get_redirect_uri(state)
        logger.info(f"Auth params redirect_uri: {params['redirect_uri']}")
        return params
    
    def auth_complete_params(self, state=None):
        params = super().auth_complete_params(state)
        # Explicitly set the redirect URI
        params['redirect_uri'] = self.get_redirect_uri(state)
        logger.info(f"Auth complete params redirect_uri: {params['redirect_uri']}")
        return params
    
    def get_user_details(self, response):
        """Return user details from Whoop account"""
        return {
            'username': response.get('user_id', ''),
            'email': response.get('email', ''),
            'fullname': response.get('fullname', ''),
            'first_name': response.get('first_name', ''),
            'last_name': response.get('last_name', ''),
        }
    
    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        try:
            # Try the v1 user profile endpoint
            return self.get_json(
                'https://api.prod.whoop.com/developer/v1/user/profile/basic',
                headers={'Authorization': f'Bearer {access_token}'}
            )
        except Exception as e:
            logger.error(f"Error getting Whoop user data: {str(e)}")
            # Return minimal data to avoid breaking the flow
            return {'user_id': 'whoop_user'} 