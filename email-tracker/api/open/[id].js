// 1x1 透明 PNG 像素 (追踪邮件打开)
const TRANSPARENT_PIXEL = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
    'base64'
);

// 使用环境变量的 Upstash Redis（需要在 Vercel 配置）
// 如果没有配置，使用内存存储（仅用于测试）
let memoryStore = { opens: {}, clicks: {} };

async function getRedisClient() {
    if (process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN) {
        const { Redis } = require('@upstash/redis');
        return new Redis({
            url: process.env.UPSTASH_REDIS_REST_URL,
            token: process.env.UPSTASH_REDIS_REST_TOKEN,
        });
    }
    return null;
}

async function loadData() {
    try {
        const redis = await getRedisClient();
        if (redis) {
            const data = await redis.get('tracking_data');
            return data || { opens: {}, clicks: {} };
        }
    } catch (e) {
        console.error('Redis load error:', e);
    }
    return memoryStore;
}

async function saveData(data) {
    try {
        const redis = await getRedisClient();
        if (redis) {
            await redis.set('tracking_data', data);
            return;
        }
    } catch (e) {
        console.error('Redis save error:', e);
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

    // 返回透明像素
    res.setHeader('Content-Type', 'image/png');
    res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
    res.setHeader('Pragma', 'no-cache');
    res.setHeader('Expires', '0');
    res.send(TRANSPARENT_PIXEL);
};
