"""
Configuration file for GA impact detection.
Add any GTM elements that should be considered as impacting Google Analytics.
Updated to include server container elements.
"""

# Tags, variables, triggers, clients and transformations that always impact GA tracking (by name)
# These are checked in addition to the automatic detection of GA tags
GA_IMPACT_ELEMENTS = {
    'tags': [
        # Examples:
        # 'Custom HTML - DataLayer Setup',
        # 'Simo Ahava - Analytics Debugger',
    ],
    'variables': [
        # Examples:
        # 'Data Layer - GA Client ID',
        # 'JS - Session ID',
    ],
    'triggers': [
        # Examples:
        # 'Custom Event - analytics_event',
        # 'Form Submission - Newsletter',
    ],
    'clients': [
        # Example server container clients:
        # 'GA4 Client - Main Property',
    ],
    'transformations': [
        # Example server container transformations:
        # 'GA4 Event Transformation',
    ]
}

# If True, any change to Custom JavaScript variables will trigger a GA impact check
CONSIDER_ALL_CJS_VARIABLES_IMPORTANT = False

# If True, any change to Custom HTML tags will trigger a GA impact check
CONSIDER_ALL_CUSTOM_HTML_IMPORTANT = False

# If True, enable deep recursive checking of variable cascading references
ENABLE_CASCADE_REFERENCE_CHECKING = True