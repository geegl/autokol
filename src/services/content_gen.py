import re
import pandas as pd
from src.services.llm import generate_with_llm

def clean_title(s):
    if not s: return ""
    s = s.strip().strip('"\'')
    s = re.sub(r'^PROJECT_TITLE:\s*', '', s, flags=re.IGNORECASE)
    s = re.sub(r'^Loved your work on\s*', '', s, flags=re.IGNORECASE)
    return s.strip().strip('"\'')

def clean_detail(s):
    if not s: return ""
    s = s.strip().strip('"\'')
    s = re.sub(r'^TECHNICAL_DETAIL:\s*', '', s, flags=re.IGNORECASE)
    s = re.sub(r'^particularly the\s*', '', s, flags=re.IGNORECASE)
    # 去除开头的冠词 (A/An/The)
    s = re.sub(r'^(A|An|The)\s+', '', s, flags=re.IGNORECASE)
    s = s.strip().strip('"\'')
    # 首字母小写（跟在 "particularly the" 后面更自然）
    if s and s[0].isupper():
        s = s[0].lower() + s[1:]
    return s

def generate_content_for_row(row, config, client, model):
    """为单行数据生成 Project Title 和 Technical Detail"""
    cols = config["columns"]
    client_name = row.get(cols["client_name"], '')
    features = row.get(cols["features"], '')
    pain_point = row.get(cols["pain_point"], '')
    
    # 策略 1: B2C 模式如果有预生成内容
    if config.get("has_pregenerated_content") and "pregenerated" in cols:
        pregenerated = row.get(cols["pregenerated"], '')
        
        if pd.notna(pregenerated) and str(pregenerated).strip():
            text = str(pregenerated).strip()
            
            # 类型1: 已有好的英文格式 
            match = re.search(r"Loved your work on (.+?) [–-] particularly the (.+?)\.?$", text)
            if match:
                project_title = clean_title(match.group(1))
                technical_detail = clean_detail(match.group(2))
                return project_title, technical_detail, '✅ 已有英文'
            
            # 检测是否有中文字符
            has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))
            
            # 检测是否是通用模板
            generic_patterns = ['interested in collaborating', 'film studio', 'looking forward']
            is_generic = any(p in text.lower() for p in generic_patterns)
            
            # 类型2: 中文翻译
            if has_chinese:
                prompt = f"""You are a native English copywriter. Based on this Chinese text about a content creator, generate TWO things:

Chinese text: {text}
Creator: {client_name}
Specialty: {features}

Generate:
1. PROJECT_TITLE: A short phrase (2-6 words) describing their work/content type
2. TECHNICAL_DETAIL: A specific compliment (5-12 words) about their style/quality

IMPORTANT: Do NOT include "Loved your work on" or "particularly the" - just the content itself.

Output format (exactly like this):
PROJECT_TITLE: [your answer]
TECHNICAL_DETAIL: [your answer]"""
                
                result = generate_with_llm(prompt, client, model)
                title_match = re.search(r'PROJECT_TITLE:\s*(.+)', result)
                detail_match = re.search(r'TECHNICAL_DETAIL:\s*(.+)', result)
                
                if title_match and detail_match:
                    return clean_title(title_match.group(1)), clean_detail(detail_match.group(1)), '🌐 中文翻译'
                else:
                    return clean_title(client_name) if client_name else "your recent content", "creative visual style", '🌐 中文翻译 (Fallback)'

            # 类型3: 通用英文定制化
            elif is_generic:
                prompt = f"""You are a native English copywriter. Based on this creator's info, generate TWO things:

Creator: {client_name}
Specialty: {features}
Content focus: {pain_point}

Generate:
1. PROJECT_TITLE: A short phrase explaining their content type
2. TECHNICAL_DETAIL: A specific compliment about their unique style

Output format:
PROJECT_TITLE: ...
TECHNICAL_DETAIL: ..."""
                
                result = generate_with_llm(prompt, client, model)
                title_match = re.search(r'PROJECT_TITLE:\s*(.+)', result)
                detail_match = re.search(r'TECHNICAL_DETAIL:\s*(.+)', result)
                
                if title_match and detail_match:
                    return clean_title(title_match.group(1)), clean_detail(detail_match.group(1)), '🔧 定制化'
                else:
                    return clean_title(features) if features else "your recent content", "unique creative vision", '🔧 定制化 (Fallback)'

    # 策略 4: 默认生成 (B2B 或 B2C 无预设内容)
    prompt = f"""You are a native English copywriter. Based on this creator's info, generate TWO things:

Creator/Client: {client_name}
Core Features/Specialty: {features}
Key Points: {pain_point}

Generate:
1. PROJECT_TITLE: A short phrase (2-6 words) describing their specific work
   Example: "AI Cinematic Short Films" or "visual effects tutorials"
   
2. TECHNICAL_DETAIL: A specific compliment (5-12 words) about their unique style/quality
   Example: "the cinematic depth you achieve with AI synthesis"

IMPORTANT: Do NOT include "Loved your work on" or "particularly the".

Output format:
PROJECT_TITLE: [your answer]
TECHNICAL_DETAIL: [your answer]"""

    result = generate_with_llm(prompt, client, model)
    title_match = re.search(r'PROJECT_TITLE:\s*(.+)', result)
    detail_match = re.search(r'TECHNICAL_DETAIL:\s*(.+)', result)
    
    if title_match and detail_match:
        return clean_title(title_match.group(1)), clean_detail(detail_match.group(1)), '✨ AI 生成'
    else:
        return clean_title(features) if features else "your project", "professional execution", '✨ AI 生成 (Fallback)'
