import pandas as pd
import re
import os
import requests
import streamlit as st
from src.config import MODE_CONFIG
from src.services.tracking import TRACKING_BASE_URL

def extract_email(contact_str):
    """从联系方式字符串中提取邮箱地址"""
    if pd.isna(contact_str):
        return None
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    matches = re.findall(email_pattern, str(contact_str))
    return matches[0] if matches else None

def extract_english_name(name_str):
    """从姓名字符串中提取英文名（去除中文和括号内容）"""
    if pd.isna(name_str):
        return "there"
    name = str(name_str)
    # 去除 @ 符号
    name = name.replace('@', '')
    # 去除括号及其内容
    name = re.sub(r'[（(][^）)]*[）)]', '', name)
    # 去除中文字符
    name = re.sub(r'[\u4e00-\u9fff]+', '', name)
    # 清理多余空格
    name = ' '.join(name.split()).strip()
    return name if name else "there"


import tempfile
import shutil

# ===== 进度持久化（云端 + 本地双重保存）=====

def save_progress(df, mode, force_cloud=False):
    """保存进度（原子写入 + 云端备份）"""
    progress_file = MODE_CONFIG[mode]["progress_file"]
    
    # 1. 原子写入本地（先写临时文件，再重命名）
    try:
        # 获取目标目录
        target_dir = os.path.dirname(progress_file)
        
        # 创建临时文件（在同一目录下，确保 rename 是原子操作）
        fd, temp_path = tempfile.mkstemp(suffix='.csv', dir=target_dir)
        try:
            # 写入临时文件
            df.to_csv(temp_path, index=False, encoding='utf-8-sig')
            os.close(fd)
            
            # 原子重命名（如果中途失败，原文件不受影响）
            shutil.move(temp_path, progress_file)
        except Exception as e:
            # 清理临时文件
            os.close(fd) if fd else None
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e
    except Exception as e:
        if mode != "B2C": # Optional: suppress for B2C if needed, but better keep it
             st.warning(f"本地保存失败: {e}")

    # 2. 云端保存（异步/限流）
    # 只有当 force_cloud=True 或 距离上次同步超过 30 秒时才同步
    import time
    last_sync_key = f'last_sync_{mode}'
    last_sync_time = st.session_state.get(last_sync_key, 0)
    current_time = time.time()
    
    if force_cloud or (current_time - last_sync_time > 30):
        try:
            success = _save_to_cloud(df, mode)
            if success:
                st.session_state[last_sync_key] = current_time
            elif force_cloud:
                st.warning("⚠️ 云端备份失败 (这不会影响当前操作，但可能无法跨设备恢复)")
        except Exception as e:
            # 云端保存失败不影响主流程，但在强制保存时提醒
            if force_cloud:
                st.warning(f"⚠️ 云端备份异常: {e}")

def _get_progress_api_key():
    """获取 Progress API Key"""
    try:
        if "PROGRESS_API_KEY" in st.secrets:
            return st.secrets["PROGRESS_API_KEY"]
    except:
        pass
    return os.environ.get("PROGRESS_API_KEY", "")

def _save_to_cloud(df, mode):
    """保存到云端 Redis（静默失败改为日志警告）"""
    try:
        api_key = _get_progress_api_key()
        api_url = f"{TRACKING_BASE_URL}/api/progress?mode={mode}&key={api_key}"
        data = df.to_dict(orient='records')
        
        # V2.9.13 Fix: Increase timeout for large payloads
        response = requests.post(api_url, json={"data": data}, timeout=15)
        if response.status_code == 200:
            return True
        else:
            # st.toast(f"Cloud Save Failed: {response.status_code}") # Optional debug
            return False
            
    except Exception as e:
        # st.toast(f"Cloud Save Error: {e}") # Optional debug
        return False

def load_progress(mode):
    """加载进度（优先本地，回退云端）"""
    # 1. 尝试本地加载
    progress_file = MODE_CONFIG[mode]["progress_file"]
    if os.path.exists(progress_file):
        try:
            return pd.read_csv(progress_file, encoding='utf-8-sig')
        except Exception as e:
            st.error(f"⚠️ 本地进度加载失败 ({progress_file}): {e}")
            # Do not swallow exception silently, show it to user
            pass
    
    # 2. 本地没有，尝试云端加载
    cloud_df = _load_from_cloud(mode)
    if cloud_df is not None:
        # 同时保存到本地
        try:
            cloud_df.to_csv(progress_file, index=False, encoding='utf-8-sig')
        except:
            pass
        return cloud_df
    
    return None

def _load_from_cloud(mode):
    """从云端 Redis 加载进度"""
    try:
        api_key = _get_progress_api_key()
        api_url = f"{TRACKING_BASE_URL}/api/progress?mode={mode}&key={api_key}"
        # V2.9.13 Fix: Increase timeout
        response = requests.get(api_url, timeout=15)
        if response.status_code == 200:
            result = response.json()
            if result.get('success') and result.get('data') and result['data'].get('data'):
                records = result['data']['data']
                if records:
                    return pd.DataFrame(records)
    except Exception as e:
        # st.warning(f"云端加载失败: {e}")
        pass
    return None

def clear_progress(mode):
    """清除进度（本地 + 云端）"""
    # 1. 清除本地
    progress_file = MODE_CONFIG[mode]["progress_file"]
    if os.path.exists(progress_file):
        try:
            os.remove(progress_file)
        except: pass
    
    # 2. 清除云端
    try:
        api_key = _get_progress_api_key()
        api_url = f"{TRACKING_BASE_URL}/api/progress?mode={mode}&key={api_key}"
        # V2.9.13 Fix: Increase timeout
        requests.delete(api_url, timeout=10)
    except:
        pass  # 静默失败

def sync_progress_to_cloud(mode):
    """手动同步本地进度到云端"""
    progress_file = MODE_CONFIG[mode]["progress_file"]
    if os.path.exists(progress_file):
        try:
            df = pd.read_csv(progress_file, encoding='utf-8-sig')
            success = _save_to_cloud(df, mode)
            if success:
                st.success("☁️ 云端同步成功！")
                return True
            else:
                st.error("云端同步失败 (API Error)")
                return False
        except Exception as e:
            st.error(f"同步失败: {e}")
            return False
    return False
