const { Redis } = require('@upstash/redis');

module.exports = async (req, res) => {
    // CORS
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS');

    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    const { key } = req.query;

    // 安全检查
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
        // 删除新旧两种格式的数据
        await redis.del('tracking_data');     // 旧格式
        await redis.del('tracking_data_v2');  // 新格式

        return res.status(200).json({
            success: true,
            message: 'All tracking data (v1 and v2) has been wiped.'
        });
    } catch (error) {
        return res.status(500).json({ error: error.message });
    }
};
