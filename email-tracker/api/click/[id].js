// 点击追踪 - 记录点击后重定向到目标 URL
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

function saveData(data) {
    try {
        fs.writeFileSync(DATA_FILE, JSON.stringify(data));
    } catch (e) { }
}

module.exports = async (req, res) => {
    const { id } = req.query;
    const targetUrl = req.query.url;

    if (!targetUrl) {
        return res.status(400).send('Missing url parameter');
    }

    // 记录点击事件
    if (id) {
        const data = loadData();
        if (!data.clicks[id]) {
            data.clicks[id] = [];
        }
        data.clicks[id].push({
            timestamp: new Date().toISOString(),
            url: targetUrl,
            ip: req.headers['x-forwarded-for'] || req.connection?.remoteAddress || 'unknown',
            userAgent: req.headers['user-agent'] || 'unknown'
        });
        saveData(data);

        console.log(`[CLICK] Email ${id} clicked ${targetUrl} at ${new Date().toISOString()}`);
    }

    // 302 重定向到目标 URL
    res.redirect(302, targetUrl);
};
