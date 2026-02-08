import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import streamlit as st
from src.config import ATTACHMENTS_DIR

def send_email_gmail(to_email, subject, body_text, body_html, sender_email, sender_password, sender_name, mode, attachments_list):
    """通过 Gmail SMTP 发送邮件 (带 PDF 附件 + 追踪像素)"""
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{sender_name} <{sender_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject

        # body_html 已经包含了追踪像素
        msg.attach(MIMEText(body_text, 'plain'))
        msg.attach(MIMEText(body_html, 'html'))
        
        # 添加附件
        for file_name in attachments_list:
            file_path = os.path.join(ATTACHMENTS_DIR, file_name)
            if os.path.exists(file_path):
                with open(file_path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {file_name}",
                )
                msg.attach(part)
            else:
                st.warning(f"⚠️ 找不到附件: {file_name} (路径: {file_path})")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
        
        return True, "邮件发送成功"

    except Exception as e:
        return False, f"❌ {str(e)}"
