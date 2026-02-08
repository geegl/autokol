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
   - `ADMIN_RESET_KEY`: 用于重置数据的密钥 (自定义字符串)
   - `PROGRESS_API_KEY`: 用于进度同步的密钥 (自定义字符串，需与 Streamlit 侧边栏一致)

4. **获取 URL**:
   部署完成后获得 `https://your-project.vercel.app`。

## API 端点

| 端点 | 方法 | 描述 | 鉴权 |
|-----|-----|------|------|
| `/api/open/[id]` | GET | 追踪邮件打开 (返回透明像素) | 无 |
| `/api/click/[id]` | GET | 追踪链接点击 (302 跳转) | 无 |
| `/api/stats` | GET | 查看统计数据 | 无 (公开) |
| `/api/progress` | GET/POST | 进度同步 (存取 JSON/CSV) | `Authorization: Bearer <PROGRESS_API_KEY>` |
| `/api/reset` | GET | 清空所有数据 | `?key=<ADMIN_RESET_KEY>` |

## 使用示例

在邮件 HTML 中添加追踪像素:
```html
<img src="https://your-app.vercel.app/api/open/email_123" width="1" height="1">
```

点击追踪:
```html
<a href="https://your-app.vercel.app/api/click/email_123?url=https://target.com">Click Me</a>
```

## 注意事项

- 本服务强依赖 **Upstash Redis**，请确保 Redis 实例运行正常。
- 只有配置了正确的环境变量，进度同步和重置功能才能正常工作。
