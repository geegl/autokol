// 查询追踪统计数据 - 友好格式
const fs = require('fs');
const DATA_FILE = '/tmp/tracking_data.json';

function loadData() {
    try {
        if (fs.existsSync(DATA_FILE)) {
            return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
        }
    } catch (e) { }
    return { opens: {}, clicks: {} };
}

// 解析 email_id: 格式为 "mode_idx_timestamp_recipientEmail_recipientName"
function parseEmailId(emailId) {
    const parts = emailId.split('_');
    if (parts.length >= 5) {
        return {
            mode: parts[0],
            index: parts[1],
            timestamp: parts[2],
            email: parts[3] || 'unknown',
            name: parts.slice(4).join('_') || 'unknown'
        };
    }
    // 兼容旧格式
    return {
        mode: parts[0] || 'unknown',
        index: parts[1] || '0',
        timestamp: parts[2] || '0',
        email: 'unknown',
        name: 'unknown'
    };
}

module.exports = async (req, res) => {
    // 简单的 API Key 验证 (可选)
    const apiKey = req.headers['x-api-key'] || req.query.key;
    const expectedKey = process.env.TRACKER_API_KEY;

    if (expectedKey && apiKey !== expectedKey) {
        return res.status(401).json({ error: 'Unauthorized' });
    }

    const data = loadData();
    const { id, format } = req.query;

    // 查询特定邮件的追踪数据
    if (id) {
        const parsed = parseEmailId(id);
        return res.json({
            email_id: id,
            recipient_email: parsed.email,
            recipient_name: parsed.name,
            opens: data.opens[id] || [],
            clicks: data.clicks[id] || [],
            open_count: (data.opens[id] || []).length,
            click_count: (data.clicks[id] || []).length,
            has_opened: (data.opens[id] || []).length > 0,
            has_clicked: (data.clicks[id] || []).length > 0
        });
    }

    // 友好格式输出
    if (format === 'friendly') {
        const allRecipients = new Set([
            ...Object.keys(data.opens),
            ...Object.keys(data.clicks)
        ]);

        const recipients = Array.from(allRecipients).map(emailId => {
            const parsed = parseEmailId(emailId);
            const opens = data.opens[emailId] || [];
            const clicks = data.clicks[emailId] || [];

            return {
                email_id: emailId,
                recipient_email: parsed.email,
                recipient_name: parsed.name,
                opened: opens.length > 0,
                clicked: clicks.length > 0,
                open_count: opens.length,
                click_count: clicks.length,
                first_open: opens.length > 0 ? opens[0].timestamp : null,
                first_click: clicks.length > 0 ? clicks[0].timestamp : null
            };
        });

        // 按打开状态和时间排序
        recipients.sort((a, b) => {
            if (a.opened !== b.opened) return b.opened - a.opened;
            if (a.clicked !== b.clicked) return b.clicked - a.clicked;
            return 0;
        });

        return res.json({
            total_tracked: recipients.length,
            opened_count: recipients.filter(r => r.opened).length,
            clicked_count: recipients.filter(r => r.clicked).length,
            recipients: recipients
        });
    }

    // 原始汇总统计
    const summary = {
        total_emails_opened: Object.keys(data.opens).length,
        total_opens: Object.values(data.opens).reduce((sum, arr) => sum + arr.length, 0),
        total_emails_clicked: Object.keys(data.clicks).length,
        total_clicks: Object.values(data.clicks).reduce((sum, arr) => sum + arr.length, 0),
        recent_opens: Object.entries(data.opens)
            .flatMap(([id, events]) => {
                const parsed = parseEmailId(id);
                return events.map(e => ({
                    email_id: id,
                    recipient_email: parsed.email,
                    recipient_name: parsed.name,
                    ...e
                }));
            })
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
            .slice(0, 20),
        recent_clicks: Object.entries(data.clicks)
            .flatMap(([id, events]) => {
                const parsed = parseEmailId(id);
                return events.map(e => ({
                    email_id: id,
                    recipient_email: parsed.email,
                    recipient_name: parsed.name,
                    ...e
                }));
            })
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
            .slice(0, 20)
    };

    res.json(summary);
};
