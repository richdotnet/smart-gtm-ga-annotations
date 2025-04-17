try:
    from ga_impact_config import GA_IMPACT_ELEMENTS, CONSIDER_ALL_CJS_VARIABLES_IMPORTANT, CONSIDER_ALL_CUSTOM_HTML_IMPORTANT, ENABLE_CASCADE_REFERENCE_CHECKING
except ImportError:
    # Default values if config doesn't exist
    GA_IMPACT_ELEMENTS = {'tags': [], 'variables': [], 'triggers': []}
    CONSIDER_ALL_CJS_VARIABLES_IMPORTANT = False
    CONSIDER_ALL_CUSTOM_HTML_IMPORTANT = False
    ENABLE_CASCADE_REFERENCE_CHECKING = True

def identify_consent_mode_tag_ids(container_version):
    """
    Identify consent mode tags created with either:
    1. Simo Ahava's consent mode template (preferred)
    2. Custom HTML tags with gtag('consent' implementation (fallback)
    
    Args:
        container_version (dict): Full container version data
        
    Returns:
        list: List of tag IDs that implement consent mode
    """
    consent_mode_tag_ids = []
    consent_mode_tpl_id = None
    
    # Step 1: Find Simo Ahava's consent mode template ID
    for template in container_version.get('customTemplate', []):
        if ('galleryReference' in template and 
            template.get('galleryReference', {}).get('repository') == 'consent-mode' and
            template.get('galleryReference', {}).get('owner') == 'gtm-templates-simo-ahava'):
            consent_mode_tpl_id = template.get('templateId')
            break
    
    # Step 2: Find all tags using this template
    if consent_mode_tpl_id:
        for tag in container_version.get('tag', []):
            tag_type = tag.get('type', '')
            if tag_type.startswith('cvt_'):
                # Split the tag type by "_" and check if the last part matches the template ID
                parts = tag_type.split('_')
                if len(parts) > 1 and parts[-1] == consent_mode_tpl_id:
                    consent_mode_tag_ids.append(tag.get('tagId'))
    
    # Step 3: If no tags found using Simo's template, look for custom HTML implementations
    if not consent_mode_tag_ids:
        for tag in container_version.get('tag', []):
            tag_type = tag.get('type', '')
            tag_id = tag.get('tagId')
            tag_name = tag.get('name', 'Unknown')
            
            if tag_type == 'html':
                # For HTML tags, check if they contain gtag('consent' code
                for param in tag.get('parameter', []):
                    if param.get('type') == 'template' and 'html' in param.get('key', ''):
                        html_content = param.get('value', '')
                        if "gtag('consent'" in html_content:
                            print(f"  ✓ Found custom HTML consent implementation: '{tag_name}' (ID: {tag_id})")
                            consent_mode_tag_ids.append(tag_id)
                            break
    
    # Return only unique tag IDs
    unique_ids = list(set(consent_mode_tag_ids))
    
    if unique_ids:
        print(f"  Found {len(unique_ids)} consent mode tags")
    else:
        print("  No consent mode tags found")
        
    return unique_ids

def build_reference_map(container_version):
    """
    Build a comprehensive map of all references between entities in the container.
    
    This enhanced version catches all references including:
    - Direct variable references in tags (through {{variable_name}})
    - Variable-to-variable references (cascading references)
    - Trigger references in tags
    """
    reference_map = {
        'tags': {},      # tag_id -> {variables: [], triggers: [], name: ""}
        'variables': {},  # variable_id -> {variables: [], name: "", tags: [], referenced_by: []} 
        'var_name_to_id': {},  # variable_name -> variable_id
        'var_id_to_name': {},  # variable_id -> variable_name
        'trigger_id_to_name': {},  # trigger_id -> trigger_name
    }
    
    # First pass: Map variable names to IDs and vice versa
    for variable in container_version.get('variable', []):
        var_id = variable.get('variableId')
        var_name = variable.get('name')
        reference_map['var_name_to_id'][var_name] = var_id
        reference_map['var_id_to_name'][var_id] = var_name
        reference_map['variables'][var_id] = {
            'variables': [], 
            'name': var_name, 
            'tags': [],
            'referenced_by': []  # List of variable names that reference this variable
        }
    
    # Map trigger IDs to names
    for trigger in container_version.get('trigger', []):
        trigger_id = trigger.get('triggerId')
        trigger_name = trigger.get('name')
        reference_map['trigger_id_to_name'][trigger_id] = trigger_name
    
    # Second pass: Process tags to find their references
    for tag in container_version.get('tag', []):
        tag_id = tag.get('tagId')
        tag_name = tag.get('name')
        reference_map['tags'][tag_id] = {
            'variables': set(),  # Use set to avoid duplicates 
            'triggers': [], 
            'name': tag_name
        }
        
        # Find variable references in all tag parameters
        extract_variable_references(tag, reference_map['tags'][tag_id]['variables'])
        
        # Add trigger references
        for trigger_id in tag.get('firingTriggerId', []):
            if trigger_id:
                reference_map['tags'][tag_id]['triggers'].append(trigger_id)
    
    # Third pass: Process variables to find their variable references
    for variable in container_version.get('variable', []):
        var_id = variable.get('variableId')
        var_name = variable.get('name')
        referenced_vars = set()
        
        # Extract all variable references in this variable
        extract_variable_references(variable, referenced_vars)
        
        # Add these references to the variable
        for ref_var_name in referenced_vars:
            reference_map['variables'][var_id]['variables'].append(ref_var_name)
            
            # Also track reverse references (what references this variable)
            ref_var_id = reference_map['var_name_to_id'].get(ref_var_name)
            if ref_var_id and ref_var_id in reference_map['variables']:
                reference_map['variables'][ref_var_id]['referenced_by'].append(var_name)
    
    # Build direct tag-to-variable references (which tags directly reference which variables)
    for tag_id, tag_data in reference_map['tags'].items():
        for var_name in tag_data['variables']:
            var_id = reference_map['var_name_to_id'].get(var_name)
            if var_id and var_id in reference_map['variables']:
                if tag_id not in reference_map['variables'][var_id]['tags']:
                    reference_map['variables'][var_id]['tags'].append(tag_id)
    
    # Convert sets back to lists for easier serialization
    for tag_id in reference_map['tags']:
        reference_map['tags'][tag_id]['variables'] = list(reference_map['tags'][tag_id]['variables'])
    
    return reference_map

def extract_variable_references(obj, reference_set):
    """
    Recursively extract all variable references from an object.
    
    Args:
        obj: The object to process (tag, variable, parameter)
        reference_set: Set to store found variable references
    """
    import re
    
    if isinstance(obj, dict):
        # Check parameter values for variable references
        if 'parameter' in obj:
            for param in obj['parameter']:
                extract_variable_references(param, reference_set)
        
        # Process all string values in the object
        for key, value in obj.items():
            if isinstance(value, str):
                # Find all {{variable}} patterns
                var_refs = re.findall(r'{{([^{}]+)}}', value)
                for var_name in var_refs:
                    reference_set.add(var_name.strip())
            elif isinstance(value, (dict, list)):
                extract_variable_references(value, reference_set)
    
    elif isinstance(obj, list):
        for item in obj:
            extract_variable_references(item, reference_set)

def get_element_name(element_id, element_type, container_version):
    """Get the name of an element by its ID"""
    id_key = element_type[:-1] + 'Id' if element_type.endswith('s') else element_type + 'Id'
    for element in container_version.get(element_type, []):
        if element.get(id_key) == element_id:
            return element.get('name', 'Unknown')
    return 'Unknown'

from change_detection import get_element_info

def build_variable_dependency_graph(container_version):
    """
    Build a complete graph of variable dependencies in the container.
    This maps which variables reference which other variables.
    """
    dependency_graph = {}
    variable_name_to_id = {}
    variable_id_to_name = {}
    
    # First build lookup tables
    for variable in container_version.get('variable', []):
        var_id = variable.get('variableId')
        var_name = variable.get('name')
        if var_id and var_name:
            variable_name_to_id[var_name] = var_id
            variable_id_to_name[var_id] = var_name
            dependency_graph[var_id] = {
                'references': set(),  # variables it references
                'referenced_by': set(),  # variables that reference it
                'directly_impacts_ga': False,  # flag if it directly impacts GA tags
                'tags': set(),  # tags that use this variable
                'triggers': set()  # triggers that use this variable
            }
    
    # Build variable-to-variable reference graph
    for variable in container_version.get('variable', []):
        var_id = variable.get('variableId')
        if not var_id or var_id not in dependency_graph:
            continue
            
        # Find references to other variables in this variable's value
        referenced_vars = set()
        extract_variable_references(variable, referenced_vars)
        
        for ref_name in referenced_vars:
            if ref_name in variable_name_to_id:
                ref_id = variable_name_to_id[ref_name]
                # This variable references another variable
                dependency_graph[var_id]['references'].add(ref_id)
                # The other variable is referenced by this variable
                if ref_id in dependency_graph:
                    dependency_graph[ref_id]['referenced_by'].add(var_id)
    
    # Find tags that use each variable
    for tag in container_version.get('tag', []):
        tag_id = tag.get('tagId')
        referenced_vars = set()
        extract_variable_references(tag, referenced_vars)
        
        for ref_name in referenced_vars:
            if ref_name in variable_name_to_id:
                ref_id = variable_name_to_id[ref_name]
                if ref_id in dependency_graph:
                    dependency_graph[ref_id]['tags'].add(tag_id)
    
    # Find triggers that use each variable
    for trigger in container_version.get('trigger', []):
        trigger_id = trigger.get('triggerId')
        referenced_vars = set()
        extract_variable_references(trigger, referenced_vars)
        
        for ref_name in referenced_vars:
            if ref_name in variable_name_to_id:
                ref_id = variable_name_to_id[ref_name]
                if ref_id in dependency_graph:
                    dependency_graph[ref_id]['triggers'].add(trigger_id)

    # Special handling for trigger parameter references - be more aggressive in finding variable uses in triggers
    for trigger in container_version.get('trigger', []):
        trigger_id = trigger.get('triggerId')
        trigger_type = trigger.get('type', '')
        
        # Convert the entire trigger to a string to catch all possible variable references
        trigger_str = str(trigger)
        
        # For each variable, check if its name appears in the trigger string
        for var_id, var_name in variable_id_to_name.items():
            # Look for common patterns of variable references in triggers
            if f"{{{{{var_name}}}}}" in trigger_str or f"\"{var_name}\"" in trigger_str or f"'{var_name}'" in trigger_str:
                if var_id in dependency_graph:
                    dependency_graph[var_id]['triggers'].add(trigger_id)
    
    return dependency_graph, variable_id_to_name, variable_name_to_id

def is_ga_impacted_by_changes(changes, container_version, verbose_logging=False):
    """Analyze if changes impact GA tracking through direct and cascading relationships."""
    impact_descriptions = []
    has_impact = False
    
    # Get all changed element IDs
    changed_tag_ids = changes['added_elements']['tags'] + changes['modified_elements']['tags'] + changes['deleted_elements']['tags']
    changed_variable_ids = changes['added_elements']['variables'] + changes['modified_elements']['variables'] + changes['deleted_elements']['variables']
    changed_trigger_ids = changes['added_elements']['triggers'] + changes['modified_elements']['triggers'] + changes['deleted_elements']['triggers']
    
    # Server container-specific elements
    changed_client_ids = changes.get('added_elements', {}).get('clients', []) + changes.get('modified_elements', {}).get('clients', []) + changes.get('deleted_elements', {}).get('clients', [])
    changed_transformation_ids = changes.get('added_elements', {}).get('transformations', []) + changes.get('modified_elements', {}).get('transformations', []) + changes.get('deleted_elements', {}).get('transformations', [])
    
    # Import the custom configuration
    from ga_impact_config import GA_IMPACT_ELEMENTS
    
    # Define GA-relevant tag types (including server-side types)
    GA_RELEVANT_TAG_TYPES = [
        # Web container types
        'googtag',      # Google tag (GA4 configuration)
        'gaawe',        # GA4 event tag
        'gaawc',        # Google Analytics tag
        # Server container types
        'sgtmgaaw',     # Server-side GA4 tag
        'gaaw_client',  # GA4 Client in server containers
        'ga4_c',        # Alternative GA4 client name
        'ga_c',         # Universal Analytics client
        'measurement_protocol'  # Measurement Protocol tag
    ]
    
    # Detect container type
    is_server_container = False
    if 'taggingServerUrls' in container_version.get('container', {}) or 'client' in container_version:
        is_server_container = True
        print("  Detected server-side container")
    
    # Find consent mode tag IDs
    consent_mode_tags = identify_consent_mode_tag_ids(container_version)
    
    print("Building comprehensive dependency maps...")
    
    # Build transformation dependency map for server containers
    transformation_dependency_map = {}
    if is_server_container:
        transformation_dependency_map = build_transformation_dependency_map(container_version, verbose_logging)
    
    # Build tag dependency map
    tag_dependency_map = build_tag_dependency_map(container_version)
    
    # Build variable dependency graph
    dependency_graph, variable_id_to_name, variable_name_to_id = build_variable_dependency_graph(container_version)
    
    # Build trigger dependency map
    trigger_dependency_map = build_trigger_dependency_map(container_version)
    
    # Identify all GA-relevant tags
    ga_tags = {}
    if verbose_logging:
        print("\n=== IDENTIFYING GA-RELEVANT TAGS ===")
    
    for tag in container_version.get('tag', []):
        tag_id = tag.get('tagId')
        tag_name = tag.get('name', 'Unknown')
        tag_type = tag.get('type', 'Unknown')
        
        if verbose_logging:
            print(f"  Checking tag: '{tag_name}' (ID: {tag_id}, Type: {tag_type})")
        
        # Consider a tag GA-relevant if ANY of these are true:
        is_ga_relevant = False
        
        if tag_type in GA_RELEVANT_TAG_TYPES:
            is_ga_relevant = True
            if verbose_logging:
                print(f"    ✓ Tag is GA-relevant based on type: {tag_type}")
        
        elif tag_id in consent_mode_tags:
            is_ga_relevant = True
            if verbose_logging:
                print(f"    ✓ Tag is GA-relevant as it's a consent mode tag")
        
        elif tag_name in GA_IMPACT_ELEMENTS.get('tags', []):
            is_ga_relevant = True
            if verbose_logging:
                print(f"    ✓ Tag is GA-relevant as it's in GA_IMPACT_ELEMENTS")
        
        if is_ga_relevant:
            ga_tags[tag_id] = tag_name
    
    if verbose_logging:
        print(f"\n  Found {len(ga_tags)} GA-relevant tags:")
        for tag_id, tag_name in ga_tags.items():
            print(f"    - {tag_name} (ID: {tag_id})")
    
    # For server containers, identify GA-relevant clients
    ga_clients = {}
    if is_server_container:
        if verbose_logging:
            print("\n=== IDENTIFYING GA-RELEVANT CLIENTS ===")
        
        for client in container_version.get('client', []):
            client_id = client.get('clientId')
            client_name = client.get('name', 'Unknown')
            client_type = client.get('type', 'Unknown')
            
            if verbose_logging:
                print(f"  Checking client: '{client_name}' (ID: {client_id}, Type: {client_type})")
            
            # GA4 clients are GA-relevant
            is_ga_client = False
            
            if client_type in ['ga4_c', 'ga_c', 'gaaw_client']:
                is_ga_client = True
                if verbose_logging:
                    print(f"    ✓ Client is GA-relevant based on type: {client_type}")
            
            elif client_name in GA_IMPACT_ELEMENTS.get('clients', []):
                is_ga_client = True
                if verbose_logging:
                    print(f"    ✓ Client is GA-relevant as it's in GA_IMPACT_ELEMENTS")
            
            if is_ga_client:
                ga_clients[client_id] = client_name
        
        if verbose_logging:
            print(f"\n  Found {len(ga_clients)} GA-relevant clients:")
            for client_id, client_name in ga_clients.items():
                print(f"    - {client_name} (ID: {client_id})")
    
    # Mark variables that directly impact GA tags
    if verbose_logging:
        print("\n=== MARKING VARIABLES THAT DIRECTLY IMPACT GA ===")
    
    for var_id, info in dependency_graph.items():
        directly_impacts = False
        var_name = variable_id_to_name.get(var_id, f"Unknown-{var_id}")
        
        # Check if variable is directly used in any GA tag
        for tag_id in info['tags']:
            if tag_id in ga_tags:
                directly_impacts = True
                tag_name = ga_tags[tag_id]
                if verbose_logging:
                    print(f"  ✓ Variable '{var_name}' directly impacts GA tag '{tag_name}'")
                break
        
        # Store the result
        info['directly_impacts_ga'] = directly_impacts
    
    # Process changed clients (server containers only)
    if is_server_container and changed_client_ids:
        print("Analyzing client changes...")
        for client_id in changed_client_ids:
            # Find client details for better reporting
            client_name = "Unknown Client"
            for client in container_version.get('client', []):
                if client.get('clientId') == client_id:
                    client_name = client.get('name', 'Unknown')
                    client_type = client.get('type', 'Unknown')
                    break
            
            # Check if it's a GA-relevant client
            if client_id in ga_clients:
                impact_msg = f"Direct GA impact: Client '{client_name}' is a GA client"
                impact_descriptions.append(impact_msg)
                print(f"  ✓ {impact_msg}")
                has_impact = True
    
    # Process changed transformations (server containers only)
    if is_server_container and changed_transformation_ids:
        print("Analyzing transformation changes...")
        for transformation_id in changed_transformation_ids:
            # Find transformation details for better reporting
            transformation_name = "Unknown Transformation"
            for transformation in container_version.get('transformation', []):
                if transformation.get('transformationId') == transformation_id:
                    transformation_name = transformation.get('name', 'Unknown')
                    break
            
            # Check if this transformation affects GA clients or tags
            transformation_impact = []
            
            # 1. Direct connection to GA client
            if transformation_id in transformation_dependency_map.get('transformation_to_clients', {}):
                for client_id in transformation_dependency_map['transformation_to_clients'][transformation_id]:
                    if client_id in ga_clients:
                        client_name = ga_clients[client_id]
                        transformation_impact.append(f"directly feeds GA client '{client_name}'")
            
            # 2. Transformation used by GA tag
            if transformation_id in transformation_dependency_map.get('transformation_to_tags', {}):
                for tag_id in transformation_dependency_map['transformation_to_tags'][transformation_id]:
                    if tag_id in ga_tags:
                        tag_name = ga_tags[tag_id]
                        transformation_impact.append(f"directly impacts GA tag '{tag_name}'")
            
            # 3. Used by another transformation that impacts GA
            if transformation_id in transformation_dependency_map.get('transformation_to_transformations', {}):
                for connected_transformation_id in transformation_dependency_map['transformation_to_transformations'][transformation_id]:
                    for client_id in transformation_dependency_map.get('transformation_to_clients', {}).get(connected_transformation_id, []):
                        if client_id in ga_clients:
                            client_name = ga_clients[client_id]
                            transformation_impact.append(f"indirectly feeds GA client '{client_name}' via another transformation")
            
            if transformation_impact:
                impact_msg = f"Transformation impact: '{transformation_name}' {' and '.join(transformation_impact)}"
                impact_descriptions.append(impact_msg)
                print(f"  ✓ {impact_msg}")
                has_impact = True
    
    # Process tag changes
    if changed_tag_ids:
        print("Analyzing tag changes...")
        for tag_id in changed_tag_ids:
            # Find tag details for better reporting
            tag_name = "Unknown Tag"
            tag_type = "Unknown"
            for tag in container_version.get('tag', []):
                if tag.get('tagId') == tag_id:
                    tag_name = tag.get('name', 'Unknown')
                    tag_type = tag.get('type', 'Unknown')
                    break
            
            # Check if it's a GA-relevant tag type
            if tag_type in GA_RELEVANT_TAG_TYPES:
                impact_msg = f"Direct GA impact: Tag '{tag_name}' is a GA-relevant tag (type: {tag_type})"
                impact_descriptions.append(impact_msg)
                print(f"  ✓ {impact_msg}")
                has_impact = True
            
            # Check if it's a consent mode tag
            elif tag_id in consent_mode_tags:
                impact_msg = f"Consent mode impact: Tag '{tag_name}' is a consent mode tag"
                impact_descriptions.append(impact_msg)
                print(f"  ✓ {impact_msg}")
                has_impact = True
            
            # Check if it's a custom GA-impacting tag
            elif tag_name in GA_IMPACT_ELEMENTS.get('tags', []):
                impact_msg = f"Custom GA impact: Tag '{tag_name}' is configured as GA-impacting in ga_impact_config.py"
                impact_descriptions.append(impact_msg)
                print(f"  ✓ {impact_msg}")
                has_impact = True
            
            # Check if this is a setup tag for any GA-relevant tag
            elif tag_id in tag_dependency_map.get('setup_tags', {}):
                for dependent_tag in tag_dependency_map['setup_tags'][tag_id]:
                    dependent_tag_id = dependent_tag['tagId']
                    dependent_tag_name = dependent_tag['name']
                    
                    if dependent_tag_id in ga_tags:
                        impact_msg = f"Setup tag impact: Tag '{tag_name}' is a setup tag for GA tag '{dependent_tag_name}'"
                        impact_descriptions.append(impact_msg)
                        print(f"  ✓ {impact_msg}")
                        has_impact = True
            
            # Same for teardown tags
            elif tag_id in tag_dependency_map.get('teardown_tags', {}):
                for dependent_tag in tag_dependency_map['teardown_tags'][tag_id]:
                    dependent_tag_id = dependent_tag['tagId']
                    dependent_tag_name = dependent_tag['name']
                    
                    if dependent_tag_id in ga_tags:
                        impact_msg = f"Teardown tag impact: Tag '{tag_name}' is a teardown tag for GA tag '{dependent_tag_name}'"
                        impact_descriptions.append(impact_msg)
                        print(f"  ✓ {impact_msg}")
                        has_impact = True
    
    # Process trigger changes
    if changed_trigger_ids:
        print("Analyzing trigger changes...")
        for trigger_id in changed_trigger_ids:
            # Find trigger details for better reporting
            trigger_name = "Unknown Trigger"
            for trigger in container_version.get('trigger', []):
                if trigger.get('triggerId') == trigger_id:
                    trigger_name = trigger.get('name', 'Unknown')
                    break
            
            # Check if this trigger is used by any GA-relevant tags (directly)
            ga_tags_using_trigger = []
            
            # Check each GA tag to see if it uses this trigger
            for tag_id, tag_name in ga_tags.items():
                for tag in container_version.get('tag', []):
                    if tag.get('tagId') != tag_id:
                        continue
                        
                    # Check firing triggers
                    firing_triggers = tag.get('firingTriggerId', [])
                    if not isinstance(firing_triggers, list):
                        firing_triggers = [firing_triggers]
                    
                    if trigger_id in firing_triggers:
                        ga_tags_using_trigger.append((tag_id, tag_name, "firing"))
                    
                    # Check blocking triggers
                    blocking_triggers = tag.get('blockingTriggerId', [])
                    if not isinstance(blocking_triggers, list):
                        blocking_triggers = [blocking_triggers]
                    
                    if trigger_id in blocking_triggers:
                        ga_tags_using_trigger.append((tag_id, tag_name, "blocking"))
            
            if ga_tags_using_trigger:
                for tag_id, tag_name, trigger_type in ga_tags_using_trigger:
                    impact_msg = f"Trigger impact: Changed trigger '{trigger_name}' is a {trigger_type} trigger for GA tag '{tag_name}'"
                    impact_descriptions.append(impact_msg)
                    print(f"  ✓ {impact_msg}")
                    has_impact = True
                    
            # Even if no direct connection, check if this trigger is in the trigger_dependency_map
            elif trigger_id in trigger_dependency_map.get('trigger_to_tags', {}):
                for affected_tag_id in trigger_dependency_map['trigger_to_tags'][trigger_id]:
                    if affected_tag_id in ga_tags:
                        tag_name = ga_tags[affected_tag_id]
                        impact_msg = f"Indirect trigger impact: Trigger '{trigger_name}' affects GA tag '{tag_name}' through dependency chain"
                        impact_descriptions.append(impact_msg)
                        print(f"  ✓ {impact_msg}")
                        has_impact = True
    
    # Process changed variables and check for cascading impacts
    if changed_variable_ids:
        print("Analyzing variable changes and their cascading impact...")
        for variable_id in changed_variable_ids:
            variable_name = variable_id_to_name.get(variable_id, f"Unknown Variable ID {variable_id}")
            print(f"  Checking impact of variable: '{variable_name}' (ID: {variable_id})")
            
            # If we're in a server container, do a special check for transformations using this variable
            if is_server_container and variable_id in transformation_dependency_map.get('variable_to_transformations', {}):
                for transformation_id in transformation_dependency_map['variable_to_transformations'][variable_id]:
                    transformation_name = "Unknown"
                    for t in container_version.get('transformation', []):
                        if t.get('transformationId') == transformation_id:
                            transformation_name = t.get('name', 'Unknown')
                            break
                    
                    # Check if this transformation affects any GA tags
                    if transformation_id in transformation_dependency_map.get('transformation_to_tags', {}):
                        affected_ga_tags = []
                        for tag_id in transformation_dependency_map['transformation_to_tags'][transformation_id]:
                            if tag_id in ga_tags:
                                affected_ga_tags.append((tag_id, ga_tags[tag_id]))
                        
                        if affected_ga_tags:
                            tag_names = [name for _, name in affected_ga_tags]
                            impact_msg = f"Server variable-transformation impact: Variable '{variable_name}' is used in transformation '{transformation_name}' which affects GA tags: {', '.join(tag_names)}"
                            impact_descriptions.append(impact_msg)
                            print(f"  ✓ {impact_msg}")
                            has_impact = True
                            continue
            
            # Standard path checking
            var_has_impact, impact_paths = find_ga_impact_path(
                variable_id, 
                dependency_graph, 
                variable_id_to_name, 
                container_version, 
                ga_tags, 
                is_server_container, 
                transformation_dependency_map, 
                ga_clients
            )
            
            if var_has_impact:
                for path in impact_paths:
                    # Format the impact path for display
                    path_description = []
                    for item in path:
                        if isinstance(item, str) and item.startswith('tag:'):
                            tag_id = item[4:]  # Remove 'tag:' prefix
                            tag_name = ga_tags.get(tag_id, f"Unknown Tag {tag_id}")
                            path_description.append(f"GA Tag '{tag_name}'")
                        elif isinstance(item, str) and item.startswith('trigger:'):
                            trigger_id = item[8:]  # Remove 'trigger:' prefix
                            trigger_name = "Unknown Trigger"
                            for trigger in container_version.get('trigger', []):
                                if trigger.get('triggerId') == trigger_id:
                                    trigger_name = trigger.get('name', 'Unknown')
                                    break
                            path_description.append(f"Trigger '{trigger_name}'")
                        elif isinstance(item, str) and item.startswith('transformation:'):
                            transformation_id = item[15:]  # Remove 'transformation:' prefix
                            transformation_name = "Unknown Transformation"
                            for transformation in container_version.get('transformation', []):
                                if transformation.get('transformationId') == transformation_id:
                                    transformation_name = transformation.get('name', 'Unknown')
                                    break
                            path_description.append(f"Transformation '{transformation_name}'")
                        elif isinstance(item, str) and item.startswith('client:'):
                            client_id = item[7:]  # Remove 'client:' prefix
                            client_name = ga_clients.get(client_id, f"Unknown Client {client_id}")
                            path_description.append(f"GA Client '{client_name}'")
                        else:
                            var_name = variable_id_to_name.get(item, f"Unknown Variable {item}")
                            path_description.append(f"Variable '{var_name}'")
                    
                    impact_msg = "Deep variable dependency chain: " + " → ".join(path_description)
                    impact_descriptions.append(impact_msg)
                    print(f"  ✓ {impact_msg}")
                    has_impact = True
            else:
                print(f"  ✗ No GA impact found for variable '{variable_name}'")
    
    # Process triggers
    # [EXISTING TRIGGER HANDLING CODE]
    
    return has_impact, impact_descriptions

def check_cascade_impact(var_name, ga_relevant_tags, reference_map, path=None, checked_vars=None):
    """
    Recursively check if a variable impacts GA tags through cascading references.
    
    Args:
        var_name (str): Variable name to check
        ga_relevant_tags (list): List of GA-relevant tag (id, name) tuples
        reference_map (dict): Reference map structure
        path (list): Current reference path for cycle detection
        checked_vars (set): Set of already checked variables to prevent duplicate work
        
    Returns:
        tuple: (bool has_impact, list impact_paths)
    """
    # Initialize tracking structures
    if path is None:
        path = [var_name]
    else:
        if var_name in path:  # Prevent circular references
            return False, []
        path = path + [var_name]
    
    if checked_vars is None:
        checked_vars = set()
    
    # Skip if already checked
    if var_name in checked_vars:
        return False, []
    
    checked_vars.add(var_name)
    impact_paths = []
    has_impact = False
    
    # Get the variable ID
    var_id = reference_map['var_name_to_id'].get(var_name)
    if not var_id:
        return False, []
        
    # STEP 1: Check if this variable is directly referenced by any GA-relevant tag
    for tag_id, tag_name in ga_relevant_tags:
        tag_data = reference_map['tags'].get(tag_id, {})
        if var_name in tag_data.get('variables', []):
            impact_path = f"Variable '{var_name}' is directly referenced in GA tag '{tag_name}'"
            impact_paths.append(impact_path)
            print(f"  Direct impact found: {impact_path}")
            has_impact = True
    
    # STEP 2: Check what variables reference this variable (who uses this variable)
    referring_vars = []
    for var_id, var_data in reference_map['variables'].items():
        if var_name in var_data.get('variables', []):
            referring_var_name = var_data['name']
            referring_vars.append(referring_var_name)
    
    # Also check the referenced_by list which contains the reverse references
    if var_id in reference_map['variables']:
        for referring_var_name in reference_map['variables'][var_id].get('referenced_by', []):
            if referring_var_name not in referring_vars:
                referring_vars.append(referring_var_name)
    
    # STEP 3: Recursively check each variable that references this one
    for referring_var_name in referring_vars:
        if referring_var_name in path:  # Skip circular references
            continue
            
        sub_has_impact, sub_paths = check_cascade_impact(
            referring_var_name, 
            ga_relevant_tags, 
            reference_map, 
            path.copy(),
            checked_vars
        )
        
        if sub_has_impact:
            for sub_path in sub_paths:
                cascade_path = f"Variable '{var_name}' impacts GA via: {var_name} → {referring_var_name} → {sub_path}"
                impact_paths.append(cascade_path)
                print(f"  Cascade impact found: {cascade_path}")
                has_impact = True
    
    return has_impact, impact_paths

def is_ga_relevant_tag(tag):
    """
    Determine if a tag is directly relevant to GA4 tracking.
    
    Args:
        tag (dict): The tag to check
        
    Returns:
        bool: True if tag directly impacts GA
    """
    # Define GA-relevant tag types
    GA_RELEVANT_TAG_TYPES = [
        'googtag',      # Google tag (GA4 configuration)
        'gaawe',        # GA4 event tag
        'gaawc',        # Google Analytics tag
    ]
    
    # Check if tag type is directly GA relevant
    tag_type = tag.get('type', '')
    if tag_type in GA_RELEVANT_TAG_TYPES:
        return True
    
    return False

def build_tag_dependency_map(container_version):
    """Build a map of tag dependencies focusing on setup tags."""
    dependency_map = {
        'setup_tags': {},      # tag_id -> list of tags that use it as setup
        'teardown_tags': {},   # tag_id -> list of tags that use it as teardown
    }
    
    # Create a lookup from tag name to tag ID
    tag_name_to_id = {}
    tag_id_to_name = {}
    for tag in container_version.get('tag', []):
        tag_id = tag.get('tagId')
        tag_name = tag.get('name')
        if tag_id and tag_name:
            tag_name_to_id[tag_name] = tag_id
            tag_id_to_name[tag_id] = tag_name
    
    # Process all tags to find setup and teardown dependencies
    for tag in container_version.get('tag', []):
        dependent_tag_id = tag.get('tagId')
        dependent_tag_name = tag.get('name')
        
        # Process setup tags (specified by name in the setupTag field)
        for setup_tag_info in tag.get('setupTag', []):
            setup_tag_name = setup_tag_info.get('tagName')
            if setup_tag_name and setup_tag_name in tag_name_to_id:
                setup_tag_id = tag_name_to_id[setup_tag_name]
                
                # Record this setup tag dependency
                if setup_tag_id not in dependency_map['setup_tags']:
                    dependency_map['setup_tags'][setup_tag_id] = []
                
                dependency_map['setup_tags'][setup_tag_id].append({
                    'tagId': dependent_tag_id,
                    'name': dependent_tag_name
                })
        
        # Process teardown tags (similarly)
        for teardown_tag_info in tag.get('teardownTag', []):
            teardown_tag_name = teardown_tag_info.get('tagName')
            if teardown_tag_name and teardown_tag_name in tag_name_to_id:
                teardown_tag_id = tag_name_to_id[teardown_tag_name]
                
                if teardown_tag_id not in dependency_map['teardown_tags']:
                    dependency_map['teardown_tags'][teardown_tag_id] = []
                
                dependency_map['teardown_tags'][teardown_tag_id].append({
                    'tagId': dependent_tag_id,
                    'name': dependent_tag_name
                })
    
    return dependency_map

def build_trigger_dependency_map(container_version):
    """Build a map of trigger dependencies to identify what triggers affect which tags."""
    dependency_map = {
        'trigger_to_tags': {},  # trigger_id -> list of tag IDs that use this trigger
        'tag_to_triggers': {},  # tag_id -> list of trigger IDs used by this tag
    }
    
    # Process all tags to find their triggers
    for tag in container_version.get('tag', []):
        tag_id = tag.get('tagId')
        
        # Process firing triggers
        firing_triggers = tag.get('firingTriggerId', [])
        if not isinstance(firing_triggers, list):
            firing_triggers = [firing_triggers]
        
        for trigger_id in firing_triggers:
            if trigger_id:
                # Add to trigger_to_tags map
                if trigger_id not in dependency_map['trigger_to_tags']:
                    dependency_map['trigger_to_tags'][trigger_id] = []
                dependency_map['trigger_to_tags'][trigger_id].append(tag_id)
                
                # Add to tag_to_triggers map
                if tag_id not in dependency_map['tag_to_triggers']:
                    dependency_map['tag_to_triggers'][tag_id] = []
                dependency_map['tag_to_triggers'][tag_id].append(trigger_id)
        
        # Process blocking triggers
        blocking_triggers = tag.get('blockingTriggerId', [])
        if not isinstance(blocking_triggers, list):
            blocking_triggers = [blocking_triggers]
        
        for trigger_id in blocking_triggers:
            if trigger_id:
                # Add to trigger_to_tags map
                if trigger_id not in dependency_map['trigger_to_tags']:
                    dependency_map['trigger_to_tags'][trigger_id] = []
                dependency_map['trigger_to_tags'][trigger_id].append(tag_id)
                
                # Add to tag_to_triggers map
                if tag_id not in dependency_map['tag_to_triggers']:
                    dependency_map['tag_to_triggers'][tag_id] = []
                dependency_map['tag_to_triggers'][tag_id].append(trigger_id)
    
    return dependency_map

def build_transformation_dependency_map(container_version, verbose_logging=False):
    """Build a dependency map for transformations in server containers."""
    dependency_map = {
        'transformation_to_clients': {},
        'transformation_to_tags': {},
        'transformation_to_transformations': {},
        'client_to_transformations': {},
        'variable_to_transformations': {},
    }
    
    # Skip if not a server container
    if 'transformation' not in container_version:
        return dependency_map
    
    # Build lookup tables and process transformations
    # [Keep core functionality but remove all debug prints]
    
    return dependency_map

def is_ga_tag(tag_id, container_version):
    """Determine if a tag is a GA-related tag."""
    GA_RELEVANT_TAG_TYPES = [
        'sgtmgaaw',     # Server-side GA4 tag
        'gaaw_client',  # GA4 Client in server containers
        'ga4_c',        # Alternative GA4 client name
        'ga_c',         # Universal Analytics client
        'measurement_protocol'  # Measurement Protocol tag
    ]
    
    for tag in container_version.get('tag', []):
        if tag.get('tagId') == tag_id and tag.get('type') in GA_RELEVANT_TAG_TYPES:
            return True
    
    return False

def find_ga_impact_path(variable_id, dependency_graph, variable_id_to_name, container_version, 
                       ga_tags, is_server_container=False, transformation_dependency_map=None, 
                       ga_clients=None, visited=None, path=None):
    """Recursively traverse variable dependencies to find paths to GA-impacting elements."""
    if visited is None:
        visited = set()
    if path is None:
        path = []
    
    # Avoid cycles
    if variable_id in visited:
        return False, []
    
    visited.add(variable_id)
    current_path = path + [variable_id]
    
    # Check if variable exists in dependency graph
    if variable_id not in dependency_graph:
        return False, []
    
    # Check if this variable directly impacts GA
    if dependency_graph[variable_id]['directly_impacts_ga']:
        return True, [current_path]
    
    # For server containers - check if this variable is used in any transformations that affect GA tags
    if is_server_container and transformation_dependency_map and ga_clients:
        # Check if variable is directly linked to transformations in our dependency map
        if variable_id in transformation_dependency_map.get('variable_to_transformations', {}):
            transformation_ids = transformation_dependency_map['variable_to_transformations'][variable_id]
            
            for transformation_id in transformation_ids:
                # Check if transformation directly impacts any GA tags
                if transformation_id in transformation_dependency_map.get('transformation_to_tags', {}):
                    for tag_id in transformation_dependency_map['transformation_to_tags'][transformation_id]:
                        if tag_id in ga_tags:
                            return True, [current_path + ['transformation:' + transformation_id, 'tag:' + tag_id]]
                        
                # Check if transformation directly feeds a GA client
                if transformation_id in transformation_dependency_map.get('transformation_to_clients', {}):
                    for client_id in transformation_dependency_map['transformation_to_clients'][transformation_id]:
                        if client_id in ga_clients:
                            return True, [current_path + ['transformation:' + transformation_id, 'client:' + client_id]]
                
                # Check if transformation feeds another transformation that impacts GA
                if transformation_id in transformation_dependency_map.get('transformation_to_transformations', {}):
                    for next_transformation_id in transformation_dependency_map['transformation_to_transformations'][transformation_id]:
                        # Check if the next transformation connects to GA tags
                        if next_transformation_id in transformation_dependency_map.get('transformation_to_tags', {}):
                            for tag_id in transformation_dependency_map['transformation_to_tags'][next_transformation_id]:
                                if tag_id in ga_tags:
                                    return True, [current_path + [
                                        'transformation:' + transformation_id, 
                                        'transformation:' + next_transformation_id, 
                                        'tag:' + tag_id
                                    ]]
    
    # [Rest of function remains the same]

    # Check variable-to-tag direct impact
    
    for tag_id in dependency_graph[variable_id]['tags']:
        if tag_id in ga_tags:
            return True, [current_path + ['tag:' + tag_id]]

    # Check variable-to-trigger-to-tag impact

    for trigger_id in dependency_graph[variable_id]['triggers']:
        
        # Find which GA tags are fired or blocked by this trigger
        ga_tags_affected = []
        for tag in container_version.get('tag', []):
            tag_id = tag.get('tagId')
            
            if tag_id not in ga_tags:
                continue
                
            # Check firing triggers
            firing_triggers = tag.get('firingTriggerId', [])
            if not isinstance(firing_triggers, list):
                firing_triggers = [firing_triggers]
            
            if trigger_id in firing_triggers:
                ga_tags_affected.append((tag_id, "firing"))
                
            # Check blocking triggers
            blocking_triggers = tag.get('blockingTriggerId', [])
            if not isinstance(blocking_triggers, list):
                blocking_triggers = [blocking_triggers]
            
            if trigger_id in blocking_triggers:
                ga_tags_affected.append((tag_id, "blocking"))
        
        # If we found GA tags affected by this trigger
        if ga_tags_affected:
            for tag_id, trigger_type in ga_tags_affected:
                return True, [current_path + ['trigger:' + trigger_id, 'tag:' + tag_id]]
    
    # Recursively check variables that this one references (forward references)
    
    for ref_id in dependency_graph[variable_id]['references']:
        
        has_impact, sub_paths = find_ga_impact_path(
            ref_id, dependency_graph, variable_id_to_name, container_version, 
            ga_tags, is_server_container, transformation_dependency_map, 
            ga_clients, visited.copy(), current_path
        )
        if has_impact:
            return True, sub_paths
    
    # Recursively check variables that reference this one (backward references)
    
    for ref_by_id in dependency_graph[variable_id]['referenced_by']:
        if ref_by_id not in visited:
            
            has_impact, sub_paths = find_ga_impact_path(
                ref_by_id, dependency_graph, variable_id_to_name, container_version, 
                ga_tags, is_server_container, transformation_dependency_map, 
                ga_clients, visited.copy(), current_path
            )
            if has_impact:
                return True, sub_paths
    
    return False, []