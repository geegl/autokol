import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import streamlit as st

# Resend Support
try:
    import resend
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content
    from sendgrid.helpers.mail import Attachment, FileContent, FileName, FileType, Disposition
    from sendgrid.helpers.mail import TrackingSettings, ClickTracking, OpenTracking
except ImportError:
    pass

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
            # 假设附件在根目录下
            file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), file_name)
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
                # st.toast(f"📎 已添加附件: {file_name}")
            else:
                st.warning(f"⚠️ 找不到附件: {file_name}")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
        
        return True, "邮件发送成功"

    except Exception as e:
        return False, f"❌ {str(e)}"

def send_email_resend(to_email, subject, body_text, body_html, sender_email, sender_name, resend_api_key, mode, attachments_list):
    """通过 Resend 发送邮件（带追踪和 PDF 附件）"""
    try:
        resend.api_key = resend_api_key
        
        message = Mail(
            from_email=Email(sender_email, sender_name),
            to_emails=To(to_email),
            subject=subject,
            plain_text_content=Content("text/plain", body_text),
            html_content=Content("text/html", body_html)
        )
        
        # 添加附件
        for file_name in attachments_list:
            file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), file_name)
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    data = f.read()
                    import base64
                    encoded_file = base64.b64encode(data).decode()
                    
                attachment = Attachment(
                    FileContent(encoded_file),
                    FileName(file_name),
                    FileType('application/pdf'),
                    Disposition('attachment')
                )
                message.add_attachment(attachment)

        # 启用追踪
        message.tracking_settings = TrackingSettings(
            click_tracking=ClickTracking(enable=True, enable_text=False),
            open_tracking=OpenTracking(enable=True)
        )

        sg = SendGridAPIClient(resend_api_key)
        response = sg.client.mail.send.post(request_body=message.get())
        
        if response.status_code >= 200 and response.status_code < 300:
            return True, "邮件发送成功"
        else:
            return False, f"邮件发送失败: {response.body}"
    except Exception as e:
        return False, f"❌ {str(e)}"
