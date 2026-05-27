"""
首次使用引导流程
"""
import streamlit as st

def render_onboarding():
    """渲染首次使用引导"""
    
    # 检测是否已完成引导
    if st.session_state.get('onboarding_complete', False):
        return False  # 不显示引导
    
    st.markdown("## 🎉 欢迎使用 Utopai Cold Email Engine!")
    st.markdown("让我们花 1 分钟完成初始配置。")
    
    st.divider()
    
    # 步骤 1: LLM API
    st.markdown("### 步骤 1: 配置 AI 服务")
    st.markdown("""
    本工具使用 **硅基流动** 提供的 DeepSeek-V4-Pro 模型来生成邮件内容。
    
    1. 访问 [硅基流动控制台](https://cloud.siliconflow.cn/account/ak)
    2. 创建一个 API Key
    3. 复制 API Key 到左侧边栏
    """)
    
    api_key_set = st.session_state.get('temp_api_key_set', False)
    if api_key_set:
        st.success("✅ API Key 已配置")
    else:
        st.warning("⚠️ 等待配置 API Key...")
    
    st.divider()
    
    # 步骤 2: Gmail 配置
    st.markdown("### 步骤 2: 配置 Gmail 发送")
    st.markdown("""
    使用 Gmail SMTP 发送邮件需要:
    
    1. 访问 [Google 账号安全设置](https://myaccount.google.com/security)
    2. 启用**两步验证**
    3. 创建**应用专用密码**（选择"邮件"和"其他设备"）
    4. 将生成的 16 位密码填入左侧边栏
    """)
    
    gmail_set = st.session_state.get('temp_gmail_set', False)
    if gmail_set:
        st.success("✅ Gmail 已配置")
    else:
        st.info("💡 可以稍后配置，先体验内容生成功能")
    
    st.divider()
    
    # 步骤 3: 追踪服务
    st.markdown("### 步骤 3: 邮件追踪（可选）")
    st.markdown("""
    默认追踪服务已配置：`https://autokol.vercel.app`
    
    追踪功能包括：
    - 📧 邮件打开检测
    - 🔗 链接点击追踪
    - 📊 Dashboard 数据分析
    """)
    st.success("✅ 追踪服务已就绪")
    
    st.divider()
    
    # 完成引导
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ 完成设置，开始使用", type="primary", use_container_width=True):
            st.session_state['onboarding_complete'] = True
            st.rerun()
    with col2:
        if st.button("🔄 稍后再说", use_container_width=True):
            st.session_state['onboarding_complete'] = True
            st.rerun()
    
    return True  # 正在显示引导，阻止主界面渲染


def check_config_status(sidebar_config):
    """检查配置状态并更新临时标记"""
    if sidebar_config.get('api_key'):
        st.session_state['temp_api_key_set'] = True
    if sidebar_config.get('email_user') and sidebar_config.get('email_pass'):
        st.session_state['temp_gmail_set'] = True
