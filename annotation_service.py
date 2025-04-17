from datetime import datetime
import requests
from auth import get_credentials
from google.auth.transport.requests import Request

def create_ga4_annotation(analytics_service, property_id, container_name, public_id, version_name, version_id, fingerprint, is_rollback=False, version_description=""):
    """Create an annotation in GA4 for a new GTM version using Admin API."""
    try:
        # Convert fingerprint (Unix timestamp in milliseconds) to date
        # First, convert to seconds by dividing by 1000
        timestamp_seconds = int(fingerprint) / 1000
        annotation_date = datetime.fromtimestamp(timestamp_seconds).strftime("%Y-%m-%d")
        year, month, day = annotation_date.split('-')
        
        if is_rollback:
            annotation_type = f"GTM Version Rollback ({version_id}) - {public_id}"
            description_concat = f"Name: {version_name} - Description: {version_description}"
            if len(version_description) < 149:
                description = description_concat
            else:
                description = "Description too long to display in GA4. Check GTM for details."
            color = "RED"  # Use red for rollbacks
        else:
            annotation_type = f"New GTM Version ({version_id}) - {public_id}"
            description_concat = f"Name: {version_name} - Description: {version_description}"
            if len(version_description) < 149:
                description = description_concat
            else:
                description = "Description too long to display in GA4. Check GTM for details."
            color = "BLUE"  # Use blue for new versions
        
        # Prepare annotation data for direct HTTP request
        annotation_data = {
            "title": f"{annotation_type}",
            "description": description,
            "color": color,
            "annotationDate": {
                "year": int(year),
                "month": int(month),
                "day": int(day)
            }
        }
        
        credentials = get_credentials()
        # Refresh access token
        credentials.refresh(Request())
        
        # Construct the API URL
        url = f'https://analyticsadmin.googleapis.com/v1alpha/properties/{property_id}/reportingDataAnnotations'
        
        # Set headers
        headers = {
            'Authorization': f'Bearer {credentials.token}',
            'Content-Type': 'application/json'
        }
        
        # Make POST request to create the annotation
        response = requests.post(url, headers=headers, json=annotation_data)
        
        # Handle response
        if response.status_code == 200:
            response_data = response.json()
            print(f"Created GA4 annotation: {response_data.get('title')} for property {property_id} on {annotation_date}")
            return response_data
        else:
            print(f"Error creating annotation: {response.status_code}")
            print(response.text)
            raise Exception(f"Failed to create annotation: {response.status_code} - {response.text}")
        
    except Exception as e:
        print(f"Error creating annotation with fingerprint {fingerprint}: {e}")