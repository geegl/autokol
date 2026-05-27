"""
Shared API key helpers for cloud sync (progress, templates, history, mapping profiles).
Centralized here to avoid duplication across 4 modules.
"""
import os

import streamlit as st

FALLBACK_PROGRESS_API_KEY = os.environ.get(
    "FALLBACK_PROGRESS_API_KEY", "autokol_progress_fallback_v1"
)


def get_progress_api_key():
    """Return the configured PROGRESS_API_KEY (st.secrets > env > fallback)."""
    try:
        if "PROGRESS_API_KEY" in st.secrets:
            return st.secrets["PROGRESS_API_KEY"]
    except Exception:
        pass
    return os.environ.get("PROGRESS_API_KEY", FALLBACK_PROGRESS_API_KEY)


def iter_api_keys():
    """Yield configured key first, then fallback key (deduplicated)."""
    primary = get_progress_api_key()
    keys = [primary]
    if primary != FALLBACK_PROGRESS_API_KEY:
        keys.append(FALLBACK_PROGRESS_API_KEY)
    return keys
