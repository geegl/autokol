// 进度持久化 API - 保存和加载进度数据
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

module.exports = async (req, res) => {
    // CORS
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    // API Key 认证
    const apiKey = req.headers['x-api-key'] || req.query.key;
    const expectedKey = process.env.PROGRESS_API_KEY;

    if (expectedKey && apiKey !== expectedKey) {
        return res.status(401).json({ error: 'Unauthorized: Invalid API key' });
    }

    if (!redis) {
        return res.status(500).json({ error: 'Redis not configured' });
    }

    const { mode, action } = req.query;

    if (!mode || !['B2B', 'B2C'].includes(mode)) {
        return res.status(400).json({ error: 'Invalid mode. Must be B2B or B2C' });
    }

    const key = `progress_${mode}`;

    try {
        // GET - 加载进度
        if (req.method === 'GET') {
            const data = await redis.get(key);
            if (data) {
                return res.json({
                    success: true,
                    data: data,
                    timestamp: new Date().toISOString()
                });
            } else {
                return res.json({
                    success: true,
                    data: null,
                    message: 'No progress data found'
                });
            }
        }

        // POST - 保存进度
        if (req.method === 'POST') {
            let body = req.body;

            // 如果 body 是字符串，解析它
            if (typeof body === 'string') {
                try {
                    body = JSON.parse(body);
                } catch (e) {
                    return res.status(400).json({ error: 'Invalid JSON body' });
                }
            }

            if (!body || !body.data) {
                return res.status(400).json({ error: 'Missing data in request body' });
            }

            // 保存数据，包含时间戳
            const saveData = {
                data: body.data,
                updated_at: new Date().toISOString(),
                row_count: Array.isArray(body.data) ? body.data.length : 0
            };

            await redis.set(key, saveData);

            return res.json({
                success: true,
                message: `Progress saved for ${mode}`,
                row_count: saveData.row_count,
                timestamp: saveData.updated_at
            });
        }

        // DELETE - 清除进度
        if (req.method === 'DELETE') {
            await redis.del(key);
            return res.json({
                success: true,
                message: `Progress cleared for ${mode}`
            });
        }

        return res.status(405).json({ error: 'Method not allowed' });

    } catch (error) {
        console.error('Progress API error:', error);
        return res.status(500).json({ error: error.message });
    }
};
