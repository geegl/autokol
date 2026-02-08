import streamlit as st
import importlib
from datetime import datetime
import pytz

def render_tracking_dashboard(tracking_url):
    """渲染邮件追踪仪表盘"""
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
        # 统计摘要
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📧 已追踪邮件", data.get('total_tracked', 0))
        with col2:
            st.metric("👁️ 已打开", data.get('opened_count', 0))
        with col3:
            st.metric("🔗 已点击", data.get('clicked_count', 0))
        with col4:
            total = data.get('total_tracked', 0)
            opened = data.get('opened_count', 0)
            open_rate = f"{(opened/total*100):.1f}%" if total > 0 else "0%"
            st.metric("📈 打开率", open_rate)
        
        st.divider()
        
        recipients = data.get('recipients', [])
        if recipients:
            # 分类显示
            opened_list = [r for r in recipients if r.get('opened')]
            not_opened_list = [r for r in recipients if not r.get('opened')]
            
            col_opened, col_not_opened = st.columns(2)
            
            with col_opened:
                st.subheader(f"✅ 已打开 ({len(opened_list)})")
                if opened_list:
                    for r in opened_list:
                        email = r.get('recipient_email', 'unknown').replace('-at-', '@').replace('-', '.')
                        name = r.get('recipient_name', 'unknown')
                        clicked = "🔗" if r.get('clicked') else ""
                        
                        first_open = r.get('first_open', '')
                        if first_open:
                            try:
                                dt = datetime.fromisoformat(first_open.replace('Z', '+00:00'))
                                london_tz = pytz.timezone('Europe/London')
                                dt_london = dt.astimezone(london_tz)
                                first_open = dt_london.strftime('%Y-%m-%d %H:%M') + " (LDN)"
                            except Exception:
                                first_open = first_open[:16]
                        
                        st.markdown(f"**{name}** {clicked}")
                        st.caption(f"{email} | 首次打开: {first_open}")
                else:
                    st.info("暂无打开记录")
            
            with col_not_opened:
                st.subheader(f"❌ 未打开 ({len(not_opened_list)})")
                if not_opened_list:
                    for r in not_opened_list:
                        email = r.get('recipient_email', 'unknown').replace('-at-', '@').replace('-', '.')
                        name = r.get('recipient_name', 'unknown')
                        st.markdown(f"**{name}**")
                        st.caption(f"{email}")
                else:
                    st.success("所有邮件都已打开！")
        else:
            st.info("📭 暂无追踪数据。发送邮件后，收件人打开/点击将自动记录。")
    else:
        st.info("点击「刷新数据」获取追踪统计")
