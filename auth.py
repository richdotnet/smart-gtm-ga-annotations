import pickle
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# OAuth 2.0 scopes needed for both GTM and GA4 APIs
SCOPES = [
    'https://www.googleapis.com/auth/tagmanager.readonly',
    'https://www.googleapis.com/auth/analytics',
    'https://www.googleapis.com/auth/analytics.edit'
]

def get_credentials():
    """Get credentials using a service account key file."""
    try:
        # Update this path to your service account JSON key file
        SERVICE_ACCOUNT_FILE = 'credentials.json'
        
        # Create credentials from the service account file
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        
        print("Successfully authenticated with service account")
        return creds
        
    except Exception as e:
        print(f"Error authenticating with service account: {e}")
        raise

def initialize_services():
    """Initialize and return GTM and Analytics API services."""
    credentials = get_credentials()
    
    # Initialize GTM API service
    gtm_service = build('tagmanager', 'v2', credentials=credentials)
    
    # Initialize Analytics Admin API v1alpha service
    analytics_service = build('analyticsadmin', 'v1alpha', credentials=credentials)
    
    return gtm_service, analytics_service