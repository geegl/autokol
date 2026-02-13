import hashlib
import json
import os
from datetime import datetime

import requests
import streamlit as st

from src.services.tracking import TRACKING_BASE_URL


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAPPING_PROFILES_FILE = os.path.join(BASE_DIR, "config", "column_mapping_profiles.json")
FALLBACK_PROGRESS_API_KEY = os.environ.get("FALLBACK_PROGRESS_API_KEY", "autokol_progress_fallback_v1")


def _normalize_col_name(name):
    text = str(name).strip().lower()
    return "".join(ch for ch in text if ch.isalnum() or ("\u4e00" <= ch <= "\u9fff"))


def _column_signature(columns):
    normalized = sorted(_normalize_col_name(c) for c in columns if str(c).strip())
    raw = "|".join(normalized)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _get_api_key():
    try:
        if "PROGRESS_API_KEY" in st.secrets:
            return st.secrets["PROGRESS_API_KEY"]
    except Exception:
        pass
    return os.environ.get("PROGRESS_API_KEY", FALLBACK_PROGRESS_API_KEY)


def _iter_api_keys():
    primary = _get_api_key()
    keys = [primary]
    if primary != FALLBACK_PROGRESS_API_KEY:
        keys.append(FALLBACK_PROGRESS_API_KEY)
    return keys


def _default_profiles():
    return {"version": 1, "items": []}


def _load_local_profiles():
    if not os.path.exists(MAPPING_PROFILES_FILE):
        return None
    try:
        with open(MAPPING_PROFILES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            return data
    except Exception:
        pass
    return None


def _save_local_profiles(data):
    try:
        os.makedirs(os.path.dirname(MAPPING_PROFILES_FILE), exist_ok=True)
        with open(MAPPING_PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _load_cloud_profiles():
    for key in _iter_api_keys():
        try:
            api_url = f"{TRACKING_BASE_URL}/api/progress?mode=mapping_profiles&key={key}"
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                result = response.json()
                payload = result.get("data", {}).get("data")
                if isinstance(payload, dict) and isinstance(payload.get("items"), list):
                    return payload
                return None
            if response.status_code != 401:
                return None
        except Exception:
            return None
    return None


def _save_cloud_profiles(data):
    for key in _iter_api_keys():
        try:
            api_url = f"{TRACKING_BASE_URL}/api/progress?mode=mapping_profiles&key={key}"
            response = requests.post(api_url, json={"data": data}, timeout=10)
            if response.status_code == 200:
                return True
            if response.status_code != 401:
                return False
        except Exception:
            return False
    return False


def _profile_timestamp(item):
    return str(item.get("updated_at", ""))


def load_mapping_profiles():
    local = _load_local_profiles()
    cloud = _load_cloud_profiles()

    final = local
    if cloud:
        if not local or len(cloud.get("items", [])) >= len(local.get("items", [])):
            final = cloud
            _save_local_profiles(final)

    if not final:
        final = _default_profiles()
        _save_local_profiles(final)

    return final


def get_persisted_mapping(mode, source_name, columns):
    if not source_name or not columns:
        return None

    source_key = os.path.basename(source_name).strip().lower()
    col_set = set(columns)
    signature = _column_signature(columns)

    profiles = load_mapping_profiles()
    items = profiles.get("items", [])
    if not items:
        return None

    exact = []
    fallback = []
    for item in items:
        if item.get("mode") != mode:
            continue
        if item.get("source_name") != source_key:
            continue
        mapping = item.get("mapping", {})
        if not isinstance(mapping, dict):
            continue
        clean_mapping = {k: v for k, v in mapping.items() if v in col_set}
        if not clean_mapping:
            continue
        if item.get("column_signature") == signature:
            exact.append((item, clean_mapping))
        else:
            fallback.append((item, clean_mapping))

    if exact:
        exact.sort(key=lambda x: _profile_timestamp(x[0]), reverse=True)
        return exact[0][1]

    if fallback:
        fallback.sort(key=lambda x: _profile_timestamp(x[0]), reverse=True)
        return fallback[0][1]

    return None


def save_persisted_mapping(mode, source_name, columns, mapping):
    if not source_name or not columns or not isinstance(mapping, dict):
        return False

    source_key = os.path.basename(source_name).strip().lower()
    signature = _column_signature(columns)
    col_set = set(columns)
    clean_mapping = {k: v for k, v in mapping.items() if isinstance(v, str) and v in col_set}
    if not clean_mapping:
        return False

    profiles = load_mapping_profiles()
    items = [i for i in profiles.get("items", []) if not (
        i.get("mode") == mode and
        i.get("source_name") == source_key and
        i.get("column_signature") == signature
    )]

    items.append({
        "mode": mode,
        "source_name": source_key,
        "column_signature": signature,
        "mapping": clean_mapping,
        "updated_at": datetime.utcnow().isoformat()
    })

    # 限制大小，防止文件无限增长
    if len(items) > 300:
        items = sorted(items, key=_profile_timestamp)[-300:]

    profiles["items"] = items
    local_ok = _save_local_profiles(profiles)
    if local_ok:
        _save_cloud_profiles(profiles)
    return local_ok

