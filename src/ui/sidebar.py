import streamlit as st

def render_sidebar():
    """渲染侧边栏配置"""
    config = {}
    with st.sidebar:
        st.header("⚙️ 配置中心")
        
        st.subheader("1. LLM 设置 (硅基流动)")
        config['api_key'] = st.text_input("硅基流动 API Key", type="password", key="sidebar_api_key", help="在 https://cloud.siliconflow.cn 获取")
        config['base_url'] = st.text_input("Base URL", value="https://api.siliconflow.cn/v1", key="sidebar_base_url")
        config['model_name'] = st.text_input("Model Name", value="deepseek-ai/DeepSeek-V3.2", key="sidebar_model_name")
        
        st.subheader("2. 邮箱设置 (Gmail)")
        st.caption("使用 Google Workspace / Gmail SMTP")
        config['email_provider'] = "Gmail" # 强制 Gmail
        
        config['email_user'] = st.text_input("发件人邮箱地址", help="例如: growth@utopaistudios.com", key="sidebar_email_user")
        config['email_pass'] = st.text_input("应用专用密码", type="password", help="在 Google 账户 → 安全性 → 两步验证 → 应用专用密码 中生成", key="sidebar_email_pass")
        
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
