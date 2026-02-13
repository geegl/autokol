"""
发送历史记录管理
保存和读取邮件发送记录，并支持云端同步
"""
import json
import os
import requests
import streamlit as st
from datetime import datetime
from src.config import OUTPUT_DIR
from src.services.tracking import TRACKING_BASE_URL

HISTORY_FILE = os.path.join(OUTPUT_DIR, "send_history.json")
FALLBACK_PROGRESS_API_KEY = os.environ.get("FALLBACK_PROGRESS_API_KEY", "autokol_progress_fallback_v1")

def _get_api_key():
    """获取 API Key (避免循环引用)"""
    try:
        if "PROGRESS_API_KEY" in st.secrets:
            return st.secrets["PROGRESS_API_KEY"]
    except:
        pass
    return os.environ.get("PROGRESS_API_KEY", FALLBACK_PROGRESS_API_KEY)

def _save_history_to_cloud(history):
    """保存历史记录到云端"""
    try:
        api_key = _get_api_key()
        # use mode='send_history'
        api_url = f"{TRACKING_BASE_URL}/api/progress?mode=send_history&key={api_key}"
        response = requests.post(api_url, json={"data": history}, timeout=5)
        return response.status_code == 200
    except Exception as e:
        # print(f"Cloud history save failed: {e}")
        return False

def _load_history_from_cloud():
    """从云端加载历史记录"""
    try:
        api_key = _get_api_key()
        api_url = f"{TRACKING_BASE_URL}/api/progress?mode=send_history&key={api_key}"
        response = requests.get(api_url, timeout=5)
        if response.status_code == 200:
            result = response.json()
            if result.get('success') and result.get('data') and result['data'].get('data'):
                return result['data']['data']
    except:
        pass
    return None

def load_send_history():
    """加载发送历史 (支持云端回退)"""
    local_history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                local_history = json.load(f)
        except:
            local_history = []
            
    # Cloud check logic (Simpler than progress: just merge or take larger?)
    # History is append-only usually. 
    # If local is empty/missing, try cloud.
    if not local_history:
        cloud_history = _load_history_from_cloud()
        if cloud_history:
            # Restore local
            try:
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                    json.dump(cloud_history, f, ensure_ascii=False, indent=2)
            except: pass
            return cloud_history
    
    # 也可以考虑合并：如果云端比本地多？
    # 暂时只做 "本地丢失时恢复"，避免复杂的合并冲突
    
    return local_history

def save_send_record(recipient_email, recipient_name, subject, status, error_type=None, mode="B2C"):
    """保存一条发送记录"""
    history = load_send_history()
    
    record = {
        "timestamp": datetime.now().isoformat(),
        "recipient_email": recipient_email,
        "recipient_name": recipient_name,
        "subject": subject,
        "status": status,  # "success" | "failed"
        "error_type": error_type,  # "AuthError" | "NetworkError" | "InvalidEmail" | "RateLimited" | None
        "mode": mode
    }
    
    history.append(record)
    
    # 只保留最近 500 条记录
    if len(history) > 500:
        history = history[-500:]
    
    # Save Local
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存发送历史失败: {e}")
        
    # Save Cloud (Fire and forget)
    _save_history_to_cloud(history)

def get_today_stats():
    """获取今日发送统计"""
    history = load_send_history()
    today = datetime.now().strftime('%Y-%m-%d')
    
    today_records = [r for r in history if r.get('timestamp', '').startswith(today)]
    
    success_count = sum(1 for r in today_records if r.get('status') == 'success')
    failed_count = sum(1 for r in today_records if r.get('status') == 'failed')
    
    return {
        "today_total": len(today_records),
        "today_success": success_count,
        "today_failed": failed_count,
        "records": today_records
    }

def get_recent_records(limit=50):
    """获取最近的发送记录"""
    history = load_send_history()
    return history[-limit:][::-1]  # 倒序返回最新的
