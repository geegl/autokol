import os
import streamlit as st


def _get_env(key, default=""):
    """Read from st.secrets first, then os.environ, then default."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, default)


def render_sidebar():
    """渲染侧边栏配置"""
    config = {}
    with st.sidebar:
        st.header("⚙️ 配置中心")

        st.subheader("1. LLM 设置 (硅基流动)")
        config['api_key'] = st.text_input(
            "硅基流动 API Key", type="password", key="sidebar_api_key",
            value=_get_env("SILICONFLOW_API_KEY"),
            help="在 https://cloud.siliconflow.cn 获取"
        )
        config['base_url'] = st.text_input(
            "Base URL",
            value=_get_env("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
            key="sidebar_base_url"
        )
        config['model_name'] = st.text_input(
            "Model Name",
            value=_get_env("SILICONFLOW_MODEL", "deepseek-ai/DeepSeek-V3.2"),
            key="sidebar_model_name"
        )

        st.subheader("2. 邮箱设置 (Email Service)")
        # V2.15: Dual Provider Support
        default_provider = "SendGrid (API)" if _get_env("SENDGRID_API_KEY") else "Gmail (SMTP)"
        provider = st.selectbox(
            "选择邮件服务商",
            ["Gmail (SMTP)", "SendGrid (API)"],
            index=0 if default_provider == "Gmail (SMTP)" else 1,
            help="Gmail: 适合个人低频发送 (每日 < 500)\nSendGrid: 适合大规模群发 (稳定防封)",
            key="sidebar_email_provider_select"
        )
        config['email_provider'] = "SendGrid" if "SendGrid" in provider else "Gmail"

        if config['email_provider'] == "Gmail":
            st.caption("使用 Google Workspace / Gmail SMTP")
            config['email_user'] = st.text_input(
                "发件人邮箱地址",
                value=_get_env("GMAIL_USER"),
                help="例如: growth@utopaistudios.com", key="sidebar_email_user"
            )
            config['email_pass'] = st.text_input(
                "应用专用密码", type="password",
                value=_get_env("GMAIL_APP_PASSWORD"),
                help="在 Google 账户 → 安全性 → 两步验证 → 应用专用密码 中生成", key="sidebar_email_pass"
            )
        else:
            st.caption("使用 SendGrid API (推荐大规模发送)")
            config['sendgrid_api_key'] = st.text_input(
                "SendGrid API Key", type="password",
                value=_get_env("SENDGRID_API_KEY"),
                help="Starts with SG...", key="sidebar_sendgrid_key"
            )
            config['sendgrid_sender'] = st.text_input(
                "已验证的发件人身份 (Verified Sender)",
                value=_get_env("SENDGRID_SENDER"),
                help="必须与 SendGrid 后台验证的 Sender Identity 一致", key="sidebar_sendgrid_sender"
            )
        
        st.subheader("3. 发件人信息")
        config['sender_name'] = st.text_input("Your Name", value="Cecilia", key="sidebar_sender_name")
        config['sender_title'] = st.text_input("Your Title", value="Director of Creative Partnerships", key="sidebar_sender_title")
        
        st.subheader("4. 邮件追踪 (可选)")
        tracking_url = st.text_input("追踪服务 URL (Vercel)", value="https://autokol.vercel.app", help="部署在 Vercel 的追踪服务地址", key="sidebar_tracking_url")
        if tracking_url and tracking_url.endswith('/'):
            tracking_url = tracking_url[:-1]
        config['tracking_url'] = tracking_url
        
        if tracking_url:
            st.success("✅ 追踪已启用 - 将自动记录打开率和点击率")
        else:
            st.info("💡 部署 email-tracker 到 Vercel 后可启用追踪")
        
        st.divider()
        
    return config
