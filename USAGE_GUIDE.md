# AutoKol 使用指南

> Utopai Cold Email Engine 完整操作手册

---

## 目录

1. [登录系统](#1-登录系统)
2. [配置侧边栏](#2-配置侧边栏)
3. [B2B/B2C 模式操作流程](#3-b2bb2c-模式操作流程)
4. [PAI PRO 模式操作流程](#4-pai-pro-模式操作流程)
5. [邮件预览与发送](#5-邮件预览与发送)
6. [追踪仪表盘](#6-追踪仪表盘)
7. [发送记录](#7-发送记录)
8. [常见问题](#8-常见问题)

---

## 1. 登录系统

### 1.1 打开应用

访问 https://autokol.streamlit.app

### 1.2 输入访问密码

如果管理员设置了 `APP_PASSWORD`，页面会显示密码输入框：

1. 在「访问密码」输入框中输入密码
2. 点击「登录」按钮
3. 密码正确后自动进入主界面

> 如果没有设置 `APP_PASSWORD`，则直接进入主界面，无需登录。

### 1.3 首次使用引导

首次打开会显示引导页面，包含 3 个步骤：

1. **配置 AI 服务** — 获取硅基流动 API Key
2. **配置 Gmail 发送** — 获取应用专用密码
3. **邮件追踪** — 默认已配置

点击「完成设置，开始使用」或「稍后再说」进入主界面。

---

## 2. 配置侧边栏

进入主界面后，左侧边栏是「配置中心」，所有配置都在这里完成。

### 2.1 LLM 设置（硅基流动）

用于 AI 自动生成邮件内容（B2B/B2C 模式需要，PAI PRO 模式不需要）。

| 字段 | 说明 | 默认值 |
|------|------|--------|
| 硅基流动 API Key | 在 https://cloud.siliconflow.cn/account/ak 获取 | （必填） |
| Base URL | API 地址 | `https://api.siliconflow.cn/v1` |
| Model Name | 模型名称 | `deepseek-ai/DeepSeek-V4-Pro` |

**获取 API Key 步骤：**
1. 访问 https://cloud.siliconflow.cn
2. 注册/登录账号
3. 进入「账户」→「API Keys」
4. 点击「创建 API Key」
5. 复制 Key 粘贴到侧边栏

> 如果在 Streamlit Cloud 的 Secrets 中配置了 `SILICONFLOW_API_KEY`，此处会自动预填，无需手动输入。

### 2.2 邮箱设置（Email Service）

选择邮件服务商，支持两种：

#### Gmail (SMTP) — 推荐

| 字段 | 说明 |
|------|------|
| 发件人邮箱地址 | 你的 Gmail 或 Google Workspace 邮箱，如 `marketing@utopaistudios.com` |
| 应用专用密码 | Google 账户生成的 16 位密码（不是登录密码） |

**获取应用专用密码步骤：**
1. 访问 https://myaccount.google.com/security
2. 确保已启用「两步验证」（必须先开启）
3. 进入「两步验证」→ 页面底部找到「应用专用密码」
4. 选择「邮件」和「其他（自定义名称）」，输入名称如 `autokol`
5. 点击「生成」
6. 复制生成的 16 位密码（格式如 `abcd efgh ijkl mnop`）
7. 粘贴到侧边栏的「应用专用密码」字段

> 应用专用密码只需要生成一次，之后每次打开应用如果在 Secrets 中配置了 `GMAIL_APP_PASSWORD` 会自动预填。

#### SendGrid (API) — 大规模发送

| 字段 | 说明 |
|------|------|
| SendGrid API Key | 以 `SG.` 开头的 API Key |
| 已验证的发件人身份 | 必须与 SendGrid 后台验证的 Sender Identity 一致 |

### 2.3 发件人信息

| 字段 | 说明 | 默认值 |
|------|------|--------|
| Your Name | 发件人姓名 | `Cecilia` |
| Your Title | 发件人职位 | `Director of Creative Partnerships` |

这些信息会出现在邮件签名中。

### 2.4 邮件追踪（可选）

| 字段 | 说明 | 默认值 |
|------|------|--------|
| 追踪服务 URL | Vercel 部署的追踪服务地址 | `https://autokol.vercel.app` |

追踪功能会自动：
- 在邮件中插入追踪像素（检测打开）
- 将链接重写为追踪链接（检测点击）
- 在「追踪仪表盘」tab 中展示数据

> 保持默认值即可，无需修改。

---

## 3. B2B/B2C 模式操作流程

B2B（企业客户）和 B2C（创作者）模式的操作流程相同，以 B2B 为例。

### 3.1 选择模式

点击顶部 tab 切换：
- 🏢 **B2B 企业模式** — 面向企业客户
- 🎨 **B2C 创作者模式** — 面向内容创作者

### 3.2 上传客户名单

有两种方式加载数据：

**方式一：从本地文件选择**
- 系统自动列出 `assets/leads_form/` 目录下的 Excel/CSV 文件
- 从下拉菜单选择一个文件

**方式二：拖拽上传**
- 将 Excel 或 CSV 文件拖拽到上传区域

### 3.3 列名映射

系统会自动识别列名并映射。如果列名不完全匹配，会弹出手动映射界面：

| 内部字段 | B2B 默认列名 | B2C 默认列名 | 说明 |
|----------|-------------|-------------|------|
| client_name | 客户名称 | Name | 公司名/创作者名 |
| contact_person | 决策人 | Name | 联系人姓名 |
| contact_info | 联系方式 | Contact | 邮箱地址 |
| features | 核心特征 | Specialty | 合作方向/特长 |
| pain_point | 破冰话术要点 | Ice Breaker | 个性化切入点 |

映射完成后点击「确认映射」。

### 3.4 选择附件

从下拉菜单选择要附加的 PDF 文件：

- **B2B**: `One-pager-enterprise.pdf`, `Utopai Early Access - Creator FAQ - V2.pdf`
- **B2C**: `One-pager_final.pdf`, `Utopai Early Access - Creator FAQ - V2.pdf`

### 3.5 进度管理

如果之前有未完成的任务，系统会提示：
- **继续上次任务** — 恢复之前的进度
- **重新开始** — 清除旧进度，从头开始

### 3.6 数据预览

显示客户数据表格，可以：
- 直接编辑表格中的内容
- 查看每行的状态（待生成/已生成/发送成功/发送失败）

### 3.7 生成邮件内容

点击 **✨ 批量生成内容** 按钮：

1. AI 会为每行生成个性化的 `Project Title` 和 `Technical Detail`
2. 进度条显示生成进度
3. 生成完成后自动保存

> 生成使用硅基流动的 DeepSeek-V4-Pro 模型，每行约 3-5 秒。

### 3.8 编辑邮件模板

在「✏️ 邮件模板编辑」区域：

1. **选择模板** — 从下拉菜单选择预设模板或自定义
2. **编辑主题** — 修改邮件标题
3. **编辑正文** — 使用富文本编辑器修改邮件内容
4. **切换源码模式** — 点击切换到 HTML 源码编辑

可用变量（会自动替换为实际值）：
- `{creator_name}` — 收件人姓名
- `{sender_name}` — 发件人姓名
- `{project_title}` — AI 生成的项目标题
- `{technical_detail}` — AI 生成的技术细节
- `{sender_title}` — 发件人职位
- `{calendly_link}` — 会议预约链接

### 3.9 预览邮件

右侧显示实时邮件预览：
1. 从下拉菜单选择要预览的行
2. 可以直接编辑 `Project Title` 和 `Technical Detail`
3. 预览区实时更新邮件渲染效果
4. 确认收件人邮箱地址正确

---

## 4. PAI PRO 模式操作流程

PAI PRO 模式是为 PAI Pro 产品推广专门设计的，**不需要 AI 生成内容**，模板已预配置。

### 4.1 切换到 PAI PRO 模式

点击顶部 tab：🚀 **PAI PRO 模式**

### 4.2 上传分段客户名单

系统已预置 4 个分段文件，从下拉菜单选择：

| 文件名 | 用户数 | 对应模板 | 说明 |
|--------|--------|---------|------|
| `pai_pro_1_deep_creation_and_pricing.xlsx` | 273 | Deep Creation + Pricing | 深度使用 + 看过价格，转化率最高 |
| `pai_pro_2_deep_creation_only.xlsx` | 1,056 | Deep Creation Only | 深度使用但没看价格，最大池子 |
| `pai_pro_3_paid_success.xlsx` | 137 | Paid Success | 已付费用户，付费意愿已验证 |
| `pai_pro_4_checkout_no_success.xlsx` | 341 | Checkout No Success | 发起结账但未完成，有购买意向 |

### 4.3 自动模板匹配

上传文件后，系统会根据文件名自动：
- 选中对应的邮件模板
- 填充正确的 Subject Line
- 加载完整的 HTML 邮件正文

4 个模板的 Subject Line：

| 模板 | Subject Line |
|------|-------------|
| Deep Creation + Pricing | Your project is already in motion. Keep building |
| Deep Creation Only | Here is a faster path to building your projects |
| Paid Success | Turn your next idea into a repeatable creation workflow |
| Checkout No Success | Your project is already in motion. Don't stop here. |

### 4.4 确认映射

系统自动映射列名：

| 内部字段 | Excel 列名 | 说明 |
|----------|-----------|------|
| client_name | Name | 收件人姓名（空值时自动从邮箱提取） |
| contact_info | emails | 邮箱地址 |
| features | segment | 用户分段 |
| pain_point | core_sections_visited | 访问过的核心功能 |

> Name 列为空时，系统自动从邮箱地址提取用户名。例如 `abc@xyz.com` → 显示为 `abc`。

### 4.5 跳过内容生成

PAI PRO 模式**不需要** AI 生成内容，会显示：

> ✅ 模板已预配置，跳过内容生成步骤

直接进入邮件预览和发送阶段。

### 4.6 预览与调整

1. 从下拉菜单选择要预览的行
2. 右侧显示邮件渲染效果
3. 可以在「✏️ 邮件模板编辑」区域修改模板内容（可选）
4. 确认 Subject Line 和邮件内容无误

### 4.7 分段发送策略

**建议按优先级顺序发送，每批间隔 1-2 天：**

| 顺序 | 分段 | 人数 | 建议 |
|------|------|------|------|
| 第 1 批 | Paid Success | 137 | 最小批次，测试水温 |
| 第 2 批 | Checkout No Success | 341 | 有购买意向 |
| 第 3 批 | Deep Creation + Pricing | 273 | 转化率最高 |
| 第 4 批 | Deep Creation Only | 1,056 | 最大池子，最后发 |

---

## 5. 邮件预览与发送

### 5.1 发送前检查清单

- [ ] 侧边栏 Gmail 邮箱地址和应用专用密码已填写
- [ ] 发件人姓名和职位正确
- [ ] 邮件模板 Subject Line 正确
- [ ] 邮件正文内容无误
- [ ] 追踪服务 URL 正确（默认即可）
- [ ] 预览了至少 2-3 封邮件确认格式正常
- [ ] 确认收件人邮箱地址有效

### 5.2 发送设置

在发送区域配置发送参数：

| 设置 | 说明 | 建议值 |
|------|------|--------|
| 🎲 启用智能随机间隔 | 每封邮件之间随机等待 5-10 秒 | ✅ 开启 |
| ⏱️ 固定发送间隔 | 如果关闭随机间隔，使用固定间隔 | 仅在需要时使用 |

**强烈建议保持智能随机间隔开启**，模拟人工操作，降低被标记为垃圾邮件的风险。

### 5.3 批量发送

1. 确认队列中有待发送邮件（顶部会显示数量）
2. 选择要附加的 PDF 文件（B2B/B2C 模式）
3. 点击 **🚀 批量发送** 按钮
4. 系统开始逐封发送，显示实时进度

### 5.4 发送过程中的操作

- **暂停发送** — 点击「⏸️ 暂停」按钮，已发送的邮件不受影响
- **恢复发送** — 点击「▶️ 继续」按钮，从暂停处继续
- **查看进度** — 顶部显示已发送/总数/失败数

### 5.5 发送完成

发送完成后：
- 每行状态更新为「发送成功」或「发送失败」
- 进度自动保存到本地和云端
- 发送记录自动写入「发送记录」tab
- 追踪数据开始收集

### 5.6 失败重试

如果有发送失败的行：
1. 查看失败原因（通常是邮箱无效或认证失败）
2. 修正问题后，点击「🚀 批量发送」
3. 系统只发送状态为「待发送」的行，已成功的不会重复发送

---

## 6. 追踪仪表盘

点击顶部 tab：📊 **追踪仪表盘**

### 6.1 数据概览

仪表盘显示所有已发送邮件的追踪数据：

| 指标 | 说明 |
|------|------|
| 总联系人 | 收到邮件的独立联系人数 |
| 总打开次数 | 所有邮件被打开的总次数 |
| 总点击次数 | 邮件中链接被点击的总次数 |
| 打开率 | 打开人数 / 发送人数 |
| 点击率 | 点击人数 / 发送人数 |

### 6.2 联系人详情

点击联系人可以查看：
- 收到的所有邮件列表
- 每封邮件的打开时间和次数
- 点击的链接和时间
- 区分真实打开和机器预取（如 Google Image Proxy）

### 6.3 注意事项

- Gmail 会通过 Google Image Proxy 预加载图片，导致打开率被高估
- Apple Mail 的隐私保护功能也会预加载图片
- 仪表盘会标记机器预取（`isBot: true`），可以过滤

---

## 7. 发送记录

点击顶部 tab：📨 **发送记录**

### 7.1 查看记录

显示所有发送记录，包含：
- 发送时间
- 收件人邮箱
- 收件人姓名
- 邮件主题
- 发送状态（成功/失败）
- 失败原因（如有）
- 所属模式（B2B/B2C/PAI_PRO）

### 7.2 今日统计

顶部显示今日发送统计：
- 今日总发送数
- 成功数
- 失败数

---

## 8. 常见问题

### Q: 页面提示「云端进度读取失败（401）」

**原因**：Streamlit 与 Vercel 的 API Key 不一致。

**解决**：确认 Streamlit Cloud Secrets 中的 `PROGRESS_API_KEY` 与 Vercel 环境变量中的 `PROGRESS_API_KEY` 一致。

### Q: Gmail 报错 `535 Username and Password not accepted`

**原因**：Google 认证失败。

**解决**：
1. 确认已启用两步验证
2. 重新生成应用专用密码
3. 确认邮箱地址正确（不要用登录密码）

### Q: 邮件发送成功但收件人没收到

**可能原因**：
- 邮箱地址无效或拼写错误
- 被收件方的垃圾邮件过滤器拦截
- Gmail 发送限制已触发（每日 500 封免费 / 2000 封 Workspace）

**解决**：
- 检查发送记录中的状态
- 让收件人检查垃圾邮件文件夹
- 确认发送量未超过限制

### Q: PAI PRO 模式上传文件后显示空白

**原因**：文件未选择或列名映射未确认。

**解决**：
1. 确认从下拉菜单选择了文件（不是只打开 tab）
2. 等待列名映射自动完成
3. 如果弹出映射确认框，点击「确认映射」

### Q: 模板中的变量显示为 `{creator_name}` 而不是实际名字

**原因**：Name 列为空或映射不正确。

**解决**：
- 检查 Excel 文件中 `Name` 列是否有值
- 确认列名映射中 `client_name` 映射到了 `Name` 列
- Name 为空时系统会自动从邮箱提取用户名

### Q: 如何在 Streamlit Cloud 配置 Secrets

1. 访问 https://share.streamlit.io
2. 找到你的应用
3. 点击右上角 **⋮** → **Settings**
4. 找到 **Secrets** 区域
5. 按 TOML 格式添加配置：

```toml
APP_PASSWORD = "你的访问密码"
SILICONFLOW_API_KEY = "你的硅基流动Key"
GMAIL_USER = "marketing@utopaistudios.com"
GMAIL_APP_PASSWORD = "你的应用专用密码"
PROGRESS_API_KEY = "你的云端同步Key"
```

6. 点击 **Save**，应用会自动重启

### Q: 如何更新邮件模板

**B2B/B2C 模板**：编辑 `config/email_settings.yaml` 文件

**PAI PRO 模板**：编辑 `assets/templates/` 目录下的 HTML 文件：
- `pai_pro_deep_creation_and_pricing.html`
- `pai_pro_deep_creation_only.html`
- `pai_pro_paid_success.html`
- `pai_pro_checkout_no_success.html`

修改后需要重新部署（push 到 GitHub，Streamlit Cloud 自动部署）。

---

## 附录：环境变量完整列表

| 变量 | 必填 | 说明 |
|------|------|------|
| `APP_PASSWORD` | 否 | 访问密码，不设置则无登录保护 |
| `SILICONFLOW_API_KEY` | 是* | 硅基流动 API Key（B2B/B2C 需要） |
| `SILICONFLOW_BASE_URL` | 否 | API 地址，默认 `https://api.siliconflow.cn/v1` |
| `SILICONFLOW_MODEL` | 否 | 模型名称，默认 `deepseek-ai/DeepSeek-V4-Pro` |
| `GMAIL_USER` | 是 | Gmail 发件人地址 |
| `GMAIL_APP_PASSWORD` | 是 | Gmail 应用专用密码 |
| `SENDGRID_API_KEY` | 否 | SendGrid API Key（与 Gmail 二选一） |
| `SENDGRID_SENDER` | 否 | SendGrid 已验证发件人 |
| `PROGRESS_API_KEY` | 否 | 云端同步密钥 |
| `SENTRY_DSN` | 否 | Sentry 错误监控 |

> *PAI PRO 模式不需要硅基流动 API Key（模板已预配置，不需要 AI 生成内容）。

---

© 2026 Utopai Studios
