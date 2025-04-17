import os
import csv
import argparse
from init_json import load_last_versions, LAST_VERSIONS_FILE
from auth import initialize_services
from change_detection import detect_gtm_changes, summarize_changes
from annotation_service import create_ga4_annotation
from ga_impact_detection import is_ga_impacted_by_changes

# File for GTM to GA4 mapping
MAPPING_FILE = 'gtm_ga4_mapping.csv'

print("GTM to GA4 Annotation Tool")
print("Note: To configure custom GA-impacting elements, edit the ga_impact_config.py file")
print("--------------------------------------------------")

def load_container_property_mapping():
    """Load mapping between GTM containers and GA4 properties from CSV file."""
    mapping = {}
    
    if not os.path.exists(MAPPING_FILE):
        print(f"Mapping file {MAPPING_FILE} not found. Please provide a CSV file with GTM container to GA4 property mappings.")
        print("Expected columns: 'gtm_public_id', 'ga4_property_id'")
        return mapping
    
    try:
        with open(MAPPING_FILE, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                container_id = row.get('gtm_public_id')
                property_id = row.get('ga4_property_id')
                if container_id and property_id:
                    mapping[container_id] = property_id
    except Exception as e:
        print(f"Error loading mapping file: {e}")
    
    return mapping

def process_container(public_id, property_id, last_versions, analytics_service):
    """Process a single container for changes and create annotations if needed."""
    if public_id not in last_versions:
        print(f"Container {public_id} not found in version tracking file.")
        return
        
    container_data = last_versions[public_id]
    latest_version = container_data.get('live_version')
    previous_version = container_data.get('old_version')
    
    if not latest_version:
        print(f"No live version found for {public_id}")
        return
        
    container_name = latest_version.get('container', {}).get('name', 'Unknown Container')
    version_id = latest_version.get('containerVersionId')
    version_name = latest_version.get('name', f"Version {version_id}")
    version_description = latest_version.get('description', '')
    fingerprint = latest_version.get('fingerprint', '')
    
    # If no previous version, we can't detect changes
    if not previous_version:
        print(f"Initial version detected for {container_name}: {version_id} - no changes to analyze")
        return
        
    previous_version_id = previous_version.get('containerVersionId')
    
    # Determine if this is a new version or a rollback
    is_rollback = int(version_id) < int(previous_version_id)
    
    if is_rollback:
        print(f"GTM version rollback detected for {container_name}: from {previous_version_id} to {version_id}")
    else:
        print(f"New GTM version detected for {container_name}: from {previous_version_id} to {version_id}")
        
    # Detect what changed between versions
    changes = detect_gtm_changes(previous_version, latest_version)
    
    # Summarize changes with element names
    summarize_changes(changes, container_name, latest_version)
    
    # Check if the changes impact GA tracking
    has_impact, impact_descriptions = is_ga_impacted_by_changes(changes, latest_version)
    if has_impact:
        print(f"Changes impact Google Analytics - creating annotation")
        print("Impact details:")
        for i, desc in enumerate(impact_descriptions, 1):
            print(f"  {i}. {desc}")
        
        # Create annotation in GA4
        try:
            create_ga4_annotation(
                analytics_service, 
                property_id, 
                container_name,
                public_id, 
                version_name,
                version_id, 
                fingerprint,
                is_rollback=is_rollback,
                version_description=version_description
            )
            
        except Exception as e:
            print(f"Error creating annotation: {e}")
    else:
        print(f"Changes do not impact Google Analytics - no annotation created")

def main():
    """Main function to process specific GTM containers and create GA4 annotations."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Process GTM containers and create GA4 annotations for changes')
    parser.add_argument('--containers', type=str, help='Comma-separated list of container IDs to process')
    args = parser.parse_args()
    
    # If no containers specified, exit
    if not args.containers:
        print("No containers specified. Use --containers argument to specify containers.")
        return
        
    # Parse container IDs from comma-separated string
    container_ids = [c.strip() for c in args.containers.split(',')]
    if not container_ids:
        print("No valid container IDs provided.")
        return
        
    print(f"Processing {len(container_ids)} specified containers: {', '.join(container_ids)}")
    
    # Check if version tracking file exists
    if not os.path.exists(LAST_VERSIONS_FILE):
        print(f"Version tracking file {LAST_VERSIONS_FILE} not found. Run check_versions.py first.")
        return
        
    # Load container to property mapping from the provided CSV
    mapping = load_container_property_mapping()
    if not mapping:
        print("No valid container-to-property mappings found. Please check your CSV file.")
        return
    
    # Load last processed versions
    last_versions = load_last_versions()
    
    # Initialize analytics service
    _, analytics_service = initialize_services()
    
    # Process each specified container
    for public_id in container_ids:
        if public_id not in mapping:
            print(f"Container {public_id} not found in mapping file. Skipping.")
            continue
            
        property_id = mapping[public_id]
        print(f"Processing GTM container {public_id} mapped to GA4 property {property_id}")
        
        process_container(public_id, property_id, last_versions, analytics_service)
    
    print("Finished processing specified containers.")

if __name__ == "__main__":
    main()