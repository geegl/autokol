// 查询追踪统计数据
const fs = require('fs');
const DATA_FILE = '/tmp/tracking_data.json';

function loadData() {
    try {
        if (fs.existsSync(DATA_FILE)) {
            return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
        }
    } catch (e) { }
    return { opens: {}, clicks: {} };
}

module.exports = async (req, res) => {
    // 简单的 API Key 验证 (可选)
    const apiKey = req.headers['x-api-key'] || req.query.key;
    const expectedKey = process.env.TRACKER_API_KEY;

    if (expectedKey && apiKey !== expectedKey) {
        return res.status(401).json({ error: 'Unauthorized' });
    }

    const data = loadData();
    const { id } = req.query;

    // 查询特定邮件的追踪数据
    if (id) {
        return res.json({
            email_id: id,
            opens: data.opens[id] || [],
            clicks: data.clicks[id] || [],
            open_count: (data.opens[id] || []).length,
            click_count: (data.clicks[id] || []).length
        });
    }

    // 返回汇总统计
    const summary = {
        total_emails_opened: Object.keys(data.opens).length,
        total_opens: Object.values(data.opens).reduce((sum, arr) => sum + arr.length, 0),
        total_emails_clicked: Object.keys(data.clicks).length,
        total_clicks: Object.values(data.clicks).reduce((sum, arr) => sum + arr.length, 0),
        recent_opens: Object.entries(data.opens)
            .flatMap(([id, events]) => events.map(e => ({ id, ...e })))
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
            .slice(0, 20),
        recent_clicks: Object.entries(data.clicks)
            .flatMap(([id, events]) => events.map(e => ({ id, ...e })))
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
            .slice(0, 20)
    };

    res.json(summary);
};
