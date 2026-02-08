// 点击追踪 - 记录点击后重定向到目标 URL

// 使用环境变量的 Upstash Redis
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
    const id = req.query.id;
    const targetUrl = req.query.url;

    if (!targetUrl) {
        return res.status(400).send('Missing url parameter');
    }

    // 记录点击事件
    if (id) {
        const data = await loadData();
        if (!data.clicks[id]) {
            data.clicks[id] = [];
        }
        data.clicks[id].push({
            timestamp: new Date().toISOString(),
            url: targetUrl,
            ip: req.headers['x-forwarded-for'] || req.connection?.remoteAddress || 'unknown',
            userAgent: req.headers['user-agent'] || 'unknown'
        });
        await saveData(data);

        console.log(`[CLICK] Email ${id} clicked ${targetUrl} at ${new Date().toISOString()}`);
    }

    // 302 重定向到目标 URL
    res.redirect(302, targetUrl);
};
