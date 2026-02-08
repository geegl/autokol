// 点击追踪 - 记录点击后重定向到目标 URL
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

let memoryStore = { contacts: {} };

async function loadData() {
    if (redis) {
        try {
            const data = await redis.get('tracking_data_v2');
            return data || { contacts: {} };
        } catch (e) {
            console.error('Redis load error:', e);
        }
    }
    return memoryStore;
}

async function saveData(data) {
    if (redis) {
        try {
            await redis.set('tracking_data_v2', data);
            return;
        } catch (e) {
            console.error('Redis save error:', e);
        }
    }
    memoryStore = data;
}

// 从 email_id 解析收件人信息
function parseEmailId(emailId) {
    const parts = emailId.split('_');
    if (parts.length >= 5) {
        const emailPart = parts[3] || '';
        const recipientEmail = emailPart.replace('-at-', '@').replace(/-/g, '.');
        const recipientName = parts.slice(4).join('_') || 'Unknown';
        return {
            mode: parts[0],
            index: parts[1],
            timestamp: parts[2],
            recipientEmail: recipientEmail,
            recipientName: recipientName,
            emailKey: `${parts[0]}_${parts[1]}_${parts[2]}`
        };
    }
    return null;
}

module.exports = async (req, res) => {
    const id = req.query.id;
    const targetUrl = req.query.url;

    if (!targetUrl) {
        return res.status(400).send('Missing url parameter');
    }

    // 解析 email_id
    const parsed = id ? parseEmailId(id) : null;

    // 记录点击事件 - 按收件人聚合
    if (parsed && parsed.recipientEmail) {
        try {
            const data = await loadData();
            const email = parsed.recipientEmail;
            const now = new Date().toISOString();

            // 初始化收件人记录
            if (!data.contacts[email]) {
                data.contacts[email] = {
                    name: parsed.recipientName,
                    total_opens: 0,
                    total_clicks: 0,
                    first_contact: now,
                    last_activity: now,
                    emails: {}
                };
            }

            // 初始化该邮件的记录
            if (!data.contacts[email].emails[parsed.emailKey]) {
                data.contacts[email].emails[parsed.emailKey] = {
                    mode: parsed.mode,
                    opens: [],
                    clicks: []
                };
            }

            // 添加点击事件
            data.contacts[email].emails[parsed.emailKey].clicks.push({
                timestamp: now,
                url: targetUrl,
                ip: req.headers['x-forwarded-for'] || req.connection?.remoteAddress || 'unknown',
                userAgent: req.headers['user-agent'] || 'unknown'
            });

            // 更新汇总统计
            data.contacts[email].total_clicks += 1;
            data.contacts[email].last_activity = now;

            await saveData(data);
            console.log(`[CLICK] ${email} clicked ${targetUrl} at ${now}`);
        } catch (error) {
            console.error('Tracking error:', error);
        }
    }

    // 302 重定向到目标 URL
    res.redirect(302, targetUrl);
};
