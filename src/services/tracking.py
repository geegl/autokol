import re
from datetime import datetime
from urllib.parse import quote

# 默认追踪服务 URL
TRACKING_BASE_URL = "https://autokol.vercel.app"

def generate_email_id(mode, idx, recipient_email, recipient_name):
    """生成包含收件人信息的邮件追踪 ID"""
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', str(recipient_name))[:20]
    clean_email = str(recipient_email).replace('@', '-at-').replace('.', '-')[:30]
    timestamp = int(datetime.now().timestamp())
    return f"{mode}_{idx}_{timestamp}_{clean_email}_{clean_name}"

def generate_tracking_pixel(email_id, tracking_url=None):
    """生成追踪像素 HTML"""
    if not tracking_url:
        return ""
    # 确保 URL 不以斜杠结尾
    if tracking_url.endswith('/'):
        tracking_url = tracking_url[:-1]
    return f'<img src="{tracking_url}/api/open/{email_id}" width="1" height="1" style="display:none" alt="">'

def generate_tracked_link(email_id, original_url, tracking_url=None):
    """生成追踪链接"""
    if not tracking_url:
        return original_url
    if tracking_url.endswith('/'):
        tracking_url = tracking_url[:-1]
    encoded_url = quote(original_url, safe='')
    return f"{tracking_url}/api/click/{email_id}?url={encoded_url}"
