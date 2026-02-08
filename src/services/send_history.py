"""
发送历史记录管理
保存和读取邮件发送记录
"""
import json
import os
from datetime import datetime
from src.config import OUTPUT_DIR

HISTORY_FILE = os.path.join(OUTPUT_DIR, "send_history.json")

def load_send_history():
    """加载发送历史"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

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
    
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存发送历史失败: {e}")

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
