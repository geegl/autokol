// 1x1 透明 PNG 像素 (追踪邮件打开)
const TRANSPARENT_PIXEL = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
    'base64'
);

// 简单的内存存储 (生产环境用 Vercel KV)
// 数据存储在 /tmp 目录,重启后丢失,正式环境需要 KV
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
    // 获取追踪 ID
    const { id } = req.query;

    if (!id) {
        res.setHeader('Content-Type', 'image/png');
        res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
        return res.send(TRANSPARENT_PIXEL);
    }

    // 记录打开事件
    const data = loadData();
    if (!data.opens[id]) {
        data.opens[id] = [];
    }
    data.opens[id].push({
        timestamp: new Date().toISOString(),
        ip: req.headers['x-forwarded-for'] || req.connection?.remoteAddress || 'unknown',
        userAgent: req.headers['user-agent'] || 'unknown'
    });
    saveData(data);

    console.log(`[OPEN] Email ${id} opened at ${new Date().toISOString()}`);

    // 返回透明像素
    res.setHeader('Content-Type', 'image/png');
    res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
    res.setHeader('Pragma', 'no-cache');
    res.setHeader('Expires', '0');
    res.send(TRANSPARENT_PIXEL);
};
