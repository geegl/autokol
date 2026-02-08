import os

# 保存文件路径
SAVE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- B2B/B2C 配置 ---
MODE_CONFIG = {
    "B2B": {
        "name": "B2B 企业客户",
        "progress_file": os.path.join(SAVE_DIR, "autokol_progress_b2b.csv"),
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
        "progress_file": os.path.join(SAVE_DIR, "autokol_progress_b2c.csv"),
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
