from social_core.backends.oauth import BaseOAuth2
from django.conf import settings
import urllib.parse
import secrets
import string

class WhoopOAuth2(BaseOAuth2):
    name = 'whoop'
    AUTHORIZATION_URL = 'https://api.prod.whoop.com/oauth/oauth2/auth'
    ACCESS_TOKEN_URL = 'https://api.prod.whoop.com/oauth/oauth2/token'
    ACCESS_TOKEN_METHOD = 'POST'
    REFRESH_TOKEN_URL = 'https://api.prod.whoop.com/oauth/oauth2/token'
    SCOPE_SEPARATOR = ' '
    DEFAULT_SCOPE = None
    EXTRA_DATA = [
        ('refresh_token', 'refresh_token'),
        ('expires_in', 'expires_in'),
        ('token_type', 'token_type'),
    ]
    REDIRECT_STATE = True

    def generate_state(self):
        """Generate an 8-character state parameter as required by Whoop"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(8))

    def get_scope(self):
        """Return required scopes"""
        return 'offline read:recovery read:sleep read:workout'

    def auth_params(self, state=None):
        params = super().auth_params(state or self.generate_state())
        params['redirect_uri'] = settings.SOCIAL_AUTH_WHOOP_REDIRECT_URI
        params['scope'] = self.get_scope()
        return params

    def auth_complete_params(self, state=None):
        params = super().auth_complete_params(state)
        params['redirect_uri'] = settings.SOCIAL_AUTH_WHOOP_REDIRECT_URI
        params['scope'] = self.get_scope()
        params['grant_type'] = 'authorization_code'
        return params

    def get_user_details(self, response):
        """Return user details from Whoop account"""
        return {
            'username': response.get('user_id'),
            'email': response.get('email', ''),
            'first_name': response.get('first_name', ''),
            'last_name': response.get('last_name', '')
        }

    def user_data(self, access_token, *args, **kwargs):
        """Load user data from service"""
        url = 'https://api.prod.whoop.com/developer/v1/user/profile/basic'
        headers = {'Authorization': f'Bearer {access_token}'}
        return self.get_json(url, headers=headers)

    def get_user_id(self, details, response):
        """Return a unique ID for the current user"""
        return response.get('user_id') 