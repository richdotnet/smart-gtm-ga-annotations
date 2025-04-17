# GTM to GA4 Annotation Tool

An automation tool that monitors Google Tag Manager (GTM) container version changes and creates annotations in Google Analytics 4 (GA4) when changes could impact GA4 data collection.

---

## Overview

This tool solves a critical challenge in analytics governance by automatically documenting GTM changes directly in GA4. It detects when tags, triggers, or variables change and analyzes whether those changes will affect your GA4 data collection, creating appropriate annotations to help explain data shifts.

---

## Features

- **Automated Version Monitoring**: Tracks GTM container version changes  
- **Intelligent Impact Detection**: Analyzes if changes affect GA4 data collection  
- **Comprehensive Dependency Analysis**: Detects complex dependency chains that impact GA4  
- **Consent Mode Support**: Identifies and monitors consent mode implementations  
- **Deep Cascading Logic**: Recognizes even distant relationships between changed elements and GA4  
- **GA4 Annotation Creation**: Automatically creates annotations in GA4 with detailed change information  
- **Flexible Configuration**: Customizable settings for your specific implementation  
- **Cron-Job Ready**: Easy to automate with scheduled jobs  

---

## Setup Requirements

### 1. Google Cloud Project Setup

- Create a Google Cloud Project  
- Enable the following APIs:  
  - Google Tag Manager API  
  - Google Analytics Admin API  
- Create a service account with the following permissions:  
  - **Tag Manager**: Tag Manager Read access  
  - **Google Analytics**: Editor role (for creating annotations)  
- Download the service account credentials as `credentials.json`

---

### 2. Install Required Python Packages

```bash
pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
```

---

### 3. Configure Mapping Files

Rename the `gtm_ga4_mapping_tpl_TO_RENAME.csv` to  `gtm_ga4_mapping.csv`.

```csv
gtm_public_id,ga4_property_id
GTM-XXXXXX,123456789
GTM-YYYYYY,987654321
```

The first column contains your GTM container public IDs, and the second column contains the GA4 property IDs where annotations should be created.

---

### 4. Custom GA-Impacting Elements Configuration (Optional)

Edit the `ga_impact_config.py` file to specify any custom elements that should be considered GA-impacting:

```python
# Configuration for elements that impact GA tracking
GA_IMPACT_ELEMENTS = {
    'tags': [
        'globalConsent',
        'Consent Mode',
        # Add any custom tags that affect GA tracking
    ],
    'variables': [
        'gaProperty',
        # Add any custom variables that affect GA tracking
    ],
    'triggers': [
        # Add any custom triggers that affect GA tracking
    ]
}
```

---

## How to Run

### Initial Setup

1. Clone this repository  
2. Place your `credentials.json` in the root directory  
3. Configure your `gtm_ga4_mapping.csv` file  
4. Run the initial setup to create version tracking baseline:

```bash
python check_versions.py
```

---

### Regular Usage

To manually check for GTM changes and create annotations:

```bash
python check_versions.py
```

---

### Automated Monitoring (Cron Job)

Set up a cron job to run the script at regular intervals:

```bash
# Check for GTM changes every hour
0 * * * * cd /path/to/GTM-GA4-annotations && python check_versions.py >> /path/to/logs/gtm_check.log 2>&1
```

---

## How It Works

### Workflow

1. `check_versions.py` retrieves the latest published version of each GTM container  
2. It compares these versions with the previously stored versions in `last_versions.json`  
3. When a version change is detected, it calls `main.py` with the specific changed containers  
4. `main.py` uses `change_detection.py` to identify exactly what changed  
5. `ga_impact_detection.py` analyzes if those changes affect GA tracking  
6. If impact is found, the tool creates an annotation in GA4 via `annotation_service.py`  
7. Version information is updated in `last_versions.json`

---

### Impact Detection Logic

The tool identifies GA impact through several sophisticated checks:

- **Direct GA Tag Changes**: Any modifications to GA4 tags, config, or events  
- **Consent Mode Changes**: Modifications to Simo Ahava's template or custom HTML consent implementations  
- **Setup Tag Dependencies**: Changes to tags that fire before GA tags  
- **Variable Impact Chains**: Deep recursive analysis of variable dependencies  
- **Trigger Relationships**: Changes to triggers that control GA tag firing  
- **Custom Configuration**: User-defined GA-impacting elements  

---

## File Structure

- `check_versions.py` - Main entry point for cron job, detects version changes  
- `main.py` - Core analysis logic, called when changes are detected  
- `change_detection.py` - Compares GTM versions and identifies what changed  
- `ga_impact_detection.py` - Analyzes changes to detect GA4 impact  
- `annotation_service.py` - Creates GA4 annotations  
- `ga_impact_config.py` - Optional config file for custom impact rules  
- `last_versions.json` - Stores the last checked version for each container  
- `gtm_ga4_mapping.csv` - Maps GTM container IDs to GA4 property IDs  
- `credentials.json` - Service account credentials for API access