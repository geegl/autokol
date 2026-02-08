import streamlit as st
import pandas as pd
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

from src.config import MODE_CONFIG, LEADS_DIR
from src.utils.helpers import load_progress, save_progress, clear_progress, extract_email, extract_english_name
from src.utils.templates import EMAIL_SUBJECT, EMAIL_BODY_TEMPLATE, EMAIL_BODY_HTML_TEMPLATE
from src.services.tracking import generate_email_id, generate_tracking_pixel, generate_tracked_link, TRACKING_BASE_URL
from src.services.email_sender import send_email_gmail
from src.services.content_gen import generate_content_for_row

def render_mode_ui(mode, sidebar_config):
    """渲染主要模式 UI (B2B 或 B2C)"""
    config = MODE_CONFIG[mode]
    st.header(f"💼 {config['name']} 模式")
    
    # 检查 LLM 配置
    if not sidebar_config.get('api_key'):
        st.warning("⚠️ 请先在侧边栏配置 硅基流动 API Key")
        return
        
    client = OpenAI(api_key=sidebar_config['api_key'], base_url=sidebar_config['base_url'])
    
    # --- 1. 数据加载 (本地文件 or 上传) ---
    df = None
    
    # 扫描 assets/leads_form 目录
    local_files = [f for f in os.listdir(LEADS_DIR) if f.endswith(('.xlsx', '.xls', '.csv'))] if os.path.exists(LEADS_DIR) else []
    
    col_upload, col_local = st.columns(2)
    selected_file = None
    
    with col_local:
        if local_files:
            selected_local = st.selectbox(f"从 {LEADS_DIR} 选择文件", ["-- 使用上传文件 --"] + local_files, key=f"local_select_{mode}")
            if selected_local != "-- 使用上传文件 --":
                selected_file = os.path.join(LEADS_DIR, selected_local)
        else:
            st.caption(f"提示: 将文件放入 {LEADS_DIR} 可直接加载")

    with col_upload:
        uploaded_file = st.file_uploader(f"或者上传文件", type=["xlsx", "xls", "csv"], key=f"uploader_{mode}")
    
    # 确定数据源
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
        except Exception as e:
            st.error(f"读取上传文件失败: {e}")
            return
    elif selected_file:
        try:
            st.info(f"正在加载: {selected_file}")
            if selected_file.endswith('.csv'):
                df = pd.read_csv(selected_file)
            else:
                df = pd.read_excel(selected_file)
        except Exception as e:
            st.error(f"读取本地文件失败: {e}")
            return

    if df is not None:
        # 检查必要列
        required_cols = list(config["columns"].values())
        missing_cols = [col for col in required_cols if col not in df.columns and col != "Unnamed: 10"]
        
        if missing_cols:
            st.error(f"❌ 缺少必要列: {', '.join(missing_cols)}")
            st.info(f"请确保 Excel 包含以下列名: {', '.join(required_cols)}")
            return
        
        # --- 2. 进度管理 ---
        # 尝试加载 output 目录下的进度文件
        progress_df = load_progress(mode)
        
        if progress_df is not None:
            if len(progress_df) == len(df):
                st.info(f"📂 检测到上次未完成的进度 ({len(progress_df)} 行)，已自动加载。")
                df = progress_df
            else:
                st.warning(f"⚠️ 检测到旧进度文件 ({len(progress_df)} 行)，但与当前文件 ({len(df)} 行) 不匹配，已忽略并重新开始。")
                # 初始化新列
                if 'AI_Project_Title' not in df.columns:
                    df['AI_Project_Title'] = ""
                if 'AI_Technical_Detail' not in df.columns:
                    df['AI_Technical_Detail'] = ""
                if 'Email_Status' not in df.columns:
                    df['Email_Status'] = "待生成"
                if 'Content_Source' not in df.columns:
                    df['Content_Source'] = ""
        else:
            # 初始化新列
            if 'AI_Project_Title' not in df.columns:
                df['AI_Project_Title'] = ""
            if 'AI_Technical_Detail' not in df.columns:
                df['AI_Technical_Detail'] = ""
            if 'Email_Status' not in df.columns:
                df['Email_Status'] = "待生成"
            if 'Content_Source' not in df.columns:
                df['Content_Source'] = ""
        
        # --- 3. 数据预览与编辑 ---
        st.subheader("🛠️ 客户数据预览")
        
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            key=f"editor_{mode}",
            column_config={
                "Email_Status": st.column_config.SelectboxColumn(
                    "状态",
                    options=["待生成", "已生成", "发送成功", "发送失败", "邮箱无效"],
                    required=True
                )
            }
        )
        
        # 同步编辑结果
        if not edited_df.equals(df):
            save_progress(edited_df, mode)
            df = edited_df

        # --- 4. 批量生成内容 ---
        col_gen, col_clear = st.columns([1, 4])
        with col_gen:
            if st.button("✨ 批量生成内容", key=f"btn_gen_{mode}", type="primary"):
                rows_to_generate = df[
                    (df['AI_Project_Title'] == "") | 
                    (df['AI_Technical_Detail'] == "")
                ].index.tolist()
                
                if not rows_to_generate:
                    st.success("所有行都已生成内容！")
                else:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for i, idx in enumerate(rows_to_generate):
                        row = df.loc[idx]
                        status_text.text(f"正在生成第 {idx+1} 行...")
                        
                        # 调用服务生成内容
                        p_title, t_detail, source = generate_content_for_row(row, config, client, sidebar_config['model_name'])
                        
                        df.loc[idx, 'AI_Project_Title'] = p_title
                        df.loc[idx, 'AI_Technical_Detail'] = t_detail
                        df.loc[idx, 'Content_Source'] = source
                        df.loc[idx, 'Email_Status'] = "已生成"
                        
                        # 实时保存
                        save_progress(df, mode)
                        progress_bar.progress((i + 1) / len(rows_to_generate))
                    
                    status_text.text("✅ 生成完成！")
                    st.rerun()

        with col_clear:
            if st.button("🗑️ 清空进度", key=f"btn_clear_{mode}"):
                clear_progress(mode)
                st.rerun()

        st.divider()

        # --- 5. 邮件预览与发送 ---
        st.subheader("📧 邮件发送中心 (Gmail SMTP)")
        
        col_idx, col_preview = st.columns([1, 2])
        
        with col_idx:
            # 只选择已生成内容的行
            ready_indices = df[df['AI_Project_Title'] != ""].index.tolist()
            if not ready_indices:
                st.warning("请先生成内容")
                return
            
            selected_index = st.selectbox("选择预览行", ready_indices, format_func=lambda x: f"Row {x+1}: {df.loc[x, config['columns']['client_name']]}")
            
            # 获取当前行数据
            current_row = df.loc[selected_index]
            
            # 显示关键字段
            st.write("**AI 生成内容预览:**")
            st.text_input("Project Title", value=current_row['AI_Project_Title'], key=f"title_{selected_index}", disabled=True)
            st.text_area("Technical Detail", value=current_row['AI_Technical_Detail'], key=f"detail_{selected_index}", disabled=True)
        
        with col_preview:
            # 实时渲染邮件预览
            client_name_val = current_row.get(config['columns']['client_name'], '')
            contact_info_val = current_row.get(config['columns']['contact_info'], '')
            recipient_email = extract_email(contact_info_val)
            english_name = extract_english_name(client_name_val)
            
            # 预览时使用假 ID，且不触发真实追踪
            preview_email_id = f"preview_{mode}_{selected_index}"
            
            # 预览时不使用真实追踪 URL (传入 None)，防止触发真实的打开记录
            tracking_pixel = generate_tracking_pixel(preview_email_id, None)  # 返回空字符串
            tracked_calendly = "https://calendly.com/cecilia-utopaistudios/30min"  # 预览时用原始链接
            
            email_body_preview = EMAIL_BODY_TEMPLATE.format(
                creator_name=english_name,
                sender_name=sidebar_config['sender_name'],
                project_title=current_row['AI_Project_Title'],
                technical_detail=current_row['AI_Technical_Detail'],
                sender_title=sidebar_config['sender_title']
            )
            
            email_html_preview = EMAIL_BODY_HTML_TEMPLATE.format(
                creator_name=english_name,
                sender_name=sidebar_config['sender_name'],
                project_title=current_row['AI_Project_Title'],
                technical_detail=current_row['AI_Technical_Detail'],
                sender_title=sidebar_config['sender_title'],
                calendly_link=tracked_calendly,
                tracking_pixel=tracking_pixel if sidebar_config.get('tracking_url') else "<!-- Tracking Pixel Placeholder -->"
            )
            
            tab_text, tab_html = st.tabs(["纯文本预览", "HTML 预览"])
            with tab_text:
                st.text_area("邮件正文", value=email_body_preview, height=400)
            with tab_html:
                st.components.v1.html(email_html_preview, height=400, scrolling=True)

        # --- 发送按钮 ---
        st.divider()
        col_test, col_batch = st.columns(2)
        
        with col_test:
            test_email = st.text_input("测试收件人邮箱", placeholder="your_email@example.com", key=f"test_email_{mode}")
            if st.button("🧪 发送测试邮件", key=f"btn_test_{mode}"):
                if not test_email:
                    st.error("请输入测试邮箱")
                else:
                    if not sidebar_config.get('email_user') or not sidebar_config.get('email_pass'):
                        st.error("请先在左侧配置 Gmail 账号和应用专用密码")
                    else:
                        with st.spinner("正在发送测试邮件..."):
                            # 测试邮件使用真实的追踪 ID
                            test_id = generate_email_id(mode, selected_index, test_email, f"Test_{english_name}")
                            
                            # 生成用于发送的内容
                            final_pixel = generate_tracking_pixel(test_id, sidebar_config.get('tracking_url'))
                            final_link = generate_tracked_link(test_id, "https://calendly.com/cecilia-utopaistudios/30min", sidebar_config.get('tracking_url'))
                            
                            final_html = EMAIL_BODY_HTML_TEMPLATE.format(
                                creator_name=english_name,
                                sender_name=sidebar_config['sender_name'],
                                project_title=current_row['AI_Project_Title'],
                                technical_detail=current_row['AI_Technical_Detail'],
                                sender_title=sidebar_config['sender_title'],
                                calendly_link=final_link,
                                tracking_pixel=final_pixel
                            )
                            
                            success, msg = send_email_gmail(
                                test_email, EMAIL_SUBJECT, email_body_preview, final_html,
                                sidebar_config['email_user'], sidebar_config['email_pass'],
                                sidebar_config['sender_name'], mode, config['attachments']
                            )
                            
                            if success:
                                st.success(f"测试邮件已发送！{msg}")
                            else:
                                st.error(f"发送失败: {msg}")

        with col_batch:
            # 筛选出待发送的行
            pending_indices = df[
                (df['AI_Project_Title'] != "") & 
                (df['Email_Status'] != "发送成功")
            ].index.tolist()
            
            st.write(f"待发送邮件数: **{len(pending_indices)}**")
            
            if st.button("🚀 批量发送所有待发送邮件", key=f"btn_batch_{mode}", type="primary", disabled=len(pending_indices)==0):
                if not sidebar_config.get('email_user') or not sidebar_config.get('email_pass'):
                    st.error("请先配置 Gmail 发件人信息")
                    st.stop()
                
                progress_bar = st.progress(0)
                status_area = st.empty()
                success_count = 0
                fail_count = 0
                
                for i, idx in enumerate(pending_indices):
                    row = df.loc[idx]
                    dest_email = extract_email(row.get(config['columns']['contact_info']))
                    dest_name = extract_english_name(row.get(config['columns']['client_name']))
                    
                    if not dest_email:
                        status_area.warning(f"跳过第 {idx+1} 行: 无法提取邮箱")
                        df.loc[idx, 'Email_Status'] = "邮箱无效"
                        save_progress(df, mode)
                        continue
                    
                    status_area.text(f"正在发送给 {dest_name} ({dest_email})...")
                    
                    # 生成真实追踪 ID 和 内容
                    real_id = generate_email_id(mode, idx, dest_email, dest_name)
                    real_pixel = generate_tracking_pixel(real_id, sidebar_config.get('tracking_url'))
                    real_link = generate_tracked_link(real_id, "https://calendly.com/cecilia-utopaistudios/30min", sidebar_config.get('tracking_url'))
                    
                    body_txt = EMAIL_BODY_TEMPLATE.format(
                        creator_name=dest_name,
                        sender_name=sidebar_config['sender_name'],
                        project_title=row['AI_Project_Title'],
                        technical_detail=row['AI_Technical_Detail'],
                        sender_title=sidebar_config['sender_title']
                    )
                    
                    body_html = EMAIL_BODY_HTML_TEMPLATE.format(
                        creator_name=dest_name,
                        sender_name=sidebar_config['sender_name'],
                        project_title=row['AI_Project_Title'],
                        technical_detail=row['AI_Technical_Detail'],
                        sender_title=sidebar_config['sender_title'],
                        calendly_link=real_link,
                        tracking_pixel=real_pixel
                    )
                    
                    # 发送 (Only Gmail supported now)
                    ok, msg = send_email_gmail(
                        dest_email, EMAIL_SUBJECT, body_txt, body_html,
                        sidebar_config['email_user'], sidebar_config['email_pass'],
                        sidebar_config['sender_name'], mode, config['attachments']
                    )
                    
                    if ok:
                        df.loc[idx, 'Email_Status'] = "发送成功"
                        success_count += 1
                    else:
                        df.loc[idx, 'Email_Status'] = f"发送失败: {msg}"
                        fail_count += 1
                    
                    save_progress(df, mode) # Saved to output/
                    progress_bar.progress((i + 1) / len(pending_indices))
                    time.sleep(1) # 避免速率限制
                
                status_area.success(f"批量发送完成！成功: {success_count}, 失败: {fail_count}")
                st.rerun()

