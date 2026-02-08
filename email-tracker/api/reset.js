const { Redis } = require('@upstash/redis');

module.exports = async (req, res) => {
    // CORS
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS');

    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    const { key } = req.query;

    // 安全检查 (你可以修改这个 key)
    if (key !== 'autokol_admin_reset') {
        return res.status(401).json({ error: 'Unauthorized: Invalid key' });
    }

    if (!process.env.UPSTASH_REDIS_REST_URL || !process.env.UPSTASH_REDIS_REST_TOKEN) {
        return res.status(500).json({ error: 'Redis credentials not configured' });
    }

    const redis = new Redis({
        url: process.env.UPSTASH_REDIS_REST_URL,
        token: process.env.UPSTASH_REDIS_REST_TOKEN,
    });

    try {
        // 数据存储在 'tracking_data' 这个 key 里
        await redis.del('tracking_data');

        return res.status(200).json({
            success: true,
            message: 'Target neutralized. Tracking data has been wiped from Redis.'
        });
    } catch (error) {
        return res.status(500).json({ error: error.message });
    }
};
