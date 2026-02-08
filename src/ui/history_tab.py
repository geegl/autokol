"""
发送历史标签页 UI
"""
import streamlit as st
from datetime import datetime
import pytz
from src.services.send_history import get_today_stats, get_recent_records, load_send_history

def render_send_history():
    """渲染发送历史标签页"""
    st.header("📨 发送记录")
    
    # 今日统计
    today_stats = get_today_stats()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📧 今日发送", today_stats['today_total'])
    with col2:
        st.metric("✅ 成功", today_stats['today_success'])
    with col3:
        st.metric("❌ 失败", today_stats['today_failed'])
    
    st.divider()
    
    # 最近发送记录
    st.subheader("📋 最近发送记录")
    
    records = get_recent_records(50)
    
    if not records:
        st.info("暂无发送记录。发送邮件后，记录将自动显示在这里。")
        return
    
    # 搜索过滤
    search = st.text_input("🔍 搜索收件人", placeholder="输入邮箱或名称搜索...")
    
    if search:
        records = [r for r in records if search.lower() in r.get('recipient_email', '').lower() 
                   or search.lower() in r.get('recipient_name', '').lower()]
    
    # 显示记录
    for record in records:
        timestamp = record.get('timestamp', '')
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                local_tz = pytz.timezone('Asia/Shanghai')
                dt_local = dt.astimezone(local_tz)
                time_str = dt_local.strftime('%m-%d %H:%M')
            except:
                time_str = timestamp[:16]
        else:
            time_str = "未知时间"
        
        status = record.get('status', 'unknown')
        status_icon = "✅" if status == 'success' else "❌"
        
        recipient_email = record.get('recipient_email', 'unknown')
        recipient_name = record.get('recipient_name', 'Unknown')
        mode = record.get('mode', 'N/A')
        error_type = record.get('error_type', '')
        
        # 显示卡片
        col_status, col_info = st.columns([1, 5])
        with col_status:
            st.markdown(f"### {status_icon}")
        with col_info:
            st.markdown(f"**{recipient_name}** ({recipient_email})")
            caption_parts = [f"🕐 {time_str}", f"📁 {mode}"]
            if error_type:
                caption_parts.append(f"⚠️ {error_type}")
            st.caption(" | ".join(caption_parts))
        
        st.markdown("---")
    
    # 统计信息
    all_history = load_send_history()
    st.caption(f"共 {len(all_history)} 条历史记录")
