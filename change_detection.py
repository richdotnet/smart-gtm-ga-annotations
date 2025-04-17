# Fields to ignore when comparing GTM elements
IGNORE_KEYS = {
    'tag': {'name', 'fingerprint', 'notes', 'parentFolderId', 'monitoringMetadata', 'tagManagerUrl'},
    'trigger': {'name', 'fingerprint', 'notes', 'parentFolderId', 'tagManagerUrl'},
    'variable': {'name', 'fingerprint', 'notes', 'parentFolderId', 'formatValue', 'tagManagerUrl'}
}

def detect_gtm_changes(old_version, new_version):
    """Detect changes between two GTM container versions."""
    changes = {
        'added_elements': {'tags': [], 'variables': [], 'triggers': []},
        'modified_elements': {'tags': [], 'variables': [], 'triggers': []},
        'deleted_elements': {'tags': [], 'variables': [], 'triggers': []}
    }
    
    # Process tag changes - store only IDs not entire objects
    old_tags = {tag.get('tagId'): tag.get('fingerprint') for tag in old_version.get('tag', [])}
    new_tags = {tag.get('tagId'): tag.get('fingerprint') for tag in new_version.get('tag', [])}
    
    # Find added tags (store IDs only)
    for tag_id in new_tags:
        if tag_id not in old_tags:
            changes['added_elements']['tags'].append(tag_id)
    
    # Find modified tags (store IDs only)
    for tag_id in new_tags:
        if tag_id in old_tags and new_tags[tag_id] != old_tags[tag_id]:
            changes['modified_elements']['tags'].append(tag_id)
    
    # Find deleted tags (store IDs only)
    for tag_id in old_tags:
        if tag_id not in new_tags:
            changes['deleted_elements']['tags'].append(tag_id)
    
    # Same pattern for variables and triggers...
    old_vars = {var.get('variableId'): var.get('fingerprint') for var in old_version.get('variable', [])}
    new_vars = {var.get('variableId'): var.get('fingerprint') for var in new_version.get('variable', [])}
    
    # Find added variables (store IDs only)
    for var_id in new_vars:
        if var_id not in old_vars:
            changes['added_elements']['variables'].append(var_id)
    
    # Find modified variables (store IDs only)
    for var_id in new_vars:
        if var_id in old_vars and new_vars[var_id] != old_vars[var_id]:
            changes['modified_elements']['variables'].append(var_id)
    
    # Find deleted variables (store IDs only)
    for var_id in old_vars:
        if var_id not in new_vars:
            changes['deleted_elements']['variables'].append(var_id)
    
    old_triggers = {trigger.get('triggerId'): trigger.get('fingerprint') for trigger in old_version.get('trigger', [])}
    new_triggers = {trigger.get('triggerId'): trigger.get('fingerprint') for trigger in new_version.get('trigger', [])}
    
    # Find added triggers (store IDs only)
    for trigger_id in new_triggers:
        if trigger_id not in old_triggers:
            changes['added_elements']['triggers'].append(trigger_id)
    
    # Find modified triggers (store IDs only)
    for trigger_id in new_triggers:
        if trigger_id in old_triggers and new_triggers[trigger_id] != old_triggers[trigger_id]:
            changes['modified_elements']['triggers'].append(trigger_id)
    
    # Find deleted triggers (store IDs only)
    for trigger_id in old_triggers:
        if trigger_id not in new_triggers:
            changes['deleted_elements']['triggers'].append(trigger_id)
    
    return changes

def summarize_changes(changes, container_name, container_version=None):
    """Generate a summary of changes without using lookups."""
    # Count changes for reporting
    total_changes = sum([
        len(changes['added_elements']['tags']),
        len(changes['added_elements']['variables']), 
        len(changes['added_elements']['triggers']),
        len(changes['modified_elements']['tags']),
        len(changes['modified_elements']['variables']),
        len(changes['modified_elements']['triggers']),
        len(changes['deleted_elements']['tags']),
        len(changes['deleted_elements']['variables']),
        len(changes['deleted_elements']['triggers'])
    ])
    
    # Output change summary (simplified, no lookups)
    print(f"  Detected {total_changes} changes in container {container_name}")
    
    # Log the changes - only count numbers, don't try to look up names
    for change_type in ['added_elements', 'modified_elements', 'deleted_elements']:
        for element_type in ['tags', 'variables', 'triggers']:
            element_ids = changes[change_type][element_type]
            if element_ids:
                print(f"    {change_type.replace('_', ' ').title()}: {len(element_ids)} {element_type}")
                
                # Only include IDs without attempting lookups
                for element_id in element_ids:
                    print(f"      - ID: {element_id}")
    
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