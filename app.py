import os
import streamlit as st
from src.ui.sidebar import render_sidebar
from src.ui.dashboard import render_tracking_dashboard
from src.ui.mode_handler import render_mode_ui
from src.ui.history_tab import render_send_history
from src.ui.onboarding import render_onboarding, check_config_status

# --- 页面配置 ---
st.set_page_config(page_title="Utopai Cold Email Engine", layout="wide")

# --- 登录保护 (APP_PASSWORD) ---
APP_PASSWORD = None
try:
    APP_PASSWORD = st.secrets.get("APP_PASSWORD")
except Exception:
    pass
if not APP_PASSWORD:
    APP_PASSWORD = os.environ.get("APP_PASSWORD")
if APP_PASSWORD:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.title("🔒 Utopai Cold Email Engine")
        pwd = st.text_input("访问密码", type="password")
        if st.button("登录"):
            if pwd == APP_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("密码错误")
        st.stop()

st.title("🚀 Utopai Cold Email Engine")
st.caption("Gmail/Resend + 硅基流动 DeepSeek-V3.2 | 自动保存进度")

# --- 渲染侧边栏 ---
sidebar_config = render_sidebar()

# 检查配置状态（用于引导流程）
check_config_status(sidebar_config)

# --- Sentry 错误监控 (从 Secrets 或 环境变量 读取) ---
sentry_dsn = None
try:
    if "SENTRY_DSN" in st.secrets:
        sentry_dsn = st.secrets["SENTRY_DSN"]
except Exception:
    pass

if not sentry_dsn:
    sentry_dsn = os.environ.get("SENTRY_DSN")

if sentry_dsn:
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=sentry_dsn,
            send_default_pii=True,  # 收集用户信息 (IP, 请求头等)
            traces_sample_rate=1.0,  # 100% 性能追踪
            profile_session_sample_rate=1.0,  # 100% 性能分析
        )
    except Exception as e:
        print(f"Sentry init failed: {e}")

# --- 首次使用引导 ---
if render_onboarding():
    st.stop()  # 阻止主界面渲染，直到完成引导

# --- 主界面 ---
# 使用 Tabs 分隔功能
tab_b2b, tab_b2c, tab_tracking, tab_history = st.tabs([
    "🏢 B2B 企业模式", 
    "🎨 B2C 创作者模式", 
    "📊 追踪仪表盘",
    "📨 发送记录"
])

# --- B2B 模式 ---
with tab_b2b:
    render_mode_ui("B2B", sidebar_config)

# --- B2C 模式 ---
with tab_b2c:
    render_mode_ui("B2C", sidebar_config)

# --- 追踪仪表盘 ---
with tab_tracking:
    render_tracking_dashboard(sidebar_config.get('tracking_url'))

# --- 发送记录 ---
with tab_history:
    render_send_history()

# 页脚说明
st.divider()
st.markdown("""
### 📋 使用说明

**B2B 企业客户** (Excel 列: 客户名称, 决策人, 联系方式, 核心特征, 破冰话术要点)
- 附件: Utopai Early Access - Creator FAQ - V2.pdf, One-pager-enterprise.pdf

**B2C 创作者** (Excel 列: Name, Contact, Specialty, Ice Breaker)
- 附件: Utopai Early Access - Creator FAQ - V2.pdf, One-pager_final.pdf
- 如果 Unnamed:10 列有预生成的英文内容，将自动解析使用

**追踪仪表盘** - 查看邮件打开率和点击率 (按收件人聚合)

**发送记录** - 查看今日和历史发送记录
""")
