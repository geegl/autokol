// 查询追踪统计数据 - 按收件人聚合
const { Redis } = require('@upstash/redis');

let redis = null;
if (process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN) {
    try {
        redis = new Redis({
            url: process.env.UPSTASH_REDIS_REST_URL,
            token: process.env.UPSTASH_REDIS_REST_TOKEN,
        });
    } catch (err) {
        console.error('Redis init error:', err);
    }
}

async function loadData() {
    if (redis) {
        try {
            // 尝试加载新格式数据
            const data = await redis.get('tracking_data_v2');
            if (data) return { version: 'v2', data };

            // 回退到旧格式（只读）
            const oldData = await redis.get('tracking_data');
            if (oldData) return { version: 'v1', data: oldData };
        } catch (e) {
            console.error('Redis load error:', e);
        }
    }
    return { version: 'v2', data: { contacts: {} } };
}

// 将旧格式数据转换为新格式的展示
function convertOldToNew(oldData) {
    const contacts = {};

    // 解析旧的 opens
    for (const [emailId, events] of Object.entries(oldData.opens || {})) {
        const parts = emailId.split('_');
        if (parts.length >= 5) {
            const emailPart = parts[3] || '';
            const recipientEmail = emailPart.replace('-at-', '@').replace(/-/g, '.');
            const recipientName = parts.slice(4).join('_') || 'Unknown';

            if (!contacts[recipientEmail]) {
                contacts[recipientEmail] = {
                    name: recipientName,
                    total_opens: 0,
                    total_clicks: 0,
                    emails: {}
                };
            }
            contacts[recipientEmail].total_opens += events.length;
        }
    }

    // 解析旧的 clicks
    for (const [emailId, events] of Object.entries(oldData.clicks || {})) {
        const parts = emailId.split('_');
        if (parts.length >= 5) {
            const emailPart = parts[3] || '';
            const recipientEmail = emailPart.replace('-at-', '@').replace(/-/g, '.');
            const recipientName = parts.slice(4).join('_') || 'Unknown';

            if (!contacts[recipientEmail]) {
                contacts[recipientEmail] = {
                    name: recipientName,
                    total_opens: 0,
                    total_clicks: 0,
                    emails: {}
                };
            }
            contacts[recipientEmail].total_clicks += events.length;
        }
    }

    return { contacts };
}

module.exports = async (req, res) => {
    // CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');

    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    const result = await loadData();
    let data = result.data;

    // 如果是旧格式，转换展示
    if (result.version === 'v1') {
        data = convertOldToNew(data);
    }

    const { email, format } = req.query;

    // 查询特定收件人
    if (email && data.contacts[email]) {
        return res.json({
            email: email,
            ...data.contacts[email]
        });
    }

    // 友好格式输出 - 按收件人列表
    if (format === 'friendly') {
        const recipients = Object.entries(data.contacts || {}).map(([email, info]) => ({
            email: email,
            name: info.name,
            total_opens: info.total_opens || 0,
            total_clicks: info.total_clicks || 0,
            first_contact: info.first_contact || null,
            last_activity: info.last_activity || null,
            opened: (info.total_opens || 0) > 0,
            clicked: (info.total_clicks || 0) > 0,
            emails_count: Object.keys(info.emails || {}).length
        }));

        // 按最后活动时间排序
        recipients.sort((a, b) => {
            if (!a.last_activity) return 1;
            if (!b.last_activity) return -1;
            return new Date(b.last_activity) - new Date(a.last_activity);
        });

        const totalOpens = recipients.reduce((sum, r) => sum + r.total_opens, 0);
        const totalClicks = recipients.reduce((sum, r) => sum + r.total_clicks, 0);
        const openedCount = recipients.filter(r => r.opened).length;
        const clickedCount = recipients.filter(r => r.clicked).length;

        return res.json({
            total_contacts: recipients.length,
            opened_count: openedCount,
            clicked_count: clickedCount,
            total_opens: totalOpens,
            total_clicks: totalClicks,
            open_rate: recipients.length > 0 ? ((openedCount / recipients.length) * 100).toFixed(1) + '%' : '0%',
            recipients: recipients,
            storage: 'redis',
            data_version: result.version
        });
    }

    // 原始数据
    res.json({
        contacts: data.contacts,
        storage: 'redis',
        data_version: result.version
    });
};
