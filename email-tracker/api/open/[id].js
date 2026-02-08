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

// 检测 Bot/预加载 User-Agent
// 返回: { isBot: boolean, botType: string|null }
function detectBot(userAgent) {
    if (!userAgent) return { isBot: false, botType: null };

    const ua = userAgent.toLowerCase();

    // Apple Mail Privacy Protection (iOS 15+)
    if (ua.includes('apple') && ua.includes('mail') && ua.includes('privacy')) {
        return { isBot: true, botType: 'Apple Mail Privacy' };
    }

    // iOS 预加载 (Apple 的代理服务器)
    if (ua.includes('proxy') || ua.includes('pre-fetch') || ua.includes('prefetch')) {
        return { isBot: true, botType: 'Prefetch Proxy' };
    }

    // Google 图片代理
    if (ua.includes('googleimageproxy') || ua.includes('google-proxy')) {
        return { isBot: true, botType: 'Google Image Proxy' };
    }

    // 已知的邮件预览 Bot
    const botPatterns = [
        { pattern: 'yahoo! slurp', type: 'Yahoo Bot' },
        { pattern: 'bingpreview', type: 'Bing Preview' },
        { pattern: 'facebookexternalhit', type: 'Facebook Bot' },
        { pattern: 'twitterbot', type: 'Twitter Bot' },
        { pattern: 'linkedinbot', type: 'LinkedIn Bot' },
        { pattern: 'slackbot', type: 'Slack Bot' },
        { pattern: 'whatsapp', type: 'WhatsApp Bot' },
        { pattern: 'telegrambot', type: 'Telegram Bot' },
        { pattern: 'crawl', type: 'Crawler' },
        { pattern: 'spider', type: 'Spider' },
        { pattern: 'bot/', type: 'Generic Bot' },
        { pattern: 'bot;', type: 'Generic Bot' },
    ];

    for (const { pattern, type } of botPatterns) {
        if (ua.includes(pattern)) {
            return { isBot: true, botType: type };
        }
    }

    // Outlook 预览 (通常没有完整的浏览器 UA)
    if (!ua.includes('mozilla') && !ua.includes('chrome') && !ua.includes('safari') && !ua.includes('firefox')) {
        // 太短或太奇怪的 UA 可能是 Bot
        if (ua.length < 30) {
            return { isBot: true, botType: 'Suspicious UA' };
        }
    }

    return { isBot: false, botType: null };
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

    if (!id) {
        res.setHeader('Content-Type', 'image/png');
        res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
        return res.send(TRANSPARENT_PIXEL);
    }

    const parsed = parseEmailId(id);

    if (!parsed || !parsed.recipientEmail) {
        res.setHeader('Content-Type', 'image/png');
        res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
        return res.send(TRANSPARENT_PIXEL);
    }

    // 检测 Bot
    const userAgent = req.headers['user-agent'] || 'unknown';
    const { isBot, botType } = detectBot(userAgent);

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
                total_bot_opens: 0,  // 新增：Bot 打开计数
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

        // 添加打开事件（包含 Bot 标记）
        data.contacts[email].emails[parsed.emailKey].opens.push({
            timestamp: now,
            ip: req.headers['x-forwarded-for'] || req.connection?.remoteAddress || 'unknown',
            userAgent: userAgent,
            isBot: isBot,
            botType: botType
        });

        // 更新汇总统计
        data.contacts[email].total_opens += 1;
        if (isBot) {
            data.contacts[email].total_bot_opens = (data.contacts[email].total_bot_opens || 0) + 1;
        }
        data.contacts[email].last_activity = now;

        await saveData(data);
        console.log(`[OPEN] ${email} - Bot: ${isBot ? botType : 'No'} at ${now}`);
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
