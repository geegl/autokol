import re
import hmac
import hashlib
import base64
import os
import requests
from datetime import datetime
from urllib.parse import quote

# 默认追踪服务 URL
TRACKING_BASE_URL = "https://autokol.vercel.app"

# 退订签名密钥（从环境变量读取）
UNSUBSCRIBE_SECRET_KEY = os.environ.get("UNSUBSCRIBE_SECRET_KEY", "autokol_default_unsub_key_v1")

def generate_email_id(mode, idx, recipient_email, recipient_name):
    """生成包含收件人信息的邮件追踪 ID"""
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', str(recipient_name))[:20]
    clean_email = str(recipient_email).replace('@', '-at-').replace('.', '-')[:30]
    timestamp = int(datetime.now().timestamp())
    return f"{mode}_{idx}_{timestamp}_{clean_email}_{clean_name}"

def generate_tracking_pixel(email_id, tracking_url=None):
    """生成追踪像素 HTML (带防缓存参数)"""
    if not tracking_url:
        return ""
    # 确保 URL 不以斜杠结尾
    if tracking_url.endswith('/'):
        tracking_url = tracking_url[:-1]
    # 加入时间戳防止浏览器缓存
    cache_buster = int(datetime.now().timestamp() * 1000)
    return f'<img src="{tracking_url}/api/open/{email_id}?t={cache_buster}" width="1" height="1" style="display:none" alt="">'


def generate_tracked_link(email_id, original_url, tracking_url=None):
    """生成追踪链接"""
    if not tracking_url:
        return original_url
    if tracking_url.endswith('/'):
        tracking_url = tracking_url[:-1]
    encoded_url = quote(original_url, safe='')
    return f"{tracking_url}/api/click/{email_id}?url={encoded_url}"


def generate_unsubscribe_url(recipient_email, tracking_url=None):
    """生成退订链接（base64 邮箱 + HMAC-SHA256 签名）"""
    if not tracking_url:
        tracking_url = TRACKING_BASE_URL
    if tracking_url.endswith('/'):
        tracking_url = tracking_url[:-1]

    normalized = (recipient_email or "").strip().lower()
    email_b64 = base64.urlsafe_b64encode(normalized.encode("utf-8")).decode("utf-8")
    token = hmac.new(
        UNSUBSCRIBE_SECRET_KEY.encode("utf-8"),
        normalized.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{tracking_url}/api/unsubscribe?email={email_b64}&token={token}"


def is_unsubscribed(recipient_email, tracking_url=None):
    """检查邮箱是否已退订（查询 Redis unsubscribe_set）"""
    if not tracking_url:
        tracking_url = TRACKING_BASE_URL
    if tracking_url.endswith('/'):
        tracking_url = tracking_url[:-1]

    normalized = (recipient_email or "").strip().lower()
    try:
        # 通过 stats API 检查（stats 包含所有联系人数据）
        resp = requests.get(f"{tracking_url}/api/stats", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            contact = data.get("contacts", {}).get(normalized, {})
            if contact.get("unsubscribed"):
                return True
    except Exception:
        pass
    return False


def replace_unsubscribe_url(html_body, recipient_email, tracking_url=None):
    """替换模板中的 {{unsubscribe_url}} 为实际退订链接"""
    unsub_url = generate_unsubscribe_url(recipient_email, tracking_url)
    return html_body.replace("{{unsubscribe_url}}", unsub_url)
