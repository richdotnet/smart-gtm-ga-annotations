import os
import json

# File to store the last processed versions
LAST_VERSIONS_FILE = 'last_versions.json'

def load_last_versions():
    """Load the last processed versions from file."""
    if os.path.exists(LAST_VERSIONS_FILE):
        print(f"Found existing {LAST_VERSIONS_FILE}, loading previous version information...")
        with open(LAST_VERSIONS_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print(f"Error parsing {LAST_VERSIONS_FILE}, starting with empty version history.")
                return {}
    else:
        print(f"{LAST_VERSIONS_FILE} not found, will create it after processing.")
        return {}

def save_last_versions(last_versions):
    """Save the last processed versions to file."""
    file_existed = os.path.exists(LAST_VERSIONS_FILE)
    with open(LAST_VERSIONS_FILE, 'w') as f:
        json.dump(last_versions, f, indent=2)
    
    if not file_existed:
        print(f"Created {LAST_VERSIONS_FILE} to track GTM container versions.")
    else:
        print(f"Updated {LAST_VERSIONS_FILE} with latest GTM container versions.")

def initialize_json():
    """Initialize the last versions JSON file if it doesn't exist."""
    if not os.path.exists(LAST_VERSIONS_FILE):
        save_last_versions({})
        print(f"Initialized empty {LAST_VERSIONS_FILE} file.")
    else:
        print(f"{LAST_VERSIONS_FILE} already exists.")

if __name__ == "__main__":
    initialize_json()
    print("JSON initialization complete.")