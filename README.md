# 🔥 Utopai Cold Email Engine (V2.17)

专业的冷启动邮件发送引擎，专为 Utopai Studios 定制。集成 LLM 个性化生成、PDF 附件管理、Vercel 邮件追踪、退订管理和 Gmail SMTP 发送服务。

## ✨ 核心特性

- **三种模式**:
  - **B2B 企业模式** — 面向企业客户的冷邮件触达
  - **B2C 创作者模式** — 面向内容创作者的个性化邮件
  - **PAI PRO 模式** — 产品推广专用，预配置模板，跳过 AI 生成，自动匹配分段模板
- **智能化生成**: 利用硅基流动 DeepSeek-V4-Pro API 自动生成个性化内容（B2B/B2C 模式）。
- **退订管理**: 每封邮件自动生成签名退订链接（HMAC-SHA256），收件人可一键退订，退订后自动跳过。
- **登录保护**: 通过 `APP_PASSWORD` 环境变量设置访问密码，保护内部工具安全。
- **环境变量预填**: 所有 API Key 支持通过 Streamlit Secrets 预填，无需每次手动输入。
- **通用 Excel 适配**: 支持任意列名映射，智能模糊匹配。
- **会话级防丢失**: 生成后的内容缓存到当前会话，切换预览行不会清空。
- **智能随机间隔**: 默认 5-10 秒随机发送间隔，模拟人工操作。
- **任务恢复**: 自动保存发送进度，支持断点续传。
- **邮件追踪**: 追踪像素（打开检测）+ 追踪链接（点击检测），Dashboard 实时展示。
- **双邮件服务商**: 支持 Gmail SMTP 和 SendGrid API 双模式。

## 📂 目录结构

```text
autokol/
├── app.py                      # 启动入口
├── Dockerfile                  # Docker 部署配置
├── pyproject.toml              # 项目元数据
├── USAGE_GUIDE.md              # 完整使用手册
├── assets/
│   ├── leads_form/             # 客户名单 (Excel/CSV)
│   ├── attachments/            # PDF 附件
│   └── templates/              # PAI Pro HTML 邮件模板
├── config/
│   └── email_settings.yaml     # 邮件主题、签名、模板配置
├── email-tracker/              # Vercel 无服务追踪 + 退订服务
│   └── api/
│       ├── open/[id].js        # 打开追踪 (1x1 像素)
│       ├── click/[id].js       # 点击追踪 (302 重定向)
│       ├── unsubscribe.js      # 退订处理 (HMAC 签名验证)
│       ├── progress.js         # 云端进度同步
│       ├── stats/index.js      # 追踪数据统计
│       └── reset.js            # 数据重置
├── src/
│   ├── services/
│   │   ├── content_gen.py      # LLM 内容生成
│   │   ├── email_sender.py     # Gmail SMTP / SendGrid 发送
│   │   ├── llm.py              # LLM API 封装
│   │   ├── tracking.py         # 追踪 URL + 退订链接生成
│   │   └── send_history.py     # 发送历史管理
│   ├── ui/
│   │   ├── mode_handler.py     # 核心模式 UI (B2B/B2C/PAI_PRO)
│   │   ├── dashboard.py        # 追踪仪表盘
│   │   ├── sidebar.py          # 侧边栏配置
│   │   ├── onboarding.py       # 首次使用引导
│   │   └── history_tab.py      # 发送记录
│   ├── utils/
│   │   ├── api_keys.py         # 共享 API Key 工具
│   │   ├── helpers.py          # 进度持久化、文件加载
│   │   ├── template_manager.py # 模板 CRUD + 云端同步
│   │   ├── mapping_profiles.py # 列映射持久化
│   │   └── templates.py        # 邮件模板加载
│   └── config.py               # 模式配置 (B2B/B2C/PAI_PRO)
├── tests/
│   └── test_api_keys.py        # API Key 单元测试
├── output/                     # 自动生成的进度文件
├── requirements.txt
└── .env.example                # 环境变量参考
```

## 🚀 快速开始

### 1. 环境准备

```bash
git clone https://github.com/geegl/autokol.git
cd autokol
pip install -r requirements.txt
```

### 2. 启动应用

```bash
streamlit run app.py
```

### 3. 首次使用

1. 首次打开会显示引导页面，按提示完成初始配置。
2. 在侧边栏填入 API Key 和 Gmail 账号密码。
3. 选择模式（B2B/B2C/PAI PRO），上传客户名单，开始使用。

> 详细操作步骤请参见 [USAGE_GUIDE.md](USAGE_GUIDE.md)

## ⚙️ 环境变量

通过环境变量或 Streamlit Secrets 可预填配置，避免每次手动输入。

| 变量 | 说明 | 必填 |
|------|------|------|
| `APP_PASSWORD` | 访问密码（不设置则无登录保护） | 否 |
| `SILICONFLOW_API_KEY` | 硅基流动 API Key（PAI PRO 不需要） | B2B/B2C 需要 |
| `SILICONFLOW_BASE_URL` | LLM API 地址 | 否 |
| `SILICONFLOW_MODEL` | 模型名称 | 否 |
| `GMAIL_USER` | Gmail 发件人地址 | 是 |
| `GMAIL_APP_PASSWORD` | Gmail 应用专用密码 | 是 |
| `SENDGRID_API_KEY` | SendGrid API Key（与 Gmail 二选一） | 否 |
| `SENDGRID_SENDER` | SendGrid 已验证发件人 | 否 |
| `PROGRESS_API_KEY` | 云端同步密钥 | 否 |
| `UNSUBSCRIBE_SECRET_KEY` | 退订链接签名密钥（两端必须一致） | 推荐 |
| `SENTRY_DSN` | Sentry 错误监控 | 否 |

### Streamlit Cloud Secrets 配置示例

在 Streamlit Cloud → Settings → Secrets 中按 TOML 格式添加：

```toml
APP_PASSWORD = "your_password"
SILICONFLOW_API_KEY = "sk-xxx"
GMAIL_USER = "marketing@utopaistudios.com"
GMAIL_APP_PASSWORD = "xxxx-xxxx-xxxx-xxxx"
PROGRESS_API_KEY = "your_progress_key"
UNSUBSCRIBE_SECRET_KEY = "your_secret_key"
```

## 📧 PAI PRO 模式

PAI PRO 模式专为产品推广设计，预配置了 4 个分段模板：

| 分段 | 用户数 | 说明 |
|------|--------|------|
| Deep Creation + Pricing | 273 | 深度使用 + 看过价格 |
| Deep Creation Only | 1,056 | 深度使用但没看价格 |
| Paid Success | 137 | 已付费用户 |
| Checkout No Success | 341 | 发起结账但未完成 |

- 上传对应分段的 xlsx 文件后，系统自动匹配模板和 Subject Line
- 跳过 AI 内容生成步骤，直接预览和发送
- Name 为空时自动从邮箱地址提取用户名

## 🔗 退订管理

- 每封邮件自动注入签名退订链接（HMAC-SHA256）
- 收件人点击后显示确认页面（Utopai 品牌风格）
- 确认退订后加入 Redis 退订列表
- 后续发送自动跳过已退订的邮箱
- 链接永不过期，重复点击安全

## 📊 邮件追踪

追踪服务部署在 Vercel，使用 Upstash Redis 存储数据：

- **打开追踪**: 邮件中嵌入 1x1 透明像素
- **点击追踪**: 链接重写为追踪链接，记录点击后 302 跳转
- **Dashboard**: 实时查看打开率、点击率，区分真实打开和机器预取
- **退订追踪**: 记录退订事件和时间

## 🛠️ 故障排查

| 问题 | 解决方案 |
|------|---------|
| 云端进度读取失败 (401) | 统一 `PROGRESS_API_KEY`（Streamlit Secrets 与 Vercel Env） |
| Gmail `535` 认证失败 | 确认开启 2FA，重新生成应用专用密码 |
| 退订链接 404 | 确认 Vercel email-tracker 已重新部署，`UNSUBSCRIBE_SECRET_KEY` 两端一致 |
| PAI PRO tab 空白 | 需要先从下拉菜单选择/上传一个 xlsx 文件 |
| 追踪数据丢失 | 检查 Upstash Redis 实例是否正常运行 |

## 📖 更多文档

- [USAGE_GUIDE.md](USAGE_GUIDE.md) — 完整使用手册（从登录到发送）
- [BUGFIX.md](BUGFIX.md) — 历史 Bug 修复记录
- [email-tracker/README.md](email-tracker/README.md) — 追踪服务 API 文档

---
© 2026 Utopai Studios
