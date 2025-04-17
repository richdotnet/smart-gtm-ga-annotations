# Fields to ignore when comparing GTM elements
IGNORE_KEYS = {
    'tag': {'name', 'fingerprint', 'notes', 'parentFolderId', 'monitoringMetadata', 'tagManagerUrl'},
    'trigger': {'name', 'fingerprint', 'notes', 'parentFolderId', 'tagManagerUrl'},
    'variable': {'name', 'fingerprint', 'notes', 'parentFolderId', 'formatValue', 'tagManagerUrl'}
}

def compare_elements(old_element, new_element, element_type=None):
    """
    Compare two GTM elements to determine if they are different, ignoring specified keys.
    """
    ignore_keys = IGNORE_KEYS.get(element_type, set()) if element_type else set()
    old_filtered = {k: v for k, v in old_element.items() if k not in ignore_keys}
    new_filtered = {k: v for k, v in new_element.items() if k not in ignore_keys}
    return old_filtered != new_filtered

def detect_gtm_changes(old_version, new_version):
    """
    Detect changes between two GTM container versions.
    Updated to support server container elements (clients, transformations).
    """
    changes = {
        'added_elements': {
            'tags': [],
            'triggers': [],
            'variables': [],
            'clients': [],        # Server container element
            'transformations': [] # Server container element
        },
        'modified_elements': {
            'tags': [],
            'triggers': [],
            'variables': [],
            'clients': [],        # Server container element
            'transformations': [] # Server container element
        },
        'deleted_elements': {
            'tags': [],
            'triggers': [],
            'variables': [],
            'clients': [],        # Server container element
            'transformations': [] # Server container element
        }
    }
    
    # Detect tag changes
    old_tags = {tag.get('tagId'): tag for tag in old_version.get('tag', [])}
    new_tags = {tag.get('tagId'): tag for tag in new_version.get('tag', [])}
    
    # Added tags
    for tag_id in new_tags:
        if tag_id not in old_tags:
            changes['added_elements']['tags'].append(tag_id)
    
    # Deleted tags
    for tag_id in old_tags:
        if tag_id not in new_tags:
            changes['deleted_elements']['tags'].append(tag_id)
    
    # Modified tags
    for tag_id in old_tags:
        if tag_id in new_tags:
            old_tag = old_tags[tag_id]
            new_tag = new_tags[tag_id]
            if compare_elements(old_tag, new_tag):
                changes['modified_elements']['tags'].append(tag_id)
    
    # Detect trigger changes
    old_triggers = {trigger.get('triggerId'): trigger for trigger in old_version.get('trigger', [])}
    new_triggers = {trigger.get('triggerId'): trigger for trigger in new_version.get('trigger', [])}
    
    # Added triggers
    for trigger_id in new_triggers:
        if trigger_id not in old_triggers:
            changes['added_elements']['triggers'].append(trigger_id)
    
    # Deleted triggers
    for trigger_id in old_triggers:
        if trigger_id not in new_triggers:
            changes['deleted_elements']['triggers'].append(trigger_id)
    
    # Modified triggers
    for trigger_id in old_triggers:
        if trigger_id in new_triggers:
            old_trigger = old_triggers[trigger_id]
            new_trigger = new_triggers[trigger_id]
            if compare_elements(old_trigger, new_trigger):
                changes['modified_elements']['triggers'].append(trigger_id)
    
    # Detect variable changes
    old_variables = {variable.get('variableId'): variable for variable in old_version.get('variable', [])}
    new_variables = {variable.get('variableId'): variable for variable in new_version.get('variable', [])}
    
    # Added variables
    for variable_id in new_variables:
        if variable_id not in old_variables:
            changes['added_elements']['variables'].append(variable_id)
    
    # Deleted variables
    for variable_id in old_variables:
        if variable_id not in new_variables:
            changes['deleted_elements']['variables'].append(variable_id)
    
    # Modified variables
    for variable_id in old_variables:
        if variable_id in new_variables:
            old_variable = old_variables[variable_id]
            new_variable = new_variables[variable_id]
            if compare_elements(old_variable, new_variable):
                changes['modified_elements']['variables'].append(variable_id)
    
    # SERVER CONTAINER: Detect client changes
    if 'client' in old_version or 'client' in new_version:
        old_clients = {client.get('clientId'): client for client in old_version.get('client', [])}
        new_clients = {client.get('clientId'): client for client in new_version.get('client', [])}
        
        # Added clients
        for client_id in new_clients:
            if client_id not in old_clients:
                changes['added_elements']['clients'].append(client_id)
        
        # Deleted clients
        for client_id in old_clients:
            if client_id not in new_clients:
                changes['deleted_elements']['clients'].append(client_id)
        
        # Modified clients
        for client_id in old_clients:
            if client_id in new_clients:
                old_client = old_clients[client_id]
                new_client = new_clients[client_id]
                if compare_elements(old_client, new_client):
                    changes['modified_elements']['clients'].append(client_id)
    
    # SERVER CONTAINER: Detect transformation changes
    if 'transformation' in old_version or 'transformation' in new_version:
        old_transformations = {transformation.get('transformationId'): transformation 
                               for transformation in old_version.get('transformation', [])}
        new_transformations = {transformation.get('transformationId'): transformation 
                               for transformation in new_version.get('transformation', [])}
        
        # Added transformations
        for transformation_id in new_transformations:
            if transformation_id not in old_transformations:
                changes['added_elements']['transformations'].append(transformation_id)
        
        # Deleted transformations
        for transformation_id in old_transformations:
            if transformation_id not in new_transformations:
                changes['deleted_elements']['transformations'].append(transformation_id)
        
        # Modified transformations
        for transformation_id in old_transformations:
            if transformation_id in new_transformations:
                old_transformation = old_transformations[transformation_id]
                new_transformation = new_transformations[transformation_id]
                if compare_elements(old_transformation, new_transformation):
                    changes['modified_elements']['transformations'].append(transformation_id)
    
    return changes

def summarize_changes(changes, container_name, container_version=None):
    """Print a summary of changes with element names."""
    total_changes = sum(len(changes[change_type][element_type]) 
                       for change_type in changes 
                       for element_type in changes[change_type])
    
    print(f"  Detected {total_changes} changes in container {container_name}")
    
    # Keep essential change summary but remove detailed element-by-element logging
    for change_type in ['added_elements', 'modified_elements', 'deleted_elements']:
        changes_in_category = sum(len(changes[change_type][element_type]) for element_type in changes[change_type])
        if changes_in_category > 0:
            print(f"    {change_type.replace('_', ' ').title()}: ", end="")
            
            element_counts = []
            for element_type in ['tags', 'triggers', 'variables', 'clients', 'transformations']:
                element_count = len(changes[change_type][element_type])
                if element_count > 0:
                    element_counts.append(f"{element_count} {element_type}")
            
            print(", ".join(element_counts))
    
    return total_changes

def get_element_info(element_id, element_type, container_version):
    """Get information about a GTM element by its ID."""
    # Default values if element not found
    element_info = {
        'name': 'Unknown',
        'type': 'Unknown'
    }
    
    # If container_version is not provided, return defaults
    if not container_version:
        return element_info
    
    # Get the field name for element ID based on element type
    id_field = element_type[:-1] + 'Id' if element_type.endswith('s') else element_type + 'Id'
    
    # Simple iteration through all elements of that type
    for element in container_version.get(element_type, []):
        if element.get(id_field) == element_id:
            return {
                'name': element.get('name', element_info['name']),
                'type': element.get('type', element_info['type'])
            }
    
    return element_info

def get_element_name(element_id, element_type, container_version):
    """Get just the name of an element by its ID."""
    return get_element_info(element_id, element_type, container_version)['name']