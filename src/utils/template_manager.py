
import json
import os
from src.utils.templates import EMAIL_BODY_HTML_TEMPLATE, get_email_subjects

# 配置文件路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
USER_TEMPLATES_FILE = os.path.join(BASE_DIR, "config", "user_templates.json")

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

def _save_templates_internal(templates):
    """Internal helper to save templates without recursion"""
    try:
        os.makedirs(os.path.dirname(USER_TEMPLATES_FILE), exist_ok=True)
        with open(USER_TEMPLATES_FILE, 'w', encoding='utf-8') as f:
            json.dump(templates, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving template: {e}")
        return False

def load_user_templates():
    """Load user templates from JSON file"""
    if os.path.exists(USER_TEMPLATES_FILE):
        try:
            with open(USER_TEMPLATES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load user templates: {e}")
    
    # If file doesn't exist, init with default
    defaults = _init_default_templates()
    # Save directly using internal method to avoid recursion
    _save_templates_internal(defaults)
    return defaults

def save_user_template(name, subject, body):
    """Save a new template or update existing one"""
    # Load current templates (this will handle init if needed)
    templates = load_user_templates()
    
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
    
    # Write to file using internal helper
    return _save_templates_internal(templates)

def delete_user_template(name):
    """Delete a template by name"""
    # Load current templates
    current_templates = load_user_templates()
    new_templates = [t for t in current_templates if t["name"] != name]
    
    return _save_templates_internal(new_templates)
