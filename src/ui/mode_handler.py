import streamlit as st
import pandas as pd
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from streamlit_quill import st_quill
import re

from src.config import MODE_CONFIG, LEADS_DIR
from src.utils.helpers import load_progress, save_progress, clear_progress, extract_email, extract_english_name
from src.utils.templates import get_email_subjects, EMAIL_BODY_TEMPLATE, EMAIL_BODY_HTML_TEMPLATE
from src.utils.template_manager import load_user_templates, save_user_template, delete_user_template
from src.services.tracking import generate_email_id, generate_tracking_pixel, generate_tracked_link, TRACKING_BASE_URL
from src.services.email_sender import send_email_gmail
from src.services.content_gen import generate_content_for_row
from src.services.send_history import save_send_record, get_today_stats

DEFAULT_CALENDLY_LINK = "https://calendly.com/cecilia-utopaistudios/30min"


def strip_html_tags(text):
    """Remove html tags from a string"""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


class _SafeFormatDict(dict):
    """Keep unknown template placeholders as-is instead of raising KeyError."""
    def __missing__(self, key):
        return "{" + key + "}"


def format_template_html(template_html, **kwargs):
    """Safely format user template and avoid hard failure on missing placeholders."""
    try:
        return template_html.format_map(_SafeFormatDict(kwargs))
    except Exception as e:
        return f"<p style='color:red'>Template Error: {e}</p>"


def get_preview_row_label(df, row_index, preferred_col):
    """Build a resilient preview label even if mapped column is missing."""
    row = df.loc[row_index]
    value = row.get(preferred_col, "") if preferred_col in df.columns else ""
    text = str(value).strip()

    if not text or text.lower() == "nan":
        for item in row.tolist():
            item_text = str(item).strip()
            if item_text and item_text.lower() != "nan":
                text = item_text
                break

    if not text:
        text = "(无可用名称)"

    return f"Row {row_index+1}: {text}"


def wrap_html_content(html_content, calendly_link="", tracking_pixel=""):
    """Wrap HTML fragment in a full email structure without escaping"""
    
    # Replace calendly link if needed (V2.10.4 Fix: Use Regex to replace safely inside href)
    if calendly_link:
        target_url = DEFAULT_CALENDLY_LINK
        
        # 1. Replace inside href attributes (e.g. from Quill)
        pattern = r'(href=["\'])' + re.escape(target_url) + r'(["\'])'
        if re.search(pattern, html_content):
             html_content = re.sub(pattern, r'\1' + calendly_link + r'\2', html_content)
        
        # 2. Fallback: If URL is in plain text (not in href), replace it (but be careful not to double replace)
        # Note: In Rich Text mode, users should make links explicit. 
        # But if they just typed the URL, we might want to auto-link it? 
        # For safety, let's assume Quill handles linking or user does. 
        # We only fix the TRACKING link replacement.
            
    return f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
{html_content}
{tracking_pixel}
</body>
</html>'''

# Helper to convert plain text template to HTML fragment for Quill
def plain_to_quill_html(text):
    paragraphs = text.split('\n\n')
    html_parts = []
    for p in paragraphs:
        p = p.replace('\n', '<br>')
        html_parts.append(f'<p>{p}</p>')
    return '\n'.join(html_parts)

def text_to_html(text, calendly_link="", tracking_pixel=""):
    """将纯文本模板转换为 HTML 格式"""
    # 转义HTML特殊字符
    import html as html_lib
    text = html_lib.escape(text)
    
    # 将换行符转为 <br> 或 <p> 标签
    paragraphs = text.split('\n\n')
    html_parts = []
    for p in paragraphs:
        p = p.replace('\n', '<br>')
        html_parts.append(f'<p>{p}</p>')
    
    body_content = '\n'.join(html_parts)
    
    # 如果有 calendly 链接，替换为可点击链接
    if calendly_link:
        body_content = body_content.replace(
            DEFAULT_CALENDLY_LINK,
            f'<a href="{calendly_link}">Book a meeting</a>'
        )
    
    return f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
{body_content}
{tracking_pixel}
</body>
</html>'''

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
        # --- 2. 动态列映射 (V2.9 Refactor: Internal Keys) ---
        # 使用 items() 获取内部 key (client_name) 和 预期 Header (Name)
        required_cols_map = config["columns"]
        
        # 检查缺失 (检查 User Columns 中是否有 Expected Headers)
        # 注意：如果用户改了列名，这里会误报缺失，但下面的映射可以解决。
        # V2.9: 我们不再强制检查 df.columns 是否包含 required_cols.values()
        # 而是看是否有映射。
        
        if f'col_mapping_{mode}' not in st.session_state:
            st.session_state[f'col_mapping_{mode}'] = {}
            
        mapped_cols = st.session_state[f'col_mapping_{mode}']
        all_columns = df.columns.tolist()
        
        # --- V2.9.2 Validate Mappings (Fix: Stale columns from previous file) ---
        invalid_keys = []
        for k, v in list(mapped_cols.items()):
            if v not in all_columns:
                invalid_keys.append(k)
        
        if invalid_keys:
            st.toast(f"⚠️ 检测到源文件变更，已重置相关映射: {', '.join(invalid_keys)}")
            for k in invalid_keys:
                del mapped_cols[k]
            # 强制重置确认状态，迫使用户重新确认
            if f'col_mapping_confirmed_{mode}' in st.session_state:
                del st.session_state[f'col_mapping_confirmed_{mode}']
        
        # 检测是否有未映射的关键字段
        # 逻辑：对于每个 internal_key，如果 mapped_cols 里没有，且 df 里也没有默认的 expected_header
        missing_mapping = []
        for int_key, exp_header in required_cols_map.items():
            if int_key not in mapped_cols:
                if exp_header not in df.columns and exp_header != "Unnamed: 10":
                    missing_mapping.append(exp_header)
        
        # 默认展开条件：有未映射字段 或 尚未确认
        is_confirmed = st.session_state.get(f'col_mapping_confirmed_{mode}', False)
        should_expand = (len(missing_mapping) > 0) or (not is_confirmed)
        
        if len(missing_mapping) > 0:
            st.warning(f"⚠️ 检测到部分列名未匹配，请手动映射")

        # V2.9.10 UX: Refactor Mapping UI
        # 1. Add "Re-configure" button if confirmed, to allow re-expanding
        if is_confirmed:
            if st.button("🔄 重新配置列名映射", key=f"btn_reconfig_{mode}"):
                st.session_state[f'col_mapping_confirmed_{mode}'] = False
                st.rerun()

        # 2. Use updated labels and help text
        with st.expander("🔧 列名映射配置", expanded=should_expand):
            st.info("💡 请将左侧的【系统字段】与右侧您上传表格中的【实际列名】进行对应。")
            
            # Label Definitions
            label_map = {
                "client_name": "客户名称 (工作室/公司名/YouTube账号)",
                "contact_person": "决策人 (优先人名，无则用 '客户名称 + Team')",
                "contact_info": "联系方式 (邮箱)",
                "features": "核心特征 (自定义)",
                "pain_point": "破冰话术要点 (自定义)",
                "pregenerated": "已生成内容 (可选)"
            }

            for int_key, exp_header in required_cols_map.items():
                # 尝试自动匹配
                default_idx = 0
                
                # 1. 已有映射
                if int_key in mapped_cols and mapped_cols[int_key] in all_columns:
                    default_idx = all_columns.index(mapped_cols[int_key])
                # 2. 默认同名
                elif exp_header in all_columns:
                    default_idx = all_columns.index(exp_header)
                
                display_label = label_map.get(int_key, f"{exp_header} ({int_key})")
                
                selected_col = st.selectbox(
                    f"**{display_label}** 对应:", 
                    all_columns,
                    index=default_idx,
                    key=f"map_{mode}_{int_key}",
                    help=f"系统内部字段: {int_key}"
                )
                mapped_cols[int_key] = selected_col
            
            if st.button("✅ 确认映射并继续", key=f"btn_confirm_map_{mode}", type="primary"):
                st.session_state[f'col_mapping_confirmed_{mode}'] = True
                st.rerun()
            
            # Block execution if not confirmed
            if should_expand and not st.session_state.get(f'col_mapping_confirmed_{mode}'):
                st.stop()
        
        # 获取最终映射 (用于后续逻辑)
        # 如果未手动映射，则默认使用 config 中的预期列名
        final_mapping = mapped_cols.copy()
        for int_key, exp_header in required_cols_map.items():
            if int_key not in final_mapping:
                final_mapping[int_key] = exp_header
        
        # --- 数据预清洗 (V2.1 Fix: B2C NaN issue) ---
        #将所有NaN填充为空字符串，防止后续处理出现 "nan"
        df = df.fillna("")
        # 确保所有列都是字符串类型（除了可能的数字列，但在邮件生成上下文中全转为字符串更安全）
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).replace('nan', '')

        # --- 3. 附件选择 (V2.2 Fix: Dual Folder Scan) ---
        # 扫描 assets/attachments/{mode} 目录，如果为空则降级扫描 assets/attachments
        st.subheader("📎 附件管理")
        from src.config import ASSETS_DIR
        
        mode_attach_dir = os.path.join(ASSETS_DIR, "attachments", mode)
        root_attach_dir = os.path.join(ASSETS_DIR, "attachments")
        
        if not os.path.exists(mode_attach_dir):
            os.makedirs(mode_attach_dir, exist_ok=True)
            
        # 1. 尝试模式目录
        available_files = [f for f in os.listdir(mode_attach_dir) if not f.startswith('.')]
        attach_source = mode_attach_dir
        
        # 2. 回退到根目录
        if not available_files and os.path.exists(root_attach_dir):
            available_files = [f for f in os.listdir(root_attach_dir) if not f.startswith('.')]
            attach_source = root_attach_dir
            if available_files:
                st.caption(f"ℹ️ {mode} 专用附件目录为空，已加载通用附件。")

        # 默认选中配置中的附件 (如果存在)
        default_files = [os.path.basename(f) for f in config['attachments']]
        default_selection = [f for f in default_files if f in available_files]
        
        selected_attachments = st.multiselect(
            "选择本次发送的附件:",
            options=available_files,
            default=default_selection,
            key=f"attach_select_{mode}"
        )
        
        #构建完整路径
        final_attachments = [os.path.join(attach_source, f) for f in selected_attachments]
        if not final_attachments:
             st.warning("⚠️ 未选择任何附件，邮件将仅包含正文")
             
        # --- 4. 进度管理与确认 (V2.2 Logic: Resume/Restart) ---
        # 尝试加载 output 目录下的进度文件
        progress_df = load_progress(mode)
        is_continuing_progress = False

        # 初始化决策状态 (Resume or New)
        if f'decision_{mode}' not in st.session_state:
            st.session_state[f'decision_{mode}'] = None # 'continue' or 'restart'

        # 自动判断“历史进度是否来自同一份文件”
        # 规则：行数不一致，或基础列重叠过低 -> 判定为旧任务，默认走 restart。
        if (
            progress_df is not None
            and isinstance(progress_df, pd.DataFrame)
            and len(progress_df) > 0
            and st.session_state[f'decision_{mode}'] is None
        ):
            current_rows = len(df)
            progress_rows = len(progress_df)

            generated_cols = {
                "AI_Project_Title",
                "AI_Technical_Detail",
                "Email_Status",
                "Content_Source",
                "Full_Email",
                "Send_Status",
                "Selected"
            }
            current_cols = set(df.columns)
            progress_base_cols = set(progress_df.columns) - generated_cols

            overlap = len(current_cols & progress_base_cols)
            min_cols = max(1, min(len(current_cols), len(progress_base_cols)))
            overlap_ratio = overlap / min_cols

            if current_rows != progress_rows or overlap_ratio < 0.7:
                st.warning(
                    f"⚠️ 检测到历史进度与当前文件不一致（历史 {progress_rows} 行 / 当前 {current_rows} 行）。"
                    "已自动切换为“重新开始（使用当前上传文件）”。"
                )
                st.session_state[f'decision_{mode}'] = 'restart'
                st.session_state[f'leads_confirmed_{mode}'] = False
        
        # 如果检测到进度，且未做决定，显示选择界面
        if progress_df is not None and st.session_state[f'decision_{mode}'] is None:
            # 检查进度文件长度，如果是 0 则忽略
            if len(progress_df) > 0:
                st.divider()
                st.info(f"📂 系统检测到上次未完成的任务 ({len(progress_df)} 行)。")
                st.write("请选择操作：")
                col_resume, col_restart = st.columns(2)
                
                with col_resume:
                    if st.button("🔄 继续上次任务 (推荐)", type="primary", key=f"btn_resume_{mode}", use_container_width=True):
                        st.session_state[f'decision_{mode}'] = 'continue'
                        st.rerun()
                
                with col_restart:
                    if st.button("🆕 重新开始 (使用此时上传的文件)", key=f"btn_restart_{mode}", use_container_width=True):
                        st.session_state[f'decision_{mode}'] = 'restart'
                        st.rerun()
                
                st.stop() # 等待用户选择
            else:
                 # 空进度文件，直接视为 restart
                 st.session_state[f'decision_{mode}'] = 'restart'

        # 根据决策执行逻辑
        decision = st.session_state.get(f'decision_{mode}')
        
        if decision == 'continue':
            is_continuing_progress = True
            df = progress_df
            
            # V2.9.3 Fix: Defensive check for corrupted progress data
            if not isinstance(df, pd.DataFrame):
                st.error("⚠️ 进度文件已损坏 (Data Type Error)，正在重置...")
                clear_progress(mode)
                st.session_state[f'decision_{mode}'] = 'restart'
                st.rerun()
                
            df = df.fillna("")
            if not st.session_state.get(f'leads_confirmed_{mode}'):
                st.session_state[f'leads_confirmed_{mode}'] = True # 继续任务默认已确认
        elif decision == 'restart':
            is_continuing_progress = False
            # 清除旧进度文件 (可选，如果不清空，下次还会提示，但这里先保留文件，仅在内存中使用新数据)
            pass
        
        # 如果不是继续旧进度，则需要用户确认 (V2.1 UX)
        if not is_continuing_progress:
            if not st.session_state.get(f'leads_confirmed_{mode}'):
                st.divider()
                st.subheader("📋 Leads 数据确认")
                
                total_leads = len(df)
                # 计算有效邮箱 (使用映射后的列名)
                contact_col = final_mapping.get('contact_info', config['columns']['contact_info'])
                valid_emails = 0
                if contact_col in df.columns:
                     # 简单检查是否包含 @
                     valid_emails = df[contact_col].astype(str).apply(lambda x: 1 if '@' in x else 0).sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("总行数", total_leads)
                c2.metric("有效邮箱 (预估)", valid_emails)
                c3.metric("待处理", total_leads)
                
                if st.button("✅ 确认并开始处理", type="primary", key=f"btn_confirm_leads_{mode}"):
                    st.session_state[f'leads_confirmed_{mode}'] = True
                    # 如果选择了重新开始，这里可以考虑清除旧进度文件，或者在 save_progress 时覆盖
                    if st.session_state.get(f'decision_{mode}') == 'restart':
                         clear_progress(mode) # 自定义清除函数，或者是 save_progress 覆盖
                    st.rerun()
                
                st.info("💡 请确认数据无误后点击上方按钮开始处理。")
                if progress_df is not None and st.session_state.get(f'decision_{mode}') == 'restart':
                     st.warning("⚠️ 注意：你选择了重新开始，确认后**旧的进度文件将被覆盖**。")
                
                st.stop() # 暂停执行，等待确认

        if is_continuing_progress:
             st.success(f"📂 已加载上次进度 ({len(df)} 行)，继续执行。")

        # 初始化新列 (确保列存在)
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
        
        # V2.9.6 Dynamic Key to force refresh after generation
        if f'gen_version_{mode}' not in st.session_state:
            st.session_state[f'gen_version_{mode}'] = 0
            
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            key=f"editor_{mode}_{st.session_state[f'gen_version_{mode}']}",
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
                    total_rows = len(rows_to_generate)
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    completed_count = 0
                    
                    # 线程工作函数
                    def process_row(idx):
                        try:
                            row = df.loc[idx]
                            p_title, t_detail, source = generate_content_for_row(row, config, client, sidebar_config['model_name'], mapped_cols=final_mapping)
                            return idx, p_title, t_detail, source, None
                        except Exception as e:
                            return idx, None, None, None, str(e)

                    # 并发执行 (最大 3 个线程，避免速率限制)
                    max_workers = 3
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        future_to_idx = {executor.submit(process_row, idx): idx for idx in rows_to_generate}
                        
                        for future in as_completed(future_to_idx):
                            original_idx = future_to_idx[future]
                            idx, p_title, t_detail, source, error = future.result()
                            
                            completed_count += 1
                            
                            if error:
                                st.warning(f"第 {idx+1} 行生成失败: {error}")
                            else:
                                # DEBUG: 检查生成内容是否为空
                                if not p_title or not t_detail:
                                    st.error(f"⚠️ Row {idx+1}: 生成内容为空! Source: {source}")
                                else:
                                    # Optional: Show success toast periodically
                                    if completed_count % 5 == 0:
                                        st.toast(f"✅ 已生成 {completed_count} 行: {p_title[:15]}...")
                                
                                df.loc[idx, 'AI_Project_Title'] = p_title
                                df.loc[idx, 'AI_Technical_Detail'] = t_detail
                                df.loc[idx, 'Content_Source'] = source
                                df.loc[idx, 'Email_Status'] = "已生成"
                                
                                # 实时保存
                                save_progress(df, mode)
                            
                            progress = completed_count / total_rows
                            progress_bar.progress(progress)
                            status_text.text(f"正在生成... ({completed_count}/{total_rows})")
                            
            # V2.9.7 UX: Add explicit warning that table will refresh at end
                            if completed_count == 1:
                                st.info("ℹ️ 注意：为了性能，表格内容将在任务全部完成后统一刷新。请关注上方绿色弹窗确认进度。")

                status_text.success(f"✅ 生成完成！共 {len(rows_to_generate)} 条")
                
                # Checkpoint: Force Cloud Sync to ensure data persists even on Cloud reboot!
                st.toast("☁️ 正在同步到云端数据库...")
                save_progress(df, mode, force_cloud=True)
                
                # Switch decision to 'continue' so next rerun loads the progress we just made!
                st.session_state[f'decision_{mode}'] = 'continue'
                
                # Increment version to force DataEditor refresh
                st.session_state[f'gen_version_{mode}'] += 1
                time.sleep(1)
                st.rerun()

        with col_clear:
            if st.button("🗑️ 清空进度", key=f"btn_clear_{mode}"):
                clear_progress(mode)
                st.rerun()

        st.divider()

        # --- 5. 邮件模板编辑器 ---
        st.subheader("✏️ 邮件模板编辑")
        
        # 初始化 session_state 用于存储模板
        if f'email_subject_final_{mode}' not in st.session_state:
            # 默认使用第一个选项
            subjects = get_email_subjects()
            if f'current_template_idx_{mode}_ver' not in st.session_state:
             st.session_state[f'current_template_idx_{mode}_ver'] = 0

        # Load Templates
        templates = load_user_templates()
        template_options = [t['name'] for t in templates]
        
        # Determine current selection index
        # Default to 0 (first template) if not set
        if f'selected_template_index_{mode}' not in st.session_state:
            st.session_state[f'selected_template_index_{mode}'] = 0
            
        def on_template_change(m):
            """Callback when template dropdown changes"""
            # Update session state with selected template content
            # Note: We need to read the index from widget key or value
            # But widget key is updated *after* callback? No, during callback the value is available via st.session_state[key]
            # Wait, st.selectbox stores VALUE (string name) in key
            selected_name = st.session_state[f"select_template_name_{m}"]
            # Find template
            t = next((x for x in load_user_templates() if x['name'] == selected_name), None)
            if t:
                # Update subject input
                st.session_state[f'email_subject_visual_{m}'] = t['subject']
                st.session_state[f'email_subject_final_{m}'] = t['subject']
                # Update body editor
                st.session_state[f'email_body_{m}'] = t['body']

        def reset_template_callback(m):
            """Callback to reset to Default Template (First one)"""
            defaults = load_user_templates()
            if defaults:
                first = defaults[0]
                # Reset internal session state
                st.session_state[f"email_subject_visual_{m}"] = first['subject']
                st.session_state[f'email_subject_final_{m}'] = first['subject']
                st.session_state[f'email_body_{m}'] = first['body']
                # Reset selectbox widget value (by key)
                st.session_state[f"select_template_name_{m}"] = first['name']


        # Initialize Body if empty
        if f'email_body_{mode}' not in st.session_state:
             if templates:
                 st.session_state[f'email_body_{mode}'] = templates[0]['body']
             else:
                 st.session_state[f'email_body_{mode}'] = plain_to_quill_html(EMAIL_BODY_TEMPLATE)

        # Initialize Subject Visual if empty
        if f'email_subject_visual_{mode}' not in st.session_state:
             if templates:
                 st.session_state[f'email_subject_visual_{mode}'] = templates[0]['subject']
             else:
                 st.session_state[f'email_subject_visual_{mode}'] = "Default Subject"


        with st.expander("📝 编辑邮件模板", expanded=False):
            st.caption("可用变量: `{creator_name}`, `{sender_name}`, `{project_title}`, `{technical_detail}`, `{sender_title}`, `{calendly_link}`")
            
            # --- V2.10 模板选择器 ---
            # 1. Template Selector
            col_templ, col_save_btn = st.columns([3, 1])
            with col_templ:
                selected_template = st.selectbox(
                    "选择模板 (Select Template)",
                    template_options,
                    index=st.session_state.get(f'selected_template_index_{mode}', 0),
                    key=f"select_template_name_{mode}",
                    on_change=on_template_change,
                    args=(mode,)
                )
                
            with col_save_btn:
                # "Save as New" Popover
                with st.popover("💾 另存为..."):
                    st.markdown("##### 保存为新模板")
                    new_tmpl_name = st.text_input("模板名称", placeholder="My New Template", key=f"new_tmpl_name_{mode}")
                    if st.button("确认保存", type="primary", key=f"btn_save_confirm_{mode}"):
                         if new_tmpl_name:
                             # Save current content
                             curr_subj = st.session_state.get(f'email_subject_visual_{mode}', "")
                             curr_body = st.session_state.get(f'email_body_{mode}', "")
                             
                             if save_user_template(new_tmpl_name, curr_subj, curr_body):
                                 st.toast(f"✅ 模板 '{new_tmpl_name}' 保存成功！")
                                 time.sleep(1)
                                 st.rerun()
                             else:
                                 st.error("保存失败")
                         else:
                             st.warning("请输入模板名称")

            # 2. Subject Input (Editable)
            # Use 'email_subject_visual_{mode}' as key/value source
            # But we need to sync it to 'email_subject_final_{mode}'
            
            # Note: We use unique key "input_subject_{mode}" for widget, and default value from session state
            # When widget changes, we update session state?
            # Better: use value=st.session_state[...] and ON_CHANGE to update
            
            def on_subject_change():
                st.session_state[f'email_subject_final_{mode}'] = st.session_state[f'input_subject_{mode}']
                st.session_state[f'email_subject_visual_{mode}'] = st.session_state[f'input_subject_{mode}']

            st.text_input(
                "邮件主题 (Subject)",
                value=st.session_state.get(f'email_subject_visual_{mode}', ""),
                key=f"input_subject_{mode}",
                on_change=on_subject_change
            )
            
            # Also ensure final state is synced if no change event fired yet (init)
            st.session_state[f'email_subject_final_{mode}'] = st.session_state.get(f'input_subject_{mode}', 
                                                                                   st.session_state.get(f'email_subject_visual_{mode}', ""))
            
            
            # 3. Editor Mode Selector (V2.11 New Feature)
            # Add toggle for Rich Text vs Clean Text (HTML Source)
            editor_mode = st.radio(
                "编辑模式 (Editor Mode)",
                options=["富文本 (Rich Text)", "源码模式 (HTML Source)"],
                horizontal=True,
                key=f"editor_mode_select_{mode}"
            )

            current_body_content = st.session_state.get(f'email_body_{mode}', "")

            if "富文本" in editor_mode:
                # Quill Editor
                st.caption("所见即所得编辑器 (What You See Is What You Get)")
                new_body = st_quill(
                    value=current_body_content,
                    placeholder="Edit your email template here...",
                    key=f"quill_body_{mode}",
                    html=True  # Ensure we get HTML back
                )
                if new_body != current_body_content:
                     st.session_state[f'email_body_{mode}'] = new_body

            else:
                # Raw HTML / Plain Text Editor
                st.caption("直接编辑 HTML 源码，适合修复格式问题")
                new_body_text = st.text_area(
                    "HTML 源码",
                    value=current_body_content,
                    height=300,
                    key=f"raw_html_body_{mode}"
                )
                if new_body_text != current_body_content:
                     st.session_state[f'email_body_{mode}'] = new_body_text

            
            # 4. Buttons (Only Reset needed, Save is above)
            st.divider()
            col_reset, col_info = st.columns([1, 3])
            with col_reset:
                st.button("🔄 重置 (Reset)", 
                          key=f"btn_reset_template_{mode}",
                          on_click=reset_template_callback,
                          args=(mode,)
                )
            with col_info:
                st.caption("💡 修改会即时生效。如需永久保存修改，请点击右上角的「💾 另存为...」按钮。")

        st.divider()

        # --- 6. 邮件预览与发送 ---
        st.subheader("📧 邮件发送中心 (Gmail SMTP)")
        
        col_idx, col_preview = st.columns([1, 2])
        
        with col_idx:
            # 只选择已生成内容的行
            ready_indices = df[df['AI_Project_Title'] != ""].index.tolist()
            if not ready_indices:
                st.warning("请先生成内容")
                return
            
            # 获取映射后的列名
            c_client = final_mapping.get('client_name', config['columns']['client_name'])
            selected_index = st.selectbox(
                "选择预览行",
                ready_indices,
                format_func=lambda x: get_preview_row_label(df, x, c_client)
            )
            
            # 获取当前行数据
            current_row = df.loc[selected_index]
            
            # 显示关键字段
            st.write("**AI 生成内容预览 (可编辑修正):**")
            
            # Project Title 编辑逻辑
            new_p_title = st.text_input("Project Title", value=current_row['AI_Project_Title'], key=f"title_{selected_index}")
            if new_p_title != current_row['AI_Project_Title']:
                df.loc[selected_index, 'AI_Project_Title'] = new_p_title
                save_progress(df, mode)
                st.rerun()
                
            # Technical Detail 编辑逻辑
            new_t_detail = st.text_area("Technical Detail", value=current_row['AI_Technical_Detail'], key=f"detail_{selected_index}")
            if new_t_detail != current_row['AI_Technical_Detail']:
                df.loc[selected_index, 'AI_Technical_Detail'] = new_t_detail
                save_progress(df, mode)
                st.rerun()
        
        with col_preview:
            # 实时渲染邮件预览
            # 获取映射后的列名
            c_client = final_mapping.get('client_name', config['columns']['client_name'])
            c_contact = final_mapping.get('contact_info', config['columns']['contact_info'])
            
            client_name_val = current_row.get(c_client, '')
            contact_info_val = current_row.get(c_contact, '')
            recipient_email = extract_email(contact_info_val)
            english_name = extract_english_name(client_name_val)
            
            # 预览时使用假 ID，且不触发真实追踪
            preview_email_id = f"preview_{mode}_{selected_index}"
            
            # 预览时不使用真实追踪 URL (传入 None)，防止触发真实的打开记录
            tracking_pixel = generate_tracking_pixel(preview_email_id, None)  # 返回空字符串
            tracked_calendly = DEFAULT_CALENDLY_LINK  # 预览时用原始链接
            
            # 预览内容清洗 (防止 nan)
            p_title = str(current_row.get('AI_Project_Title', ''))
            t_detail = str(current_row.get('AI_Technical_Detail', ''))
            if p_title.lower() == 'nan': p_title = ""
            if t_detail.lower() == 'nan': t_detail = ""

            # 使用用户编辑的模板 (HTML)
            user_template = st.session_state.get(f'email_body_{mode}', plain_to_quill_html(EMAIL_BODY_TEMPLATE))
            
            # Format the HTML template
            try:
                email_body_preview_html = format_template_html(
                    user_template,
                    creator_name=english_name,
                    sender_name=sidebar_config['sender_name'],
                    project_title=p_title,
                    technical_detail=t_detail,
                    sender_title=sidebar_config['sender_title'],
                    calendly_link=tracked_calendly,
                    tracking_pixel=""
                )
            except Exception as e:
                email_body_preview_html = f"<p style='color:red'>Template Error: {e}</p>"
            
            # Generate Plain Text version for Preview/Multipart
            email_body_preview_text = strip_html_tags(email_body_preview_html)
            
            # Create Final HTML (Wrapped)
            final_html = wrap_html_content(
                email_body_preview_html, 
                config.get('calendly_link', DEFAULT_CALENDLY_LINK),
                tracking_pixel if sidebar_config.get('tracking_url') else "<!-- Tracking Pixel Placeholder -->"
            )
            
            # 获取当前选择的主题
            current_subject = st.session_state.get(f'email_subject_final_{mode}', "Default Subject")
            
            # V2.4: 手动刷新按钮 (响应用户需求)
            if st.button("🔄 刷新预览 (Update Preview)", key=f"btn_refresh_preview_{mode}"):
                st.rerun()
            
            # 使用 st.info 显示主题 (无状态组件，确保实时刷新，避免 text_input 的缓存问题)
            st.info(f"**预览的主题 (Subject):**\n{current_subject}")
            
            st.caption("📧 预览:")
            st.markdown(f"**Subject:** {st.session_state.get(f'email_subject_final_{mode}', '')}")
            st.markdown("---")
            # Render HTML in Streamlit
            st.components.v1.html(final_html, height=400, scrolling=True)

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
                            final_link = generate_tracked_link(test_id, DEFAULT_CALENDLY_LINK, sidebar_config.get('tracking_url'))
                            
                            # Use the HTML template from session state
                            user_template_html = st.session_state.get(f'email_body_{mode}', plain_to_quill_html(EMAIL_BODY_TEMPLATE))
                            
                            # Format the HTML template
                            try:
                                formatted_body_html = format_template_html(
                                    user_template_html,
                                    creator_name=english_name,
                                    sender_name=sidebar_config['sender_name'],
                                    project_title=p_title,
                                    technical_detail=t_detail,
                                    sender_title=sidebar_config['sender_title'],
                                    calendly_link=final_link,
                                    tracking_pixel=final_pixel
                                )
                            except Exception as e:
                                formatted_body_html = f"<p style='color:red'>Template Error: {e}</p>"
                            
                            # Generate plain text version
                            formatted_body_text = strip_html_tags(formatted_body_html)

                            # Wrap in full HTML structure
                            final_html_to_send = wrap_html_content(
                                formatted_body_html,
                                calendly_link=final_link,
                                tracking_pixel=final_pixel
                            )
                            
                            # 使用用户编辑的主题
                            user_subject = st.session_state.get(f'email_subject_final_{mode}', "Subject Error")
                            
                            success, msg, error_type = send_email_gmail(
                                test_email, user_subject, formatted_body_text, final_html_to_send,
                                sidebar_config['email_user'], sidebar_config['email_pass'],
                                sidebar_config['sender_name'], mode, final_attachments
                            )
                            
                            # 保存发送记录
                            save_send_record(
                                recipient_email=test_email,
                                recipient_name=f"Test_{english_name}",
                                subject=user_subject,
                                status="success" if success else "failed",
                                error_type=error_type,
                                mode=mode
                            )
                            
                            if success:
                                st.success(f"测试邮件已发送！{msg}")
                            else:
                                st.error(f"发送失败: {msg}")

        with col_batch:
            # Gmail 限制预警
            today_stats = get_today_stats()
            today_sent = today_stats.get('today_success', 0)
            gmail_limit = 500  # Gmail 每日限制
            remaining = gmail_limit - today_sent
            
            # 显示今日发送统计
            col_sent, col_remain = st.columns(2)
            with col_sent:
                st.metric("📧 今日已发送", today_sent)
            with col_remain:
                if remaining <= 50:
                    st.metric("⚠️ 剩余额度", remaining, delta=None, delta_color="inverse")
                else:
                    st.metric("✅ 剩余额度", remaining)
            
            if remaining <= 0:
                st.error("🚫 今日 Gmail 发送额度已用完！请明天再试。")
            elif remaining <= 50:
                st.warning(f"⚠️ 今日剩余额度仅 {remaining} 封，请注意控制发送量！")
            
            # --- 发送速率控制 (V2.8 Smart Interval) ---
            use_smart_interval = st.checkbox(
                "🎲 启用智能随机间隔 (5-10秒)", 
                value=True,
                help="【推荐】模拟真实人工发送行为，每封邮件随机等待 5-10 秒，有效降低被 Gmail 判定为机器人的风险。",
                key=f"use_smart_interval_{mode}"
            )
            
            if not use_smart_interval:
                send_interval = st.slider(
                    "⏱️ 固定发送间隔 (秒)", 
                    min_value=2, 
                    max_value=30, 
                    value=5,
                    help="设置固定的等待时间。",
                    key=f"fixed_interval_{mode}"
                )
            else:
                send_interval = st.slider(
                    "⏱️ 随机间隔范围 (秒)", 
                    min_value=2, 
                    max_value=60, 
                    value=(5, 10),
                    help="设置随机等待的最小值和最大值。",
                    key=f"range_interval_{mode}"
                )
                st.info(f"✅ 智能模式已启用：每封邮件将随机等待 {send_interval[0]} 到 {send_interval[1]} 秒。")

            st.divider()
            
            # 筛选出待发送的行
            pending_indices = df[
                (df['AI_Project_Title'] != "") & 
                (df['Email_Status'] != "发送成功")
            ].index.tolist()
            
            # 筛选出发送失败的行
            failed_indices = df[
                df['Email_Status'].str.startswith("发送失败", na=False)
            ].index.tolist()
            
            st.write(f"待发送邮件数: **{len(pending_indices)}**")
            if failed_indices:
                st.write(f"发送失败待重试: **{len(failed_indices)}**")
            
            # 初始化发送状态
            if f'sending_{mode}' not in st.session_state:
                st.session_state[f'sending_{mode}'] = False
            if f'paused_{mode}' not in st.session_state:
                st.session_state[f'paused_{mode}'] = False
            
            # --- V2.5 发送状态提示 ---
            if not st.session_state.get(f'sending_{mode}', False):
                if len(pending_indices) > 0:
                    st.info(f"💡 队列中有 **{len(pending_indices)}** 封邮件等待发送。准备好后请点击下方「批量发送」。")
                elif failed_indices:
                    st.warning(f"⚠️ 发现 **{len(failed_indices)}** 封发送失败的邮件。请点击下方「重试失败」。")
            
            # 按钮区域
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            
            with btn_col1:
                send_disabled = len(pending_indices) == 0 or remaining <= 0 or st.session_state[f'sending_{mode}']
                if st.button("🚀 批量发送", key=f"btn_batch_{mode}", type="primary", disabled=send_disabled):
                    st.session_state[f'sending_{mode}'] = True
                    st.session_state[f'paused_{mode}'] = False
                    st.session_state[f'send_queue_{mode}'] = pending_indices.copy()
                    st.rerun()
            
            with btn_col2:
                retry_disabled = len(failed_indices) == 0 or remaining <= 0 or st.session_state[f'sending_{mode}']
                if st.button("🔄 重试失败", key=f"btn_retry_{mode}", disabled=retry_disabled):
                    st.session_state[f'sending_{mode}'] = True
                    st.session_state[f'paused_{mode}'] = False
                    st.session_state[f'send_queue_{mode}'] = failed_indices.copy()
                    st.rerun()
            
            with btn_col3:
                if st.session_state[f'sending_{mode}']:
                    if st.session_state[f'paused_{mode}']:
                        if st.button("▶️ 继续", key=f"btn_resume_{mode}"):
                            st.session_state[f'paused_{mode}'] = False
                            st.rerun()
                    else:
                        if st.button("⏸️ 暂停", key=f"btn_pause_{mode}"):
                            st.session_state[f'paused_{mode}'] = True
                            st.rerun()
            
            # 发送逻辑
            if st.session_state[f'sending_{mode}'] and not st.session_state[f'paused_{mode}']:
                if not sidebar_config.get('email_user') or not sidebar_config.get('email_pass'):
                    st.error("请先配置 Gmail 发件人信息")
                    st.session_state[f'sending_{mode}'] = False
                    st.stop()
                
                queue = st.session_state.get(f'send_queue_{mode}', [])
                if not queue:
                    st.session_state[f'sending_{mode}'] = False
                    st.success("✅ 所有邮件发送完成！")
                else:
                    # 取出下一个要发送的
                    idx = queue.pop(0)
                    st.session_state[f'send_queue_{mode}'] = queue
                    
                    row = df.loc[idx]
                    # 获取列名 (优先使用映射，否则使用默认)
                    c_contact = final_mapping.get('contact_info', config['columns']['contact_info'])
                    c_client = final_mapping.get('client_name', config['columns']['client_name'])
                    
                    dest_email = extract_email(row.get(c_contact))
                    dest_name = extract_english_name(row.get(c_client))
                    
                    if not dest_email:
                        st.warning(f"跳过第 {idx+1} 行: 无法提取邮箱")
                        df.loc[idx, 'Email_Status'] = "邮箱无效"
                        save_progress(df, mode)
                        time.sleep(0.5)
                        st.rerun()
                    
                    with st.spinner(f"正在发送给 {dest_name} ({dest_email})..."):
                        # 生成追踪内容
                        real_id = generate_email_id(mode, idx, dest_email, dest_name)
                        real_pixel = generate_tracking_pixel(real_id, sidebar_config.get('tracking_url'))
                        real_link = generate_tracked_link(real_id, DEFAULT_CALENDLY_LINK, sidebar_config.get('tracking_url'))
                        
                        # 使用用户编辑的模板 (HTML)
                        # Fallback to HTML converted default if not in session state
                        user_template_html = st.session_state.get(f'email_body_{mode}', plain_to_quill_html(EMAIL_BODY_TEMPLATE))
                        
                        try:
                            formatted_body_html = format_template_html(
                                user_template_html,
                                creator_name=dest_name,
                                sender_name=sidebar_config['sender_name'],
                                project_title=row['AI_Project_Title'],
                                technical_detail=row['AI_Technical_Detail'],
                                sender_title=sidebar_config['sender_title'],
                                calendly_link=real_link,
                                tracking_pixel=real_pixel
                            )
                        except Exception as e:
                            # Fallback if formatting fails
                            formatted_body_html = f"<p>Error formatting email: {e}</p>"
                        
                        # Generate plain text version by stripping tags
                        body_txt = strip_html_tags(formatted_body_html)
                        
                        # Generate Full HTML (Wrapped)
                        body_html = wrap_html_content(
                            formatted_body_html,
                            calendly_link=real_link,
                            tracking_pixel=real_pixel
                        )
                        
                        # 使用用户编辑的主题
                        # 使用用户编辑的主题
                        user_subject = st.session_state.get(f'email_subject_final_{mode}', "Subject Error")
                        
                        ok, msg, error_type = send_email_gmail(
                            dest_email, user_subject, body_txt, body_html,
                            sidebar_config['email_user'], sidebar_config['email_pass'],
                            sidebar_config['sender_name'], mode, final_attachments
                        )
                        
                        save_send_record(
                            recipient_email=dest_email,
                            recipient_name=dest_name,
                            subject=user_subject,
                            status="success" if ok else "failed",
                            error_type=error_type,
                            mode=mode
                        )
                        
                        if ok:
                            df.loc[idx, 'Email_Status'] = "发送成功"
                            st.success(f"✅ 发送成功: {dest_name}")
                        else:
                            df.loc[idx, 'Email_Status'] = f"发送失败: {msg}"
                            st.error(f"❌ 发送失败: {dest_name} - {msg}")
                        
                        save_progress(df, mode)
                    
                    # 更新剩余数量显示
                    remaining_count = len(st.session_state.get(f'send_queue_{mode}', []))
                    if remaining_count > 0:
                        st.info(f"📤 队列剩余: {remaining_count} 封")
                    
                    if use_smart_interval:
                        import random
                        # send_interval is a tuple (min, max)
                        wait_seconds = random.uniform(send_interval[0], send_interval[1])
                        st.caption(f"⏳ 智能随机等待: {wait_seconds:.1f} 秒...")
                        time.sleep(wait_seconds)
                    else:
                        time.sleep(send_interval)  # 使用用户设置的固定间隔
                    st.rerun()
            
            # 暂停状态提示
            if st.session_state[f'paused_{mode}']:
                remaining_count = len(st.session_state.get(f'send_queue_{mode}', []))
                st.warning(f"⏸️ 发送已暂停，队列剩余 {remaining_count} 封。点击「继续」恢复发送。")
