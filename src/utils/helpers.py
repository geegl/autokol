import pandas as pd
import re
import os
import streamlit as st
from src.config import MODE_CONFIG

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

def save_progress(df, mode):
    """保存进度到本地 CSV"""
    try:
        progress_file = MODE_CONFIG[mode]["progress_file"]
        df.to_csv(progress_file, index=False, encoding='utf-8-sig')
    except Exception as e:
        st.warning(f"保存进度失败: {e}")

def load_progress(mode):
    """加载上次保存的进度"""
    progress_file = MODE_CONFIG[mode]["progress_file"]
    if os.path.exists(progress_file):
        try:
            return pd.read_csv(progress_file, encoding='utf-8-sig')
        except:
            return None
    return None

def clear_progress(mode):
    """清除进度文件"""
    progress_file = MODE_CONFIG[mode]["progress_file"]
    if os.path.exists(progress_file):
        os.remove(progress_file)
