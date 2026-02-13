import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import streamlit as st
from src.config import ATTACHMENTS_DIR

# 错误类型分类
class EmailError:
    AUTH_ERROR = "AuthError"           # 认证失败（密码错误）
    NETWORK_ERROR = "NetworkError"     # 网络连接问题
    INVALID_EMAIL = "InvalidEmail"     # 邮箱地址无效
    RATE_LIMITED = "RateLimited"       # 发送频率限制
    UNKNOWN = "UnknownError"           # 其他未知错误

def classify_error(error_message):
    """根据错误信息分类错误类型"""
    msg = str(error_message).lower()
    
    if 'authentication' in msg or 'username and password not accepted' in msg or 'invalid credentials' in msg:
        return EmailError.AUTH_ERROR
    elif 'rate' in msg or 'limit' in msg or 'too many' in msg or 'quota' in msg:
        return EmailError.RATE_LIMITED
    elif 'recipient' in msg or 'invalid address' in msg or 'mailbox' in msg or 'does not exist' in msg:
        return EmailError.INVALID_EMAIL
    elif 'connection' in msg or 'timeout' in msg or 'network' in msg or 'refused' in msg:
        return EmailError.NETWORK_ERROR
    else:
        return EmailError.UNKNOWN

def send_email_gmail(to_email, subject, body_text, body_html, sender_email, sender_password, sender_name, mode, attachments_list):
    """
    通过 Gmail SMTP 发送邮件 (带 PDF 附件 + 追踪像素)
    
    返回: (success: bool, message: str, error_type: str|None)
    """
    try:
        # 防止输入中含有首尾空格，或 App Password 复制时带空格
        to_email = (to_email or "").strip()
        sender_email = (sender_email or "").strip()
        sender_password = (sender_password or "").replace(" ", "").strip()

        msg = MIMEMultipart('alternative')
        msg['From'] = f"{sender_name} <{sender_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject

        # body_html 已经包含了追踪像素
        msg.attach(MIMEText(body_text, 'plain'))
        msg.attach(MIMEText(body_html, 'html'))
        
        # 添加附件
        for file_name in (attachments_list or []):
            # 兼容两种输入：文件名（旧逻辑）或完整路径（新附件选择逻辑）
            candidates = [
                file_name,
                os.path.join(ATTACHMENTS_DIR, file_name)
            ]
            file_path = next((p for p in candidates if os.path.exists(p)), None)

            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {os.path.basename(file_path)}",
                )
                msg.attach(part)
            else:
                st.warning(f"⚠️ 找不到附件: {file_name} (路径: {file_path})")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
        
        return True, "邮件发送成功", None

    except smtplib.SMTPAuthenticationError as e:
        return False, f"❌ 认证失败: {str(e)}", EmailError.AUTH_ERROR
    except smtplib.SMTPRecipientsRefused as e:
        return False, f"❌ 收件人无效: {str(e)}", EmailError.INVALID_EMAIL
    except smtplib.SMTPException as e:
        error_type = classify_error(str(e))
        return False, f"❌ SMTP错误: {str(e)}", error_type
    except ConnectionError as e:
        return False, f"❌ 网络连接失败: {str(e)}", EmailError.NETWORK_ERROR
    except TimeoutError as e:
        return False, f"❌ 连接超时: {str(e)}", EmailError.NETWORK_ERROR
    except Exception as e:
        error_type = classify_error(str(e))
        return False, f"❌ {str(e)}", error_type
