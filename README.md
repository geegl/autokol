# 🚀 Utopai Cold Email Engine

一个智能化的冷邮件自动化工具，支持 B2B 企业客户和 B2C 创作者两种模式，使用 AI 生成个性化话术并通过 Gmail 批量发送。

## ✨ 功能特性

### 双模式支持
| 模式 | 目标客户 | Excel 列要求 | 附件 |
|------|---------|-------------|------|
| 🏢 **B2B** | 企业客户 | 客户名称, 决策人, 联系方式, 核心特征, 破冰话术要点 | FAQ + One-pager-enterprise.pdf |
| 🎨 **B2C** | 创作者 | Name, Contact, Specialty, Ice Breaker, Unnamed:10 | FAQ + One-pager_final.pdf |

### AI 内容生成
- 🤖 **硅基流动 DeepSeek-V3.2** 模型驱动
- 🌐 中文内容自动翻译为 native speaker 英文
- 🔧 通用模板自动定制化
- ✅ 已有英文内容直接解析使用

### 邮件发送
- 📧 Gmail SMTP 安全发送
- 📎 自动附加 PDF 附件
- 🧪 测试发送功能（发给自己确认格式）
- ⏱️ 可配置的发送间隔，避免触发限流

### 进度管理
- 💾 自动保存进度到本地 CSV
- 🔄 断点续传，页面刷新后可恢复
- 📊 Content_Source 列追踪内容来源

---

## 📋 环境要求

- Python 3.8+
- 依赖包：`streamlit`, `pandas`, `openai`, `openpyxl`

```bash
pip install streamlit pandas openai openpyxl
```

---

## 🚀 快速开始

### 1. 启动应用
```bash
cd /path/to/autokol
streamlit run app.py
```

### 2. 配置 API 和邮箱
在侧边栏填写：
- **硅基流动 API Key**：[获取地址](https://cloud.siliconflow.cn)
- **Gmail 地址**
- **应用专用密码**：Google 账户 → 安全性 → 两步验证 → 应用专用密码
- **发件人姓名和职位**

### 3. 上传 Leads 文件
- 选择 B2B 或 B2C 标签页
- 上传对应格式的 Excel/CSV 文件

### 4. 生成话术
点击「🚀 生成话术」，AI 会为每个 Lead 生成：
- `AI_Project_Title`：项目/作品名称
- `AI_Technical_Detail`：具体赞美内容

### 5. 预览和发送
- 点击「✨ 生成所有邮件」预览完整邮件
- 使用「🧪 测试发送」先发给自己确认
- 确认无误后点击「📤 发送选中的邮件」

---

## 📁 文件结构

```
autokol/
├── app.py                              # 主程序
├── README.md                           # 本文档
├── Utopai Early Access - Creator FAQ - V2.pdf   # 通用附件
├── One-pager-enterprise.pdf            # B2B 专用附件
├── One-pager_final.pdf                 # B2C 专用附件
├── autokol_progress_b2b.csv            # B2B 进度文件（自动生成）
└── autokol_progress_b2c.csv            # B2C 进度文件（自动生成）
```

---

## 📊 Excel 格式要求

### B2B 模式
| 列名 | 说明 | 必填 |
|-----|------|-----|
| 客户名称 | 公司名称 | ✅ |
| 决策人 | 联系人姓名 | ✅ |
| 联系方式 | 包含邮箱的文本 | ✅ |
| 核心特征 | 公司业务特点 | ✅ |
| 破冰话术要点 | 切入点/优势 | ✅ |

### B2C 模式
| 列名 | 说明 | 必填 |
|-----|------|-----|
| Name | 创作者名称/账号 | ✅ |
| Contact | 邮箱地址 | ✅ |
| Specialty | 创作领域/风格 | ✅ |
| Ice Breaker | 破冰话术 | ✅ |
| Unnamed: 10 | 预生成内容（可选） | ❌ |

**Unnamed: 10 内容处理逻辑：**
| 内容类型 | 处理方式 | 标记 |
|---------|---------|------|
| `Loved your work on...` 格式 | 直接解析 | ✅ 已有英文 |
| 包含中文 | AI 翻译润色 | 🌐 中文翻译 |
| 通用模板 | AI 定制化 | 🔧 定制化 |
| 空白 | AI 从头生成 | 🤖 AI生成 |

---

## 📧 邮件模板

**主题：**
```
Utopai Studios Creator Program: Amplify Your Vision - Early and exclusive access to a new AI model for cinematic storytelling?
```

**正文结构：**
```
Hi {creator_name},

I'm {sender_name} from Utopai Studios...

Loved your work on {AI_Project_Title} – particularly the {AI_Technical_Detail}.

[邮件正文...]

Best,
{sender_name}
{sender_title}
Utopai Studios
```

---

## ⚠️ 注意事项

### API 限流
- 硅基流动 API 有调用频率限制
- 建议并发数设为 1-2
- 系统已内置 1 秒/请求的限流保护

### Gmail 发送限制
- Workspace 账户：2000 封/天
- 个人账户：500 封/天
- 建议分批发送，设置 30-60 秒随机间隔

### 安全建议
- 使用 Gmail 应用专用密码，不要使用主密码
- API Key 不要提交到代码仓库

---

## 🔧 故障排查

| 问题 | 解决方案 |
|-----|---------|
| API 429 错误 | 降低并发数，等待几分钟后重试 |
| 邮件发送失败 | 检查应用专用密码是否正确，确认开启两步验证 |
| Excel 读取错误 | 确认列名完全匹配（包括大小写和空格） |
| 进度丢失 | 检查 `autokol_progress_*.csv` 文件是否存在 |

---

## 📝 更新日志

### v2.0 (2026-02)
- ✨ 新增 B2B/B2C 双模式标签页
- 🤖 智能识别内容类型（中文/英文/通用模板）
- 🔧 修复 "Loved your work on" 重复问题
- 💾 分离 B2B/B2C 进度文件
- 🧪 新增测试发送功能

### v1.0 (2026-02)
- 📧 基础邮件发送功能
- 🤖 AI 话术生成
- 💾 自动保存进度

---

## 📄 License

Internal use only - Utopai Studios
