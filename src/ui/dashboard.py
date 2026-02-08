import streamlit as st
from datetime import datetime
import pytz

def render_tracking_dashboard(tracking_url):
    """渲染邮件追踪仪表盘 - 区分确认阅读和可能预加载"""
    st.header("📊 邮件追踪仪表盘")
    
    if not tracking_url:
        st.warning("⚠️ 请在侧边栏填入追踪服务 URL 后使用此功能")
        return

    st.info(f"追踪服务: {tracking_url}")
    
    col_refresh, col_url = st.columns([1, 3])
    with col_refresh:
        refresh = st.button("🔄 刷新数据", key="refresh_tracking")
    with col_url:
        st.markdown(f"[📈 查看原始数据]({tracking_url}/api/stats?format=friendly)")
    
    if refresh or 'tracking_data' not in st.session_state:
        try:
            import requests
            response = requests.get(f"{tracking_url}/api/stats?format=friendly", timeout=10)
            if response.status_code == 200:
                st.session_state.tracking_data = response.json()
            else:
                st.error(f"获取追踪数据失败: HTTP {response.status_code}")
                st.session_state.tracking_data = None
        except Exception as e:
            st.error(f"无法连接追踪服务: {e}")
            st.session_state.tracking_data = None
    
    data = st.session_state.get('tracking_data')
    
    if data:
        # 主要指标
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("👥 收件人数", data.get('total_contacts', 0))
        with col2:
            st.metric("✅ 确认阅读", data.get('confirmed_reads', 0), 
                     help="有真实打开 + 点击过链接的收件人")
        with col3:
            st.metric("⚠️ 可能预加载", data.get('possible_preloads', 0),
                     help="有打开记录但未点击，可能是邮件客户端自动加载")
        with col4:
            st.metric("📈 确认阅读率", data.get('confirmed_rate', '0%'))
        
        st.divider()
        
        # 详细指标
        with st.expander("📊 详细统计", expanded=False):
            col5, col6, col7, col8 = st.columns(4)
            with col5:
                st.metric("👁️ 总打开次数", data.get('total_opens', 0))
            with col6:
                st.metric("🧑 真人打开", data.get('human_opens', 0),
                         help="非 Bot 的打开次数")
            with col7:
                st.metric("🤖 Bot 打开", data.get('bot_opens', 0),
                         help="被识别为 Bot/预加载的打开次数")
            with col8:
                st.metric("🔗 总点击次数", data.get('total_clicks', 0))
        
        st.divider()
        
        recipients = data.get('recipients', [])
        if recipients:
            # 三栏分类显示
            confirmed = [r for r in recipients if r.get('confirmed_read')]
            preload = [r for r in recipients if r.get('possible_preload')]
            not_opened = [r for r in recipients if not r.get('opened')]
            
            tab1, tab2, tab3 = st.tabs([
                f"✅ 确认阅读 ({len(confirmed)})",
                f"⚠️ 可能预加载 ({len(preload)})",
                f"❌ 未打开 ({len(not_opened)})"
            ])
            
            with tab1:
                if confirmed:
                    for r in confirmed:
                        _render_recipient_card(r, show_bot_info=True)
                else:
                    st.info("暂无确认阅读的收件人")
            
            with tab2:
                if preload:
                    st.caption("💡 这些收件人有打开记录，但没有点击任何链接。可能是邮件客户端自动预加载，也可能是用户只是浏览了一下。")
                    for r in preload:
                        _render_recipient_card(r, show_bot_info=True)
                else:
                    st.success("没有疑似预加载的记录")
            
            with tab3:
                if not_opened:
                    for r in not_opened:
                        st.markdown(f"**{r.get('name', 'Unknown')}**")
                        st.caption(f"{r.get('email', 'unknown')}")
                else:
                    st.success("所有邮件都有打开记录！")
        else:
            st.info("📭 暂无追踪数据。发送邮件后，收件人打开/点击将自动记录。")
    else:
        st.info("点击「刷新数据」获取追踪统计")


def _render_recipient_card(r, show_bot_info=False):
    """渲染单个收件人卡片"""
    email = r.get('email', 'unknown')
    name = r.get('name', 'Unknown')
    human_opens = r.get('human_opens', 0)
    bot_opens = r.get('bot_opens', 0)
    total_clicks = r.get('total_clicks', 0)
    bot_types = r.get('bot_types', [])
    
    # 最后活动时间
    last_activity = r.get('last_activity', '')
    if last_activity:
        try:
            dt = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
            local_tz = pytz.timezone('Asia/Shanghai')
            dt_local = dt.astimezone(local_tz)
            last_activity = dt_local.strftime('%m-%d %H:%M')
        except Exception:
            last_activity = last_activity[:16]
    
    # 显示卡片
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**{name}**")
        st.caption(f"{email}")
    with col2:
        if total_clicks > 0:
            st.markdown("🔗 已点击")
    
    # 详细信息
    info_parts = [f"🧑 {human_opens}次真人打开", f"🔗 {total_clicks}次点击"]
    if show_bot_info and bot_opens > 0:
        info_parts.append(f"🤖 {bot_opens}次Bot打开")
    info_parts.append(f"最后活动: {last_activity}")
    st.caption(" | ".join(info_parts))
    
    # Bot 类型
    if show_bot_info and bot_types:
        st.caption(f"🤖 检测到的 Bot 类型: {', '.join(bot_types)}")
    
    st.markdown("---")
