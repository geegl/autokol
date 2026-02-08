# Email Tracker - Vercel Serverless

自建邮件追踪服务，支持打开率和点击率追踪。

## 部署到 Vercel

1. 安装 Vercel CLI:
```bash
npm i -g vercel
```

2. 部署:
```bash
cd email-tracker
vercel
```

3. 记录生成的 URL (例如: `https://email-tracker-xxx.vercel.app`)

## API 端点

| 端点 | 描述 |
|-----|------|
| `GET /api/open/{id}` | 追踪打开，返回透明像素 |
| `GET /api/click/{id}?url=xxx` | 追踪点击，302 重定向 |
| `GET /api/stats` | 查看所有统计 |
| `GET /api/stats?id=xxx` | 查看单个邮件统计 |

## 使用示例

在邮件 HTML 中添加:
```html
<img src="https://your-tracker.vercel.app/api/open/email123" width="1" height="1">
<a href="https://your-tracker.vercel.app/api/click/email123?url=https://calendly.com/xxx">预约会议</a>
```

## 注意事项

- 数据存储在 `/tmp`，Vercel 函数重启后会丢失
- 生产环境建议使用 Vercel KV (需付费或免费额度)
