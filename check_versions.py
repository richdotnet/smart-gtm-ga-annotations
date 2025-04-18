import os
import csv
import subprocess
from init_json import load_last_versions, save_last_versions, LAST_VERSIONS_FILE
from auth import initialize_services
from gtm_service import get_latest_live_version, find_container_by_public_id

# File for GTM to GA4 mapping
MAPPING_FILE = 'gtm_ga4_mapping.csv'

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

def initialize_versions():
    """Initialize the last_versions.json file for first run."""
    # Load container to property mapping from the provided CSV
    mapping = load_container_property_mapping()
    if not mapping:
        print("No valid container-to-property mappings found. Please check your CSV file.")
        return
        
    print(f"Loaded {len(mapping)} container-to-property mappings from CSV.")
    print("Creating initial version tracking file with container data from CSV...")
    
    # Initialize services
    gtm_service, _ = initialize_services()
    
    # Create a dictionary to store initial versions
    initial_versions = {}
    
    # Process each container defined in the CSV mapping
    for public_id, property_id in mapping.items():
        print(f"Processing GTM container {public_id} mapped to GA4 property {property_id}")
        
        # Find the container by public ID
        container_path, container_name = find_container_by_public_id(gtm_service, public_id)
        if not container_path:
            continue
        
        # Get the live version for this container
        print(f"  Getting live version for {container_name} ({public_id})...")
        live_version = get_latest_live_version(gtm_service, container_path)
        
        if live_version:
            # Store the full live version data using public ID as key
            initial_versions[public_id] = {
                "live_version": live_version,
                "old_version": None  # Initially there is no old version
            }
            print(f"    Stored baseline version {live_version.get('containerVersionId')} for {public_id}")
        else:
            print(f"    No live version found for {public_id}")
    
    # Save the full initial version data
    save_last_versions(initial_versions)
    print(f"Created {LAST_VERSIONS_FILE} as baseline with full version data for {len(initial_versions)} containers.")
    print("No annotations created during this initialization run. Run the script again to detect and annotate GTM changes.")

def check_versions():
    """Check for GTM version changes and trigger main.py if needed."""
    print("GTM Version Change Detector")
    print("--------------------------------------------------")

    # Check if last_versions.json exists
    if not os.path.exists(LAST_VERSIONS_FILE):
        print(f"Initial run detected: {LAST_VERSIONS_FILE} doesn't exist.")
        # Initialize the versions file
        initialize_versions()
        return
        
    print("Authenticated version tracking file found. Checking for GTM version changes...")

    # Initialize services
    gtm_service, _ = initialize_services()
    
    # Load container to property mapping from the provided CSV
    mapping = load_container_property_mapping()
    if not mapping:
        print("No valid container-to-property mappings found. Please check your CSV file.")
        return
    
    print(f"Loaded {len(mapping)} container-to-property mappings from CSV.")
    
    # Load last processed versions
    last_versions = load_last_versions()
    
    # Create a temporary dictionary to store version updates
    version_updates = {}
    changed_containers = []
    
    # Process each container defined in the CSV mapping
    for public_id, property_id in mapping.items():
        print(f"Processing GTM container {public_id} mapped to GA4 property {property_id}")
        
        # Find the container by public ID
        container_path, container_name = find_container_by_public_id(gtm_service, public_id)
        if not container_path:
            continue
        
        # Get the live version for this container
        latest_version = get_latest_live_version(gtm_service, container_path)
        if not latest_version:
            print(f"  No published versions found for {public_id}")
            continue
        
        version_id = latest_version['containerVersionId']
        version_name = latest_version.get('name', f"Version {version_id}")
        
        # Check if we have a previous version to compare with
        if public_id in last_versions:
            previous_data = last_versions[public_id]
            previous_version = previous_data.get('live_version', {})
            previous_version_id = previous_version.get('containerVersionId')
            
            # Skip if version hasn't changed
            if previous_version_id == version_id:
                print(f"  No change for {container_name}, still at {version_name}")
                continue
                
            print(f"  Version change detected for {container_name}: from {previous_version_id} to {version_id}")
            
            # Store the update but don't apply it yet
            version_updates[public_id] = {
                "live_version": latest_version,
                "old_version": previous_version
            }
            
            # Add to list of changed containers
            changed_containers.append(public_id)
        else:
            # First time seeing this container
            print(f"  Initial version detected for {container_name}: {version_id}")
            version_updates[public_id] = {
                "live_version": latest_version,
                "old_version": None
            }
    
    # If any containers changed, call main.py
    if changed_containers:
        print(f"Found {len(changed_containers)} containers with version changes. Running main.py...")
        container_args = ",".join(changed_containers)
        
        # Run main.py and check its exit code
        result = subprocess.run(["python", "main.py", "--containers", container_args])
        
        # Only update last_versions.json if main.py was successful
        if result.returncode == 0:
            # Apply the updates to last_versions
            for public_id, update_data in version_updates.items():
                last_versions[public_id] = update_data
            
            # Save updated versions
            save_last_versions(last_versions)
            print("Updated last_versions.json with latest GTM container versions.")
        else:
            print("Error: main.py failed to process changes. Not updating last_versions.json.")
            print("You can run the script again to retry processing these changes.")
    else:
        print("No container version changes detected. Exiting without running main.py.")

if __name__ == "__main__":
    check_versions()