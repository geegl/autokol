import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 资源目录
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
LEADS_DIR = os.path.join(ASSETS_DIR, "leads_form")
ATTACHMENTS_DIR = os.path.join(ASSETS_DIR, "attachments")

# 输出目录
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# --- B2B/B2C 配置 ---
MODE_CONFIG = {
    "B2B": {
        "name": "B2B 企业客户",
        "progress_file": os.path.join(OUTPUT_DIR, "autokol_progress_b2b.csv"),
        "attachments": [
            "Utopai Early Access - Creator FAQ - V2.pdf",
            "One-pager-enterprise.pdf"
        ],
        "columns": {
            "client_name": "客户名称",
            "contact_person": "决策人",
            "contact_info": "联系方式",
            "features": "核心特征",
            "pain_point": "破冰话术要点"
        },
        "has_pregenerated_content": False
    },
    "B2C": {
        "name": "B2C 创作者",
        "progress_file": os.path.join(OUTPUT_DIR, "autokol_progress_b2c.csv"),
        "attachments": [
            "Utopai Early Access - Creator FAQ - V2.pdf",
            "One-pager_final.pdf"
        ],
        "columns": {
            "client_name": "Name",
            "contact_person": "Name",
            "contact_info": "Contact",
            "features": "Specialty",
            "pain_point": "Ice Breaker",
            "pregenerated": "Unnamed: 10"  # 已有的英文内容
        },
        "has_pregenerated_content": True
    }
}
