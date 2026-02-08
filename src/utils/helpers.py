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

def save_progress(df, mode):
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
        st.warning(f"本地保存失败: {e}")
    
    # 2. 云端保存（异步，不阻塞）
    try:
        _save_to_cloud(df, mode)
    except Exception as e:
        # 云端保存失败不影响主流程
        pass

def _save_to_cloud(df, mode):
    """保存到云端 Redis（静默失败）"""
    try:
        api_url = f"{TRACKING_BASE_URL}/api/progress?mode={mode}"
        data = df.to_dict(orient='records')
        requests.post(api_url, json={"data": data}, timeout=5)
    except:
        pass  # 静默失败

def load_progress(mode):
    """加载进度（优先本地，回退云端）"""
    # 1. 尝试本地加载
    progress_file = MODE_CONFIG[mode]["progress_file"]
    if os.path.exists(progress_file):
        try:
            return pd.read_csv(progress_file, encoding='utf-8-sig')
        except:
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
        api_url = f"{TRACKING_BASE_URL}/api/progress?mode={mode}"
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('success') and result.get('data') and result['data'].get('data'):
                records = result['data']['data']
                if records:
                    return pd.DataFrame(records)
    except Exception as e:
        st.warning(f"云端加载失败: {e}")
    return None

def clear_progress(mode):
    """清除进度（本地 + 云端）"""
    # 1. 清除本地
    progress_file = MODE_CONFIG[mode]["progress_file"]
    if os.path.exists(progress_file):
        os.remove(progress_file)
    
    # 2. 清除云端
    try:
        api_url = f"{TRACKING_BASE_URL}/api/progress?mode={mode}"
        requests.delete(api_url, timeout=5)
    except:
        pass  # 静默失败

def sync_progress_to_cloud(mode):
    """手动同步本地进度到云端"""
    progress_file = MODE_CONFIG[mode]["progress_file"]
    if os.path.exists(progress_file):
        try:
            df = pd.read_csv(progress_file, encoding='utf-8-sig')
            _save_to_cloud(df, mode)
            return True
        except Exception as e:
            st.error(f"同步失败: {e}")
            return False
    return False
