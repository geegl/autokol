# 🔥 Utopai Cold Email Engine (V2.12)

专业的冷启动邮件发送引擎，专为 Utopai Studios 定制。集成 LLM 个性化生成、PDF 附件管理、Vercel 邮件追踪和 Gmail SMTP 发送服务。

## ✨ 核心特性

- **智能化生成**: 利用硅基流动 DeepSeek-V3.2 API 自动生成个性化的 "Project Title" 和 "Technical Detail"。
- **所见即所得 (V2.5 NEW)**: 预览区不仅可以修改邮件正文，现在还支持直接 **编辑修正 AI 生成的内容** (Project Title/Detail)，修改后自动保存。
- **高级主题管理 (V2.3 NEW)**: 下拉式选择预设高转化主题，亦可随时切换至自定义模式输入。
- **B2B/B2C 双模式**: 支持针对企业客户和创作者的不同话术策略与邮件主题配置。
- **通用 Excel 适配**: 支持任意列名映射，且会自动识别“历史进度与当前文件不一致”并切换为重新开始，避免读错旧任务。
- **会话级防丢失**: 生成后的内容会缓存到当前会话，切换预览行或触发 rerun 不会把已生成字段清空。
- **交互增强 (V2.4)**: 实时无延迟的预览更新，以及明确的发送队列状态提示，拒绝盲发。
- **安全与鲁棒性 (V2.8)**: 
  - **智能随机间隔**: 默认启用 5-10 秒随机发送间隔 (支持自定义范围)，模拟人工操作，显着降低风控风险。
  - **隐私保护**: 自动清洗附件文件名，避免本地路径泄露。
  - **智能同步**: 云端进度备份采用智能限流策略，大批量生成时性能提升显著。
  - **零配置回退**: 未配置 `PROGRESS_API_KEY` 时自动回退内置 key，并支持双 key 重试。
- **任务恢复 (V2.2)**: 自动保存发送进度，支持 **断点续传** 或 **重新开始**，不用担心浏览器崩溃。
- **动态数据映射 (V2.0)**: 上传任意格式 Excel/CSV，智能映射列名。

## 📂 目录结构

```text
autokol/
├── app.py                  # 启动入口
├── output/                 # ✅ [自动生成] 进度文件和结果保存位置
├── assets/                 # ✅ [手动管理] 资源文件夹
│   ├── leads_form/         # ➡️ 将客户 Excel/CSV 名单放入此处
│   └── attachments/        # ➡️ 存放 PDF 附件 (根目录或按 B2B/B2C 子目录分类)
├── config/
│   └── email_settings.yaml # 📧 邮件主题(列表)、签名、模板配置文件
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

1.  **邮件配置**: 修改 `config/email_settings.yaml` 设置邮件主题列表 (Subject List) 和签名。
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
5.  **邮件预览与修正**:
    *   **主题选择**: 在 "编辑邮件模板" 区域下拉选择预设主题，或自定义。
    *   **内容修正**: 在右侧预览区，直接修改 AI 生成的 Project Title 或 Detail，所见即所得。
    *   **实时确认**: 点击 "刷新预览" 确保最终效果无误。
6.  **批量发送**:
    *   **状态提示**: 顶部会显示剩余待发邮件数量。
    *   选择附件。
    *   **发送策略**: 默认开启 **🎲 智能随机间隔 (5-10s)**，推荐保持开启以确保安全。如需追求速度，可取消勾选并手动设置固定间隔。
    *   点击 **🚀 批量发送**。

## 📊 邮件追踪服务

本项目依赖 Vercel 服务进行追踪和进度云端备份。详情请见 `email-tracker/README.md`。

## 🧩 稳定性说明

1. `output/` 下进度 CSV 不再纳入 Git 版本控制，避免部署时带入历史快照。
2. `api/progress` 支持 `B2B`、`B2C`、`user_templates`、`send_history` 四种 mode。
3. 模板渲染默认支持 `{calendly_link}` 变量，避免预览/发送阶段 `Template Error`。
4. 附件路径支持“文件名”和“完整路径”两种输入，减少附件读取失败。

## 🛠️ 故障排查

1. 页面提示 `云端进度读取失败（401）`
   - 含义：Streamlit 与 Vercel 的 key 不一致，系统会回退到本地进度。
   - 建议：统一 `PROGRESS_API_KEY`（Streamlit Secrets 与 Vercel Env）。
2. 页面提示 `未配置 PROGRESS_API_KEY`
   - 含义：未显式配置 key，系统会自动使用 fallback key。
   - 建议：生产环境仍建议配置正式 `PROGRESS_API_KEY`。
3. Gmail 报错 `535 Username and Password not accepted`
   - 含义：Google 认证失败，不是模板逻辑问题。
   - 建议：确认账号开启 2FA，并重新生成 App Password 后填写。

## 📒 BugFix 记录

详见 `BUGFIX.md`，包含每次修复的症状、根因、修复点与验证方式。

---
© 2026 Utopai Studios
