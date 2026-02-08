import streamlit as st
from datetime import datetime
import pytz

def render_tracking_dashboard(tracking_url):
    """渲染邮件追踪仪表盘 - 按收件人聚合显示"""
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
        # 统计摘要 - 适配新格式
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("👥 收件人数", data.get('total_contacts', 0))
        with col2:
            st.metric("👁️ 已打开", data.get('opened_count', 0))
        with col3:
            st.metric("🔗 已点击", data.get('clicked_count', 0))
        with col4:
            st.metric("📈 打开率", data.get('open_rate', '0%'))
        
        # 详细指标
        col5, col6 = st.columns(2)
        with col5:
            st.metric("👁️ 总打开次数", data.get('total_opens', 0), help="所有收件人打开邮件的总次数（包含重复打开）")
        with col6:
            st.metric("🔗 总点击次数", data.get('total_clicks', 0), help="所有收件人点击链接的总次数")
        
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
                        email = r.get('email', 'unknown')
                        name = r.get('name', 'Unknown')
                        total_opens = r.get('total_opens', 0)
                        total_clicks = r.get('total_clicks', 0)
                        clicked_icon = "🔗" if r.get('clicked') else ""
                        
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
                        st.markdown(f"**{name}** {clicked_icon}")
                        st.caption(f"{email}")
                        st.caption(f"👁️ {total_opens}次打开 | 🔗 {total_clicks}次点击 | 最后活动: {last_activity}")
                        st.markdown("---")
                else:
                    st.info("暂无打开记录")
            
            with col_not_opened:
                st.subheader(f"❌ 未打开 ({len(not_opened_list)})")
                if not_opened_list:
                    for r in not_opened_list:
                        email = r.get('email', 'unknown')
                        name = r.get('name', 'Unknown')
                        st.markdown(f"**{name}**")
                        st.caption(f"{email}")
                else:
                    st.success("所有邮件都已打开！")
        else:
            st.info("📭 暂无追踪数据。发送邮件后，收件人打开/点击将自动记录。")
    else:
        st.info("点击「刷新数据」获取追踪统计")
