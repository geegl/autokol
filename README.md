# 🔥 Utopai Cold Email Engine

专业的冷启动邮件发送引擎，专为 Utopai Studios 定制。集成 LLM 个性化生成、PDF 附件管理、Vercel 邮件追踪和 Gmail SMTP 发送服务。

## ✨ 特性

- **模块化架构**：专业的 `src/` 目录结构，业务逻辑与 UI 分离。
- **智能化生成**：利用硅基流动 DeepSeek-V3.2 API 自动生成个性化的 Project Title 和 Technical Detail。
- **自动化追踪**：集成 Vercel + Upstash Redis 追踪邮件打开率和点击率。
- **本地化管理**：支持直接读取 `assets/leads_form` 中的客户名单，生成结果自动保存在 `output/`。
- **原生 Gmail 支持**：完全移除第三方邮件 API，直接通过 Gmail/Google Workspace SMTP 发送，到达率更高。

## 📂 目录结构

```text
autokol/
├── app.py                  # 启动入口
├── output/                 # ✅ [自动生成] 进度文件和结果保存位置
├── assets/                 # ✅ [手动管理] 资源文件夹
│   ├── leads_form/         # ➡️ 将客户 Excel/CSV 名单放入此处
│   └── attachments/        # ➡️ 存放需要发送的 PDF 附件
├── email-tracker/          # Vercel 追踪服务代码
├── src/                    # 源代码
└── requirements.txt
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆代码
git clone https://github.com/geegl/autokol.git
cd autokol

# 安装依赖
pip install -r requirements.txt
```

### 2. 资源配置

1.  将客户名单 Excel/CSV 文件放入 `assets/leads_form/`。
2.  确保 `assets/attachments/` 中包含以下附件（如不一样请修改 `src/config.py`）：
    *   `Utopai Early Access - Creator FAQ - V2.pdf`
    *   `One-pager-enterprise.pdf` (B2B)
    *   `One-pager_final.pdf` (B2C)

### 3. Gmail 配置

为了安全发送邮件，请使用 **App Password (应用专用密码)**：
1.  登录 Google 账号。
2.  开启两步验证 (2FA)。
3.  搜索 "App Passwords"，生成一个新的密码（名称可填 Autokol）。
4.  保存这个 16 位密码。

### 4. 启动应用

```bash
streamlit run app.py
```

### 5. 在应用中操作
1.  **侧边栏配置**：
    *   填入 **硅基流动 API Key**。
    *   填入 **Gmail 账号** 和 **应用专用密码**。
    *   确认 **追踪 URL** (Vercel)。
2.  **主界面操作**：
    *   选择 B2B 或 B2C 模式。
    *   在 "从 assets/leads_form 选择文件" 下拉框中选择你的名单。
    *   点击 **✨ 批量生成内容**。
    *   生成并保存完毕后，下拉预览生成的邮件内容。
    *   点击 **🚀 批量发送**。
3.  **结果查看**：
    *   生成的带状态文件会自动保存在 `output/autokol_progress_xxx.csv`。
    *   在 **📊 追踪仪表盘** Tab 查看实时打开/点击数据。

## 📊 邮件追踪

项目包含一个独立的 `email-tracker` 服务，需部署到 Vercel：
1.  `cd email-tracker`
2.  `vercel deploy --prod`
3.  在 Vercel 后台配置环境变量：
    *   `UPSTASH_REDIS_REST_URL`
    *   `UPSTASH_REDIS_REST_TOKEN`
4.  获取 Vercel URL (如 `https://autokol-tracker.vercel.app`) 填入 Streamlit 侧边栏。
5.  **重置数据**：访问 `https://your-vercel-url/api/reset?key=autokol_admin_reset` 可清空所有追踪记录。

---
© 2024 Utopai Studios
