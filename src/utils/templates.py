"""
邮件模板 - 从配置文件加载
"""
import os
import yaml

# 配置文件路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_FILE = os.path.join(BASE_DIR, "config", "email_settings.yaml")

# 默认配置（配置文件不存在时使用）
DEFAULT_CONFIG = {
    "email_subjects": [
        "Utopai Studios Creator Program: Amplify Your Vision"
    ],
    "sender": {
        "name": "Cecilia",
        "title": "Director of Creative Partnerships"
    },
    "calendly_link": "https://calendly.com/cecilia-utopaistudios/30min"
}

def load_email_config():
    """加载邮件配置文件"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Warning: Failed to load email config: {e}")
    return DEFAULT_CONFIG

# 加载配置
_config = load_email_config()

# 导出配置值
EMAIL_SUBJECTS = _config.get("email_subjects", DEFAULT_CONFIG["email_subjects"])
# 兼容旧配置 (如果用户没更新 yaml)
if not isinstance(EMAIL_SUBJECTS, list):
    EMAIL_SUBJECTS = [str(EMAIL_SUBJECTS)]

CALENDLY_LINK = _config.get("calendly_link", DEFAULT_CONFIG["calendly_link"])

def get_email_subjects():
    """获取所有可用的邮件主题"""
    return EMAIL_SUBJECTS

# 邮件模板 (保持原有格式，支持变量替换)
EMAIL_BODY_TEMPLATE = """Hi {creator_name},

I'm {sender_name} from Utopai Studios. We're building a "Cinematic Storytelling Engine" for people who care about story first.

Loved your work on {project_title} – particularly the {technical_detail}.

It got me thinking: how many visionary scripts are shelved not for lack of talent, but because the production scale feels out of reach? At Utopai Studios, we're building a path to help creators move ambitious ideas forward without getting boxed in by scale, time, or existing production limits.

Think less "AI video tool," more director-level control. Our system is designed to maintain perfect character and scene consistency across shots and understand WGA scripts and concept art as direct instructions. It is like a second unit that helps you explore ideas faster, without taking creative control away from you.

A Direct Invitation
Given your visual style, I believe your perspective would be invaluable. We're curating a small group of Pioneer Creators for early collaboration. This includes:
- ✅ Full platform access + signon bonus to onboard
- ✅ Eligibility for a Pioneer Grant for project development
- ✅ Co-credit & distribution pathways for collaborative work

A Simple Way to See If It's a Fit
No lengthy forms. We've made a 2-minute demo that shows our workflow turning a script into coherent scenes. If you're curious:

Simply reply with:
1. "Demo" – and I'll send the video link straight away.
2. "More info" – for a detailed brief on the Pioneer program.
3. "Talk" – to schedule a 15-minute chat soon. Book a meeting: https://calendly.com/cecilia-utopaistudios/30min

Looking forward to hearing your thoughts.

Best,
{sender_name}
{sender_title}
Utopai Studios"""

EMAIL_BODY_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<p>Hi {creator_name},</p>

<p>I'm {sender_name} from Utopai Studios. We're building a "Cinematic Storytelling Engine" for people who care about story first.</p>

<p>Loved your work on <strong>{project_title}</strong> – particularly the <strong>{technical_detail}</strong>.</p>

<p>It got me thinking: how many visionary scripts are shelved not for lack of talent, but because the production scale feels out of reach? At Utopai Studios, we're building a path to help creators move ambitious ideas forward without getting boxed in by scale, time, or existing production limits.</p>

<p>Think less "AI video tool," more director-level control. Our system is designed to maintain perfect character and scene consistency across shots and understand WGA scripts and concept art as direct instructions. It is like a second unit that helps you explore ideas faster, without taking creative control away from you.</p>

<p><strong>A Direct Invitation</strong><br>
Given your visual style, I believe your perspective would be invaluable. We're curating a small group of Pioneer Creators for early collaboration. This includes:</p>
<ul>
<li>✅ Full platform access + signon bonus to onboard</li>
<li>✅ Eligibility for a Pioneer Grant for project development</li>
<li>✅ Co-credit & distribution pathways for collaborative work</li>
</ul>

<p><strong>A Simple Way to See If It's a Fit</strong><br>
No lengthy forms. We've made a 2-minute demo that shows our workflow turning a script into coherent scenes. If you're curious:</p>

<p>Simply reply with:</p>
<ol>
<li>"Demo" – and I'll send the video link straight away.</li>
<li>"More info" – for a detailed brief on the Pioneer program.</li>
<li>"Talk" – to schedule a 15-minute chat soon. <a href="{calendly_link}">Book a meeting</a>.</li>
</ol>

<p>Looking forward to hearing your thoughts.</p>

<p>Best,<br>
{sender_name}<br>
{sender_title}<br>
Utopai Studios</p>
{tracking_pixel}
</body>
</html>"""


def reload_config():
    """重新加载配置（用于热更新）"""
    global _config, EMAIL_SUBJECT, CALENDLY_LINK
    _config = load_email_config()
    EMAIL_SUBJECT = _config.get("email_subject", DEFAULT_CONFIG["email_subject"])
    CALENDLY_LINK = _config.get("calendly_link", DEFAULT_CONFIG["calendly_link"])
