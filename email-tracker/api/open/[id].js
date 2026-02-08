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

let memoryStore = { opens: {}, clicks: {} };

async function loadData() {
    if (redis) {
        try {
            const data = await redis.get('tracking_data');
            return data || { opens: {}, clicks: {} };
        } catch (e) {
            console.error('Redis load error:', e);
        }
    }
    return memoryStore;
}

async function saveData(data) {
    if (redis) {
        try {
            await redis.set('tracking_data', data);
            return;
        } catch (e) {
            console.error('Redis save error:', e);
        }
    }
    memoryStore = data;
}

module.exports = async (req, res) => {
    // 获取追踪 ID
    const id = req.query.id;

    if (!id) {
        res.setHeader('Content-Type', 'image/png');
        res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
        return res.send(TRANSPARENT_PIXEL);
    }

    // 记录打开事件
    try {
        const data = await loadData();
        if (!data.opens[id]) {
            data.opens[id] = [];
        }
        data.opens[id].push({
            timestamp: new Date().toISOString(),
            ip: req.headers['x-forwarded-for'] || req.connection?.remoteAddress || 'unknown',
            userAgent: req.headers['user-agent'] || 'unknown'
        });
        await saveData(data);
        console.log(`[OPEN] Email ${id} opened at ${new Date().toISOString()}`);
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
