import streamlit as st
import pandas as pd
import smtplib
import re
import time
import random
import threading
import os
import base64
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

# URL 编码 (用于追踪链接)
from urllib.parse import quote, urlencode

# 全局锁，用于控制 API 调用频率
api_lock = threading.Lock()
LAST_API_CALL_TIME = 0

# 保存文件路径
SAVE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- 页面配置 ---
st.set_page_config(page_title="Utopai Cold Email Engine", layout="wide")
st.title("🚀 Utopai Cold Email Engine")
st.caption("Gmail SMTP + 硅基流动 DeepSeek-V3.2 | 自动保存进度")

# --- B2B/B2C 配置 ---
MODE_CONFIG = {
    "B2B": {
        "name": "B2B 企业客户",
        "progress_file": os.path.join(SAVE_DIR, "autokol_progress_b2b.csv"),
        "attachments": [
            "Utopai Early Access - Creator FAQ - V2.pdf",
            "One-pager-enterprise.pdf"
        ],
        "columns": {
            "client_name": "客户名称",
            "contact_person": "决策人",
            "contact_info": "联系方式",
            "features": "核心特征",
            "pain_point": "破冰话术要点"
        },
        "has_pregenerated_content": False
    },
    "B2C": {
        "name": "B2C 创作者",
        "progress_file": os.path.join(SAVE_DIR, "autokol_progress_b2c.csv"),
        "attachments": [
            "Utopai Early Access - Creator FAQ - V2.pdf",
            "One-pager_final.pdf"
        ],
        "columns": {
            "client_name": "Name",
            "contact_person": "Name",
            "contact_info": "Contact",
            "features": "Specialty",
            "pain_point": "Ice Breaker",
            "pregenerated": "Unnamed: 10"  # 已有的英文内容
        },
        "has_pregenerated_content": True
    }
}

# --- 邮件模板 ---
EMAIL_SUBJECT = "Utopai Studios Creator Program: Amplify Your Vision - Early and exclusive access to a new AI model for cinematic storytelling?"

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
<li>"Talk" – to schedule a 15-minute chat soon. <a href="https://calendly.com/cecilia-utopaistudios/30min">Book a meeting</a>.</li>
</ol>

<p>Looking forward to hearing your thoughts.</p>

<p>Best,<br>
{sender_name}<br>
{sender_title}<br>
Utopai Studios</p>
</body>
</html>"""

# --- 侧边栏配置 ---
with st.sidebar:
    st.header("⚙️ 配置中心")
    
    st.subheader("1. LLM 设置 (硅基流动)")
    api_key = st.text_input("硅基流动 API Key", type="password", help="在 https://cloud.siliconflow.cn 获取")
    base_url = st.text_input("Base URL", value="https://api.siliconflow.cn/v1")
    model_name = st.text_input("Model Name", value="deepseek-ai/DeepSeek-V3.2")
    
    st.subheader("2. 邮箱设置 (Gmail)")
    email_user = st.text_input("Gmail/Workspace 地址", help="例如: growth@utopaistudios.com")
    email_pass = st.text_input("应用专用密码", type="password", help="在 Google 账户 → 安全性 → 两步验证 → 应用专用密码 中生成")
    
    st.subheader("3. 发件人信息")
    sender_name = st.text_input("Your Name", value="Cecilia")
    sender_title = st.text_input("Your Title", value="Director of Creative Partnerships")
    
    st.subheader("4. 邮件追踪 (可选)")
    tracking_url = st.text_input("追踪服务 URL", placeholder="https://your-tracker.vercel.app", help="部署 email-tracker 后填入")
    if tracking_url:
        st.success("✅ 追踪已启用 - 将自动记录打开率和点击率")
    else:
        st.info("💡 部署 email-tracker 到 Vercel 后可启用追踪")
    
    st.divider()

# --- 工具函数 ---

def extract_email(contact_str):
    """从联系方式字符串中提取邮箱地址"""
    if pd.isna(contact_str):
        return None
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    matches = re.findall(email_pattern, str(contact_str))
    return matches[0] if matches else None

def extract_english_name(name_str):
    """从姓名字符串中提取英文名（去除中文和括号内容）"""
    if pd.isna(name_str):
        return "there"
    name = str(name_str)
    # 去除 @ 符号
    name = name.replace('@', '')
    # 去除括号及其内容
    name = re.sub(r'[（(][^）)]*[）)]', '', name)
    # 去除中文字符
    name = re.sub(r'[\u4e00-\u9fff]+', '', name)
    # 清理多余空格
    name = ' '.join(name.split()).strip()
    return name if name else "there"

def save_progress(df, mode):
    """保存进度到本地 CSV"""
    try:
        progress_file = MODE_CONFIG[mode]["progress_file"]
        df.to_csv(progress_file, index=False, encoding='utf-8-sig')
    except Exception as e:
        st.warning(f"保存进度失败: {e}")

def load_progress(mode):
    """加载上次保存的进度"""
    progress_file = MODE_CONFIG[mode]["progress_file"]
    if os.path.exists(progress_file):
        try:
            return pd.read_csv(progress_file, encoding='utf-8-sig')
        except:
            return None
    return None

def clear_progress(mode):
    """清除进度文件"""
    progress_file = MODE_CONFIG[mode]["progress_file"]
    if os.path.exists(progress_file):
        os.remove(progress_file)

def generate_with_llm(prompt, client, model, max_retries=3):
    """调用 LLM 生成文本 (硅基流动 API，关闭思考模式)"""
    global LAST_API_CALL_TIME
    
    for attempt in range(max_retries):
        try:
            with api_lock:
                elapsed = time.time() - LAST_API_CALL_TIME
                if elapsed < 1.0:
                    time.sleep(1.0 - elapsed)
                LAST_API_CALL_TIME = time.time()
            
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=200,
                extra_body={"enable_thinking": False}
            )
            
            message = response.choices[0].message
            result = message.content
            
            if result is None:
                return "[Error: Empty response from model]"
            
            # 返回完整结果（保留多行），只做基本清理
            result = result.strip()
            
            return result if result else "[Error: Empty content]"
            
        except Exception as e:
            error_str = str(e)
            if '429' in error_str:
                wait_time = (2 ** attempt) * 3
                time.sleep(wait_time)
                continue
            return f"[Error: {error_str}]"
    
    return "[Error: Max retries exceeded]"

def generate_single_row(idx, row, client, model, df, mode, progress_placeholder):
    """生成单行数据并立即保存"""
    config = MODE_CONFIG[mode]
    cols = config["columns"]
    
    client_name = row.get(cols["client_name"], '')
    features = row.get(cols["features"], '')
    pain_point = row.get(cols["pain_point"], '')
    
    # B2C 模式：检查 Unnamed:10 列的内容类型
    if config["has_pregenerated_content"] and "pregenerated" in cols:
        pregenerated = row.get(cols["pregenerated"], '')
        
        if pd.notna(pregenerated) and str(pregenerated).strip():
            text = str(pregenerated).strip()
            
            # 辅助函数：清理 AI 输出中可能包含的前缀
            def clean_title(s):
                s = s.strip().strip('"\'')
                # 去除各种可能的前缀
                s = re.sub(r'^PROJECT_TITLE:\s*', '', s, flags=re.IGNORECASE)
                s = re.sub(r'^Loved your work on\s*', '', s, flags=re.IGNORECASE)
                return s.strip().strip('"\'')
            
            def clean_detail(s):
                s = s.strip().strip('"\'')
                # 去除各种可能的前缀
                s = re.sub(r'^TECHNICAL_DETAIL:\s*', '', s, flags=re.IGNORECASE)
                s = re.sub(r'^particularly the\s*', '', s, flags=re.IGNORECASE)
                # 去除开头的冠词 (A/An/The)
                s = re.sub(r'^(A|An|The)\s+', '', s, flags=re.IGNORECASE)
                s = s.strip().strip('"\'')
                # 首字母小写（跟在 "particularly the" 后面更自然）
                if s and s[0].isupper():
                    s = s[0].lower() + s[1:]
                return s
            
            # 类型1: 已有好的英文格式 "Loved your work on XXX – particularly the YYY."
            match = re.search(r"Loved your work on (.+?) [–-] particularly the (.+?)\.?$", text)
            if match:
                project_title = clean_title(match.group(1))
                technical_detail = clean_detail(match.group(2))
                df.loc[idx, 'AI_Project_Title'] = project_title
                df.loc[idx, 'AI_Technical_Detail'] = technical_detail
                df.loc[idx, 'Content_Source'] = '✅ 已有英文'
                save_progress(df, mode)
                return idx, project_title, technical_detail
            
            # 检测是否有中文字符
            has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))
            
            # 检测是否是通用模板 (常见的通用短语)
            generic_patterns = [
                'interested in collaborating',
                'interested in collaboration',
                'creative projects',
                'film studio',
                'looking forward'
            ]
            is_generic = any(p in text.lower() for p in generic_patterns)
            
            # 类型2: 中文内容 → 翻译润色为 native speaker 英文
            if has_chinese:
                prompt = f"""You are a native English copywriter. Based on this Chinese text about a content creator, generate TWO things:

Chinese text: {text}
Creator: {client_name}
Specialty: {features}

Generate:
1. PROJECT_TITLE: A short phrase (2-6 words) describing their work/content type
   Example: "AI Cinematic Short Films" or "fantasy art videos" or "film review essays"
   
2. TECHNICAL_DETAIL: A specific compliment (5-12 words) about their style/quality
   Example: "visual consistency across interconnected scenes" or "cinematic pacing in the opening sequence"

IMPORTANT: Do NOT include "Loved your work on" or "particularly the" - just the content itself.

Output format (exactly like this):
PROJECT_TITLE: [your answer]
TECHNICAL_DETAIL: [your answer]"""
                
                result = generate_with_llm(prompt, client, model)
                
                # 解析结果
                title_match = re.search(r'PROJECT_TITLE:\s*(.+)', result)
                detail_match = re.search(r'TECHNICAL_DETAIL:\s*(.+)', result)
                
                if title_match and detail_match:
                    project_title = clean_title(title_match.group(1))
                    technical_detail = clean_detail(detail_match.group(1))
                else:
                    project_title = clean_title(client_name) if client_name else "your recent content"
                    technical_detail = "creative visual style and attention to detail"
                
                df.loc[idx, 'AI_Project_Title'] = project_title
                df.loc[idx, 'AI_Technical_Detail'] = technical_detail
                df.loc[idx, 'Content_Source'] = '🌐 中文翻译'
                save_progress(df, mode)
                return idx, project_title, technical_detail
            
            # 类型3: 通用英文模板 → 根据信息定制化
            elif is_generic:
                prompt = f"""You are a native English copywriter. Based on this creator's info, generate TWO things:

Creator: {client_name}
Specialty: {features}
Content focus: {pain_point}

Generate:
1. PROJECT_TITLE: A short phrase (2-6 words) describing their specific work/content type
   Example: "AI Cinematic Short Films" or "visual effects tutorials" or "film analysis videos"
   
2. TECHNICAL_DETAIL: A specific compliment (5-12 words) about their unique style/quality
   Example: "the cinematic depth you achieve with AI synthesis" or "how you blend traditional and modern techniques"

IMPORTANT: Do NOT include "Loved your work on" or "particularly the" - just the content itself.

Output format (exactly like this):
PROJECT_TITLE: [your answer]
TECHNICAL_DETAIL: [your answer]"""
                
                result = generate_with_llm(prompt, client, model)
                
                title_match = re.search(r'PROJECT_TITLE:\s*(.+)', result)
                detail_match = re.search(r'TECHNICAL_DETAIL:\s*(.+)', result)
                
                if title_match and detail_match:
                    project_title = clean_title(title_match.group(1))
                    technical_detail = clean_detail(detail_match.group(1))
                else:
                    project_title = clean_title(features) if features else "your recent content"
                    technical_detail = "unique creative vision and style"
                
                df.loc[idx, 'AI_Project_Title'] = project_title
                df.loc[idx, 'AI_Technical_Detail'] = technical_detail
                df.loc[idx, 'Content_Source'] = '🔧 定制化'
                save_progress(df, mode)
                return idx, project_title, technical_detail
    
    # 辅助函数（默认分支也需要）
    def clean_title(s):
        s = s.strip().strip('"\'')
        s = re.sub(r'^PROJECT_TITLE:\s*', '', s, flags=re.IGNORECASE)
        s = re.sub(r'^Loved your work on\s*', '', s, flags=re.IGNORECASE)
        return s.strip().strip('"\'')
    
    def clean_detail(s):
        s = s.strip().strip('"\'')
        s = re.sub(r'^TECHNICAL_DETAIL:\s*', '', s, flags=re.IGNORECASE)
        s = re.sub(r'^particularly the\s*', '', s, flags=re.IGNORECASE)
        # 去除开头的冠词 (A/An/The)
        s = re.sub(r'^(A|An|The)\s+', '', s, flags=re.IGNORECASE)
        s = s.strip().strip('"\'')
        # 首字母小写
        if s and s[0].isupper():
            s = s[0].lower() + s[1:]
        return s
    
    # 默认: 用 AI 从头生成
    prompt = f"""You are a native English copywriter. Based on this creator's info, generate TWO things:

Creator: {client_name}
Specialty: {features}
Style notes: {pain_point}

Generate:
1. PROJECT_TITLE: A short phrase (2-6 words) describing their content type
   Example: "AI-generated short films" or "fantasy art videos" or "film review essays"
   
2. TECHNICAL_DETAIL: A specific compliment (5-12 words) about their style/quality
   Example: "visual consistency across interconnected scenes" or "the way you blend AI tools with traditional storytelling"

IMPORTANT: Do NOT include "Loved your work on" or "particularly the" - just the content itself.

Output format (exactly like this):
PROJECT_TITLE: [your answer]
TECHNICAL_DETAIL: [your answer]"""
    
    result = generate_with_llm(prompt, client, model)
    
    title_match = re.search(r'PROJECT_TITLE:\s*(.+)', result)
    detail_match = re.search(r'TECHNICAL_DETAIL:\s*(.+)', result)
    
    if title_match and detail_match:
        project_title = clean_title(title_match.group(1))
        technical_detail = clean_detail(detail_match.group(1))
    else:
        # Fallback: 尝试按行解析
        lines = [l.strip() for l in result.split('\n') if l.strip()]
        project_title = clean_title(lines[0]) if lines else "your recent content"
        technical_detail = clean_detail(lines[1]) if len(lines) > 1 else "creative visual style"
    
    df.loc[idx, 'AI_Project_Title'] = project_title
    df.loc[idx, 'AI_Technical_Detail'] = technical_detail
    df.loc[idx, 'Content_Source'] = '🤖 AI生成'
    
    save_progress(df, mode)
    return idx, project_title, technical_detail

def render_full_email(row, sender_name, sender_title, mode):
    """渲染完整邮件内容"""
    config = MODE_CONFIG[mode]
    cols = config["columns"]
    
    raw_name = row.get(cols["contact_person"], 'Creator')
    creator_name = extract_english_name(raw_name)
    project_title = row.get('AI_Project_Title', '[Project Title]')
    technical_detail = row.get('AI_Technical_Detail', '[Technical Detail]')
    
    return EMAIL_BODY_TEMPLATE.format(
        creator_name=creator_name,
        sender_name=sender_name,
        sender_title=sender_title,
        project_title=project_title,
        technical_detail=technical_detail
    )

def send_email(to_email, subject, body_text, body_html, user, password, sender_name, mode):
    """通过 Gmail SMTP 发送邮件（带 PDF 附件）"""
    msg = MIMEMultipart('mixed')
    msg['From'] = f"{sender_name} <{user}>"
    msg['To'] = to_email
    msg['Subject'] = subject
    
    body_part = MIMEMultipart('alternative')
    part1 = MIMEText(body_text, 'plain', 'utf-8')
    part2 = MIMEText(body_html, 'html', 'utf-8')
    body_part.attach(part1)
    body_part.attach(part2)
    msg.attach(body_part)
    
    # 添加 PDF 附件（根据模式选择）
    attachments = MODE_CONFIG[mode]["attachments"]
    for filename in attachments:
        filepath = os.path.join(SAVE_DIR, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'rb') as f:
                    part = MIMEBase('application', 'pdf')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                    msg.attach(part)
            except Exception as e:
                print(f"Warning: Could not attach {filename}: {e}")
    
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(user, password)
        server.sendmail(user, to_email, msg.as_string())
        server.quit()
        return True, "✅ Sent (Gmail)"
    except Exception as e:
        return False, f"❌ {str(e)}"



# =============================================
# 主界面 - B2B/B2C 标签页
# =============================================

tab_b2b, tab_b2c = st.tabs(["🏢 B2B 企业客户", "🎨 B2C 创作者"])

def render_mode_ui(mode):
    """渲染特定模式的 UI"""
    config = MODE_CONFIG[mode]
    cols = config["columns"]
    state_key = f"df_data_{mode}"
    
    # 检查是否有保存的进度
    saved_progress = load_progress(mode)
    
    if saved_progress is not None and state_key not in st.session_state:
        st.info(f"📂 检测到 {config['name']} 的进度文件 ({len(saved_progress)} 条记录)")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📥 加载上次进度", type="primary", key=f"load_{mode}"):
                st.session_state[state_key] = saved_progress
                st.rerun()
        with col2:
            if st.button("🗑️ 清除进度，重新开始", key=f"clear_{mode}"):
                clear_progress(mode)
                st.rerun()
        with col3:
            st.download_button("📥 下载进度文件", saved_progress.to_csv(index=False), file_name=f"progress_{mode.lower()}.csv", key=f"download_{mode}")
    
    # 文件上传
    st.markdown("### 📂 上传 Leads 文件")
    st.caption(f"**{config['name']}** 模式 | 附件: {', '.join(config['attachments'])}")
    
    uploaded_file = st.file_uploader(f"上传 Excel/CSV 文件 ({mode})", type=['xlsx', 'csv'], key=f"uploader_{mode}")
    
    if uploaded_file is not None:
        # 读取文件
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        # 提取邮箱
        contact_col = cols["contact_info"]
        if contact_col in df.columns:
            df['Email'] = df[contact_col].apply(extract_email)
        else:
            st.error(f"找不到联系方式列 '{contact_col}'")
            return
        
        # 只保留有邮箱的行
        df_with_email = df[df['Email'].notna()].copy().reset_index(drop=True)
        
        st.success(f"✅ 已加载 {len(df)} 条数据，其中 **{len(df_with_email)} 条有邮箱** 可处理")
        
        if len(df_with_email) == 0:
            st.warning("没有找到有效邮箱，请检查数据")
            return
        
        st.session_state[state_key] = df_with_email
    
    # 处理数据
    if state_key in st.session_state:
        df = st.session_state[state_key]
        
        # =============================================
        # 第一步：生成 AI 话术
        # =============================================
        with st.expander("📝 第一步：生成 AI 话术", expanded=True):
            st.caption("为每个 Lead 生成个性化的 Project Title 和 Technical Detail")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                max_workers = st.slider(f"并发数量 ({mode})", min_value=1, max_value=5, value=2, help="建议设为 1-2 避免触发 API 限流", key=f"workers_{mode}")
            
            if st.button("🚀 生成话术", type="primary", disabled=not api_key, key=f"gen_phrases_{mode}"):
                if not api_key:
                    st.error("请先在侧边栏填写硅基流动 API Key")
                else:
                    # 初始化列
                    if 'AI_Project_Title' not in df.columns:
                        df['AI_Project_Title'] = None
                    if 'AI_Technical_Detail' not in df.columns:
                        df['AI_Technical_Detail'] = None
                    
                    # 筛选待处理的行
                    pending_mask = df['AI_Project_Title'].isna() | df['AI_Technical_Detail'].isna()
                    pending_indices = df[pending_mask].index.tolist()
                    
                    if len(pending_indices) == 0:
                        st.info("✅ 所有行已生成完毕")
                    else:
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        client = OpenAI(api_key=api_key, base_url=base_url)
                        completed = 0
                        
                        for idx in pending_indices:
                            row = df.loc[idx]
                            _, title, detail = generate_single_row(idx, row, client, model_name, df, mode, status_text)
                            completed += 1
                            progress_bar.progress(completed / len(pending_indices))
                            status_text.text(f"[{completed}/{len(pending_indices)}] 已生成: {title[:30]}...")
                        
                        st.session_state[state_key] = df
                        save_progress(df, mode)
                        st.success(f"✅ 已完成 {len(pending_indices)} 条话术生成")
                        st.rerun()
            
            # 显示结果
            if 'AI_Project_Title' in df.columns:
                display_cols = [cols["client_name"], cols["contact_person"], 'AI_Project_Title', 'AI_Technical_Detail']
                # 去重（B2C 模式下 client_name 和 contact_person 都是 Name）
                display_cols = list(dict.fromkeys([c for c in display_cols if c in df.columns]))
                st.dataframe(df[display_cols], use_container_width=True, height=300)
        
        # =============================================
        # 第二步：生成完整邮件
        # =============================================
        if 'AI_Project_Title' in df.columns and df['AI_Project_Title'].notna().any():
            st.markdown("### 📧 第二步：生成完整邮件")
            
            if st.button("✨ 生成所有邮件", key=f"gen_emails_{mode}"):
                df['Full_Email'] = df.apply(lambda row: render_full_email(row, sender_name, sender_title, mode), axis=1)
                st.session_state[state_key] = df
                save_progress(df, mode)
                st.success("✅ 已生成所有邮件内容")
                st.rerun()
            
            # 邮件预览
            if 'Full_Email' in df.columns:
                st.markdown("**邮件预览：**")
                valid_rows = df[df['Full_Email'].notna()]
                if len(valid_rows) > 0:
                    preview_options = valid_rows.apply(
                        lambda row: f"{row.get(cols['contact_person'], 'N/A')} ({row.get(cols['client_name'], 'N/A')})", axis=1
                    ).tolist()
                    
                    selected_idx = st.selectbox("选择 Lead 预览邮件", range(len(valid_rows)), format_func=lambda x: preview_options[x], key=f"preview_select_{mode}")
                    
                    if selected_idx is not None:
                        selected_row = valid_rows.iloc[selected_idx]
                        text_preview = render_full_email(selected_row, sender_name, sender_title, mode)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.text_area("📧 纯文本版本", value=text_preview, height=400, key=f"text_{mode}_{selected_idx}")
                        with col2:
                            st.markdown("**🌐 HTML 预览：**")
                            html_preview = EMAIL_BODY_HTML_TEMPLATE.format(
                                creator_name=extract_english_name(selected_row.get(cols['contact_person'], 'Creator')),
                                sender_name=sender_name,
                                sender_title=sender_title,
                                project_title=selected_row.get('AI_Project_Title', '[Project Title]'),
                                technical_detail=selected_row.get('AI_Technical_Detail', '[Technical Detail]')
                            )
                            st.components.v1.html(html_preview, height=400, scrolling=True)
        
        # =============================================
        # 第三步：邮件发送
        # =============================================
        if 'Full_Email' in df.columns and df['Full_Email'].notna().any():
            st.divider()
            st.markdown("### 📤 第三步：邮件发送")
            
            # 初始化发送状态
            if 'Send_Status' not in df.columns:
                df['Send_Status'] = '⏳ 待发送'
            if 'Selected' not in df.columns:
                df['Selected'] = True
            
            # 选择发送列表（去重避免 B2C Name 列重复）
            display_cols_send = [cols["client_name"], cols["contact_person"], 'Email', 'Send_Status', 'Selected']
            display_cols_send = list(dict.fromkeys([c for c in display_cols_send if c in df.columns]))
            
            edited_df = st.data_editor(
                df[display_cols_send],
                column_config={"Selected": st.column_config.CheckboxColumn("选择")},
                disabled=[c for c in display_cols_send if c != 'Selected'],
                use_container_width=True,
                key=f"send_editor_{mode}"
            )
            
            df['Selected'] = edited_df['Selected']
            
            selected_count = df['Selected'].sum()
            pending_count = ((df['Selected'] == True) & (df['Send_Status'] == '⏳ 待发送')).sum()
            st.info(f"已选择 **{selected_count}** 个 Leads，其中 **{pending_count}** 个待发送")
            
            # 发送设置
            col1, col2, _ = st.columns(3)
            with col1:
                delay_min = st.number_input("最小间隔 (秒)", value=30, min_value=10, key=f"delay_min_{mode}")
            with col2:
                delay_max = st.number_input("最大间隔 (秒)", value=60, min_value=20, key=f"delay_max_{mode}")
            
            st.warning(f"⚠️ 附件: {', '.join(config['attachments'])}")
            
            # 测试发送
            st.markdown("---")
            st.markdown("#### 🧪 测试发送")
            
            test_col1, test_col2 = st.columns([2, 1])
            with test_col1:
                test_email = st.text_input("测试收件邮箱", value=email_user, key=f"test_email_{mode}")
            with test_col2:
                test_idx = st.selectbox(
                    "测试内容",
                    range(len(df)),
                    format_func=lambda x: f"{df.iloc[x].get(cols['contact_person'], 'N/A')}",
                    key=f"test_idx_{mode}"
                )
            
            if st.button("🧪 发送测试邮件", disabled=not (email_user and email_pass), key=f"test_send_{mode}"):
                test_row = df.iloc[test_idx]
                body_text = render_full_email(test_row, sender_name, sender_title, mode)
                body_html = EMAIL_BODY_HTML_TEMPLATE.format(
                    creator_name=extract_english_name(test_row.get(cols['contact_person'], 'Creator')),
                    sender_name=sender_name,
                    sender_title=sender_title,
                    project_title=test_row.get('AI_Project_Title', '[Project Title]'),
                    technical_detail=test_row.get('AI_Technical_Detail', '[Technical Detail]')
                )
                
                # 通过 Gmail SMTP 发送测试邮件
                success, msg = send_email(test_email, f"[TEST] {EMAIL_SUBJECT}", body_text, body_html, email_user, email_pass, sender_name, mode)
                
                if success:
                    st.success(f"✅ 测试邮件已发送到 {test_email}")
                else:
                    st.error(f"❌ 发送失败: {msg}")
            
            # 正式发送
            st.markdown("---")
            st.markdown("#### 📤 正式发送")
            
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            # 检查是否可以发送 (Gmail SMTP)
            can_send = email_user and email_pass and pending_count > 0
            
            with col_btn1:
                send_selected = st.button("📤 发送选中的邮件", type="primary", disabled=not can_send, key=f"send_{mode}")
            with col_btn2:
                if st.button("🔄 重置状态", key=f"reset_{mode}"):
                    df['Send_Status'] = '⏳ 待发送'
                    save_progress(df, mode)
                    st.rerun()
            with col_btn3:
                st.download_button("📥 导出数据", df.to_csv(index=False), file_name=f"kol_final_{mode.lower()}.csv", key=f"export_{mode}")
            
            if send_selected:
                to_send = df[(df['Selected'] == True) & (df['Send_Status'] == '⏳ 待发送')]
                
                if len(to_send) > 0:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    logs = []
                    
                    for i, (idx, row) in enumerate(to_send.iterrows()):
                        target_email = row.get('Email')
                        
                        body_text = render_full_email(row, sender_name, sender_title, mode)
                        body_html = EMAIL_BODY_HTML_TEMPLATE.format(
                            creator_name=extract_english_name(row.get(cols['contact_person'], 'Creator')),
                            sender_name=sender_name,
                            sender_title=sender_title,
                            project_title=row.get('AI_Project_Title', '[Project Title]'),
                            technical_detail=row.get('AI_Technical_Detail', '[Technical Detail]')
                        )
                        
                        # 通过 Gmail SMTP 发送
                        success, msg = send_email(target_email, EMAIL_SUBJECT, body_text, body_html, email_user, email_pass, sender_name, mode)
                        
                        if success:
                            df.loc[idx, 'Send_Status'] = '✅ 已发送'
                            logs.append(f"✅ [{i+1}/{len(to_send)}] {row.get(cols['contact_person'])} → {target_email}")
                        else:
                            df.loc[idx, 'Send_Status'] = f'❌ 失败'
                            logs.append(f"❌ [{i+1}/{len(to_send)}] {row.get(cols['contact_person'])}: {msg}")
                        
                        save_progress(df, mode)
                        progress_bar.progress((i + 1) / len(to_send))
                        status_text.text(logs[-1])
                        
                        if i < len(to_send) - 1:
                            delay = random.uniform(delay_min, delay_max)
                            time.sleep(delay)
                    
                    st.session_state[state_key] = df
                    st.success(f"✅ 已完成 {len(to_send)} 封邮件发送")
                    
                    with st.expander("📋 发送日志"):
                        st.code('\n'.join(logs))

# 渲染 B2B 和 B2C 标签页
with tab_b2b:
    render_mode_ui("B2B")

with tab_b2c:
    render_mode_ui("B2C")

# 页脚说明
st.divider()
st.markdown("""
### 📋 使用说明

**B2B 企业客户** (Excel 列: 客户名称, 决策人, 联系方式, 核心特征, 破冰话术要点)
- 附件: Utopai Early Access - Creator FAQ - V2.pdf, One-pager-enterprise.pdf

**B2C 创作者** (Excel 列: Name, Contact, Specialty, Ice Breaker)
- 附件: Utopai Early Access - Creator FAQ - V2.pdf, One-pager_final.pdf
- 如果 Unnamed:10 列有预生成的英文内容，将自动解析使用
""")
