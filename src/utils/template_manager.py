
import json
import os
import requests
import streamlit as st
from src.utils.templates import EMAIL_BODY_HTML_TEMPLATE, get_email_subjects
from src.services.tracking import TRACKING_BASE_URL

FALLBACK_PROGRESS_API_KEY = os.environ.get("FALLBACK_PROGRESS_API_KEY", "autokol_progress_fallback_v1")

# 配置文件路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
USER_TEMPLATES_FILE = os.path.join(BASE_DIR, "config", "user_templates.json")

def _get_progress_api_key():
    """Duplicate of helpers._get_progress_api_key to avoid circular imports"""
    try:
        if "PROGRESS_API_KEY" in st.secrets:
            return st.secrets["PROGRESS_API_KEY"]
    except:
        pass
    return os.environ.get("PROGRESS_API_KEY", FALLBACK_PROGRESS_API_KEY)


def _iter_api_keys():
    """Try configured key first, then fallback key."""
    primary = _get_progress_api_key()
    keys = [primary]
    if primary != FALLBACK_PROGRESS_API_KEY:
        keys.append(FALLBACK_PROGRESS_API_KEY)
    return keys

def _save_to_cloud(templates):
    """Save templates to cloud (using progress API with mode='user_templates')"""
    try:
        for key in _iter_api_keys():
            # Use mode='user_templates' to sequester data
            api_url = f"{TRACKING_BASE_URL}/api/progress?mode=user_templates&key={key}"
            # API expects {data: [...]} 
            # For progress (df), data is list of records.
            # For templates, it is list of dicts. Compatible.
            response = requests.post(api_url, json={"data": templates}, timeout=10)
            if response.status_code == 200:
                return True
            if response.status_code != 401:
                return False
        return False
    except Exception:
        return False

def _load_from_cloud():
    """Load templates from cloud"""
    try:
        for key in _iter_api_keys():
            api_url = f"{TRACKING_BASE_URL}/api/progress?mode=user_templates&key={key}"
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                result = response.json()
                # Structure: {success: true, data: {data: [...]}}
                if result.get('success') and result.get('data') and result['data'].get('data'):
                    return result['data']['data']
                return None
            if response.status_code != 401:
                return None
    except Exception:
        pass
    return None

def _init_default_templates():
    """Fail-safe: Return default templates if no file exists"""
    subjects = get_email_subjects()
    default_subject = subjects[0] if subjects else "Default Subject"
    
    return [
        {
            "name": "Default Template",
            "subject": default_subject,
            "body": EMAIL_BODY_HTML_TEMPLATE # This assumes it's already HTML
        }
    ]

def _save_templates_internal(templates, sync_cloud=False):
    """Internal helper to save templates without recursion"""
    success = False
    try:
        os.makedirs(os.path.dirname(USER_TEMPLATES_FILE), exist_ok=True)
        with open(USER_TEMPLATES_FILE, 'w', encoding='utf-8') as f:
            json.dump(templates, f, indent=4, ensure_ascii=False)
        success = True
    except Exception as e:
        print(f"Error saving template: {e}")
    
    if success and sync_cloud:
        # Fire and forget cloud sync
        _save_to_cloud(templates)
        
    return success

def load_user_templates():
    """Load user templates from JSON file (with Cloud Sync fallback)"""
    local_templates = None
    
    # 1. Try Local
    if os.path.exists(USER_TEMPLATES_FILE):
        try:
            with open(USER_TEMPLATES_FILE, 'r', encoding='utf-8') as f:
                local_templates = json.load(f)
            if not isinstance(local_templates, list):
                local_templates = None
        except Exception as e:
            print(f"Warning: Failed to load user templates: {e}")
    
    # 2. Try Cloud (Always check, or check if local missing?)
    # On Streamlit Cloud reboot, local file is gone (or reverted to git commit state which might be empty/default).
    # So we should check Cloud.
    cloud_templates = _load_from_cloud()
    if cloud_templates is not None and not isinstance(cloud_templates, list):
        cloud_templates = None
    
    final_templates = local_templates
    
    # 3. Merge Strategy
    if cloud_templates:
        if not local_templates:
            # Only Cloud has data -> Restore
            final_templates = cloud_templates
            _save_templates_internal(final_templates, sync_cloud=False) # Restore local, no need to push back immediately
            # st.toast("☁️ Restored templates from Cloud Backup")
            
        else:
            # Both exists. 
            # Heuristic: If Cloud has MORE templates, assume it's newer/better?
            if len(cloud_templates) > len(local_templates):
                 final_templates = cloud_templates
                 _save_templates_internal(final_templates, sync_cloud=False)
                 # st.toast("☁️ Synced templates from Cloud")
            
            # Special case: Local is Default (1 item), Cloud has many.
            elif len(local_templates) == 1 and local_templates[0]['name'] == 'Default Template' and len(cloud_templates) > 0:
                 final_templates = cloud_templates
                 _save_templates_internal(final_templates, sync_cloud=False)

    
    if not final_templates:
        # If still nothing, init default
        defaults = _init_default_templates()
        _save_templates_internal(defaults, sync_cloud=True) # Push default to Cloud to init
        return defaults

    return final_templates

def save_user_template(name, subject, body):
    """Save a new template or update existing one"""
    # Load current templates (local first)
    # We use internal load logic to get latest state
    templates = load_user_templates()
    if not isinstance(templates, list):
        templates = _init_default_templates()
    
    # Check if exists
    existing = next((t for t in templates if t["name"] == name), None)
    if existing:
        existing["subject"] = subject
        existing["body"] = body
    else:
        templates.append({
            "name": name,
            "subject": subject,
            "body": body
        })
    
    # Write to file AND Cloud
    return _save_templates_internal(templates, sync_cloud=True)

def delete_user_template(name):
    """Delete a template by name"""
    # Load current templates
    current_templates = load_user_templates()
    if not isinstance(current_templates, list):
        current_templates = _init_default_templates()
    new_templates = [t for t in current_templates if t["name"] != name]
    
    return _save_templates_internal(new_templates, sync_cloud=True)
