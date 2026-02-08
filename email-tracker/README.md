# Email Tracker - Vercel Serverless

自建邮件追踪服务，支持打开率/点击率追踪，以及发送进度云端同步。

## 部署到 Vercel

1. **安装 Vercel CLI**:
   ```bash
   npm i -g vercel
   ```

2. **部署**:
   ```bash
   cd email-tracker
   vercel --prod
   ```

3. **配置环境变量 (Vercel Dashboard)**:
   - `UPSTASH_REDIS_REST_URL`: Upstash Redis URL
   - `UPSTASH_REDIS_REST_TOKEN`: Upstash Redis Token
   - `ADMIN_RESET_KEY`: 用于重置数据的密钥 (自定义字符串，用于 /api/reset)
   - `PROGRESS_API_KEY`: 用于进度同步的密钥 (自定义字符串，需与 Streamlit 侧边栏一致)

4. **获取 URL**:
   部署完成后获得 `https://your-project.vercel.app`。

## API 端点

| 端点 | 方法 | 描述 | 鉴权 |
|-----|-----|------|------|
| `/api/open/[id]` | GET | 追踪邮件打开 (返回透明像素) | 无 |
| `/api/click/[id]` | GET | 追踪链接点击 (302 跳转) | 无 |
| `/api/stats` | GET | 查看统计数据 | 无 (公开) |
| `/api/progress` | GET/POST | 进度同步 (存取 JSON 数据) | Header `x-api-key: <KEY>` 或 Query `?key=<KEY>` (推荐前者) |
| `/api/reset` | GET | 清空所有数据 | Query `?key=<ADMIN_RESET_KEY>` |

## 使用示例

### 邮件追踪
在邮件 HTML 中添加追踪像素:
```html
<img src="https://your-app.vercel.app/api/open/email_123" width="1" height="1">
```

### 链接追踪
```html
<a href="https://your-app.vercel.app/api/click/email_123?url=https://target.com">Click Me</a>
```

### 进度同步 (Python 示例)
```python
import requests
headers = {"x-api-key": "your_secret_key"}
# 保存进度
requests.post("https://your-app.vercel.app/api/progress?mode=B2B", json={"data": [...]}, headers=headers)
# 读取进度
data = requests.get("https://your-app.vercel.app/api/progress?mode=B2B", headers=headers).json()
```

## 注意事项

- 本服务强依赖 **Upstash Redis**，请确保 Redis 实例运行正常。
- 数据安全: 请保管好 `ADMIN_RESET_KEY` 和 `PROGRESS_API_KEY`，不要将其提交到公开代码仓库。
- 隐私: 追踪 URL 中包含的 ID 可能包含部分脱敏的用户信息，请谨慎分享原始链接。
