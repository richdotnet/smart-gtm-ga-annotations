def get_gtm_containers(service):
    """Get all accessible GTM containers."""
    accounts = service.accounts().list().execute()
    containers = []
    
    if not accounts.get('account'):
        print("No GTM accounts found.")
        return containers
    
    for account in accounts['account']:
        account_path = f"accounts/{account['accountId']}"
        
        try:
            container_list = service.accounts().containers().list(
                parent=account_path
            ).execute()
            
            if container_list.get('container'):
                for container in container_list['container']:
                    container_info = {
                        'accountId': account['accountId'],
                        'accountName': account['name'],
                        'containerId': container['containerId'],
                        'containerName': container['name'],
                        'publicId': container.get('publicId', ''),  # Get the public ID
                        'path': f"{account_path}/containers/{container['containerId']}"
                    }
                    containers.append(container_info)
                    print(f"  Found container: {container['name']} (ID: {container['containerId']}, Public ID: {container.get('publicId', 'N/A')})")
        except Exception as e:
            print(f"Error listing containers for account {account['name']}: {e}")
    
    return containers

def get_latest_live_version(service, container_path):
    """Get the latest published version of a GTM container."""
    try:
        # Use live() method to retrieve the live container version
        versions = service.accounts().containers().versions().live(
            parent=container_path
        ).execute()
        
        # Since we're directly requesting the live version, we should get it
        if not versions:
            print(f"No live version found for container path: {container_path}")
            return None
            
        return versions
        
    except Exception as e:
        print(f"Error getting latest version for {container_path}: {e}")
        # Let's add some helpful debugging information
        print("Trying to get container info to debug...")
        try:
            container_info = service.accounts().containers().get(
                path=container_path
            ).execute()
            print(f"Container info: {container_info.get('name')}")
        except Exception as debug_e:
            print(f"Error getting container info: {debug_e}")
        
        return None

def find_container_by_public_id(gtm_service, public_id):
    """Find a GTM container by its public ID and return its path and name."""
    # First get all accounts
    accounts_response = gtm_service.accounts().list().execute()
    
    container_path = None
    container_name = None
    
    # Properly iterate through accounts and containers with parent parameter
    for account in accounts_response.get('account', []):
        account_id = account['accountId']
        account_path = f"accounts/{account_id}"
        
        # Use the parent parameter when listing containers
        containers_response = gtm_service.accounts().containers().list(
            parent=account_path
        ).execute()
        
        for container in containers_response.get('container', []):
            if container.get('publicId') == public_id:
                container_path = f"{account_path}/containers/{container['containerId']}"
                container_name = container['name']
                print(f"  Found container: {container_name} (Public ID: {public_id})")
                return container_path, container_name
    
    print(f"  Container with Public ID {public_id} not found.")
    return None, None