# 🔥 Utopai Cold Email Engine (V2.2)

专业的冷启动邮件发送引擎，专为 Utopai Studios 定制。集成 LLM 个性化生成、PDF 附件管理、Vercel 邮件追踪和 Gmail SMTP 发送服务。

## ✨ 核心特性

- **智能化生成**: 利用硅基流动 DeepSeek-V3.2 API 自动生成个性化的 "Project Title" 和 "Technical Detail"。
- **B2B/B2C 双模式**: 支持针对企业客户和创作者的不同话术策略与邮件主题。
- **动态数据映射 (V2.0)**: 上传任意格式 Excel/CSV，智能映射列名。
- **安全发送 (V2.0)**: 内置 Gmail SMTP 轮询，支持发送速率控制 (1-10s 间隔)，避免被封号。
- **任务恢复 (V2.2)**: 自动保存发送进度，支持 **断点续传** 或 **重新开始**。
- **附件管理 (V2.2)**: 自动扫描 `assets/attachments`，支持多选发送，具备智能回退机制。
- **可视化编辑 (V1.1)**: 所见即所得的邮件模板编辑器，支持变量实时预览。
- **数据追踪**: 集成 Vercel + Redis 追踪邮件打开率。

## 📂 目录结构

```text
autokol/
├── app.py                  # 启动入口
├── output/                 # ✅ [自动生成] 进度文件和结果保存位置
├── assets/                 # ✅ [手动管理] 资源文件夹
│   ├── leads_form/         # ➡️ 将客户 Excel/CSV 名单放入此处
│   └── attachments/        # ➡️ 存放 PDF 附件 (可按 B2B/B2C 子目录分类)
├── config/
│   └── email_settings.yaml # 📧 邮件主题、签名、模板配置文件
├── email-tracker/          # Vercel 追踪服务代码
├── src/                    # 源代码
└── requirements.txt
```

## 🚀 快速开始

### 1. 环境准备

```bash
git clone https://github.com/geegl/autokol.git
cd autokol
pip install -r requirements.txt
```

### 2. 配置说明

1.  **邮件配置**: 修改 `config/email_settings.yaml` 设置邮件主题和签名。
2.  **客户名单**: 将 Excel/CSV 文件放入 `assets/leads_form/`。
3.  **附件**: 将 PDF 放入 `assets/attachments/` (或 `B2B`/`B2C` 子目录)。

### 3. 启动应用

```bash
streamlit run app.py
```

### 4. 完整工作流

1.  **侧边栏配置**: 填入 API Key 和 Gmail 账号密码。
2.  **模式选择**: 选择 B2B 企业模式或 B2C 创作者模式。
3.  **数据加载**:
    *   从列表选择文件或拖拽上传。
    *   **动态映射**: 如列名不匹配，系统会提示手动映射。
    *   **Leads 确认**: 查看有效邮箱统计，点击确认。
    *   *(如果是未完成任务，可选择继续或重新开始)*
4.  **内容生成**: 点击 **✨ 批量生成内容**，AI 将自动分析并填充个性化字段。
5.  **邮件预览**:
    *   在 "邮件模板编辑" 中修改主题或正文。
    *   选择一行预览实际发送效果。
6.  **批量发送**:
    *   选择附件。
    *   设置 **⏱️ 发送间隔** (建议 3-5s)。
    *   点击 **🚀 批量发送**。

## 📊 邮件追踪服务

本项目依赖 Vercel 服务进行追踪和进度云端备份。详情请见 `email-tracker/README.md`。

---
© 2024 Utopai Studios
