// 1x1 透明 PNG 像素 (追踪邮件打开)
const TRANSPARENT_PIXEL = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
    'base64'
);

// Redis 客户端
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

// 默认数据结构 - 以收件人为中心
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
// 格式: mode_index_timestamp_recipientEmail_recipientName
function parseEmailId(emailId) {
    const parts = emailId.split('_');
    if (parts.length >= 5) {
        // 收件人邮箱格式: xxx-at-domain-com
        const emailPart = parts[3] || '';
        const recipientEmail = emailPart.replace('-at-', '@').replace(/-/g, '.');
        const recipientName = parts.slice(4).join('_') || 'Unknown';
        return {
            mode: parts[0],
            index: parts[1],
            timestamp: parts[2],
            recipientEmail: recipientEmail,
            recipientName: recipientName,
            // 唯一邮件 ID (不含收件人信息，用于聚合)
            emailKey: `${parts[0]}_${parts[1]}_${parts[2]}`
        };
    }
    return null;
}

module.exports = async (req, res) => {
    // 获取追踪 ID
    const id = req.query.id;

    if (!id) {
        res.setHeader('Content-Type', 'image/png');
        res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
        return res.send(TRANSPARENT_PIXEL);
    }

    // 解析 email_id
    const parsed = parseEmailId(id);

    if (!parsed || !parsed.recipientEmail) {
        // 无法解析，跳过记录
        res.setHeader('Content-Type', 'image/png');
        res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
        return res.send(TRANSPARENT_PIXEL);
    }

    // 记录打开事件 - 按收件人聚合
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

        // 添加打开事件
        data.contacts[email].emails[parsed.emailKey].opens.push({
            timestamp: now,
            ip: req.headers['x-forwarded-for'] || req.connection?.remoteAddress || 'unknown',
            userAgent: req.headers['user-agent'] || 'unknown'
        });

        // 更新汇总统计
        data.contacts[email].total_opens += 1;
        data.contacts[email].last_activity = now;

        await saveData(data);
        console.log(`[OPEN] ${email} (${parsed.recipientName}) opened email at ${now}`);
    } catch (error) {
        console.error('Tracking error:', error);
    }

    // 返回透明像素
    res.setHeader('Content-Type', 'image/png');
    res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
    res.setHeader('Pragma', 'no-cache');
    res.setHeader('Expires', '0');
    res.send(TRANSPARENT_PIXEL);
};
