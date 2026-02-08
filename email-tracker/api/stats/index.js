// 查询追踪统计数据 - 按收件人聚合，区分真实打开和 Bot 打开
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

async function loadData() {
    if (redis) {
        try {
            const data = await redis.get('tracking_data_v2');
            if (data) return { version: 'v2', data, storage: 'redis' };

            const oldData = await redis.get('tracking_data');
            if (oldData) return { version: 'v1', data: oldData, storage: 'redis' };

            // Redis 连接正常但没有数据
            return { version: 'v2', data: { contacts: {} }, storage: 'redis' };
        } catch (e) {
            console.error('Redis load error:', e);
            // Redis 连接失败，回退到内存
            return { version: 'v2', data: { contacts: {} }, storage: 'memory (redis error)' };
        }
    }
    // Redis 未配置
    return { version: 'v2', data: { contacts: {} }, storage: 'memory (no redis)' };
}

// 将旧格式数据转换为新格式
function convertOldToNew(oldData) {
    const contacts = {};

    for (const [emailId, events] of Object.entries(oldData.opens || {})) {
        const parts = emailId.split('_');
        if (parts.length >= 5) {
            const emailPart = parts[3] || '';
            const recipientEmail = emailPart.replace('-at-', '@').replace(/-/g, '.');
            const recipientName = parts.slice(4).join('_') || 'Unknown';

            if (!contacts[recipientEmail]) {
                contacts[recipientEmail] = {
                    name: recipientName,
                    total_opens: 0,
                    total_bot_opens: 0,
                    total_clicks: 0,
                    emails: {}
                };
            }
            contacts[recipientEmail].total_opens += events.length;
        }
    }

    for (const [emailId, events] of Object.entries(oldData.clicks || {})) {
        const parts = emailId.split('_');
        if (parts.length >= 5) {
            const emailPart = parts[3] || '';
            const recipientEmail = emailPart.replace('-at-', '@').replace(/-/g, '.');
            const recipientName = parts.slice(4).join('_') || 'Unknown';

            if (!contacts[recipientEmail]) {
                contacts[recipientEmail] = {
                    name: recipientName,
                    total_opens: 0,
                    total_bot_opens: 0,
                    total_clicks: 0,
                    emails: {}
                };
            }
            contacts[recipientEmail].total_clicks += events.length;
        }
    }

    return { contacts };
}

// 分析收件人数据，计算真实打开和 Bot 打开
function analyzeContact(info) {
    let humanOpens = 0;
    let botOpens = 0;
    let botTypes = [];

    // 遍历所有邮件的打开记录
    for (const emailData of Object.values(info.emails || {})) {
        for (const open of (emailData.opens || [])) {
            if (open.isBot) {
                botOpens++;
                if (open.botType && !botTypes.includes(open.botType)) {
                    botTypes.push(open.botType);
                }
            } else {
                humanOpens++;
            }
        }
    }

    // 如果没有详细数据，使用汇总数据
    if (humanOpens === 0 && botOpens === 0) {
        humanOpens = (info.total_opens || 0) - (info.total_bot_opens || 0);
        botOpens = info.total_bot_opens || 0;
    }

    return {
        human_opens: humanOpens,
        bot_opens: botOpens,
        bot_types: botTypes
    };
}

module.exports = async (req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');

    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    const result = await loadData();
    let data = result.data;

    if (result.version === 'v1') {
        data = convertOldToNew(data);
    }

    const { email, format } = req.query;

    // 查询特定收件人
    if (email && data.contacts[email]) {
        const info = data.contacts[email];
        const analysis = analyzeContact(info);
        return res.json({
            email: email,
            ...info,
            ...analysis
        });
    }

    // 友好格式输出
    if (format === 'friendly') {
        const recipients = Object.entries(data.contacts || {}).map(([email, info]) => {
            const analysis = analyzeContact(info);
            const totalClicks = info.total_clicks || 0;

            // 确认阅读 = 有真实打开 + 有点击
            const confirmedRead = analysis.human_opens > 0 && totalClicks > 0;
            // 可能预加载 = 只有打开没有点击，或者只有 Bot 打开
            const possiblePreload = !confirmedRead && (info.total_opens || 0) > 0;

            return {
                email: email,
                name: info.name,
                total_opens: info.total_opens || 0,
                human_opens: analysis.human_opens,
                bot_opens: analysis.bot_opens,
                bot_types: analysis.bot_types,
                total_clicks: totalClicks,
                first_contact: info.first_contact || null,
                last_activity: info.last_activity || null,
                // 阅读状态分类
                confirmed_read: confirmedRead,        // 确认阅读（有点击）
                possible_preload: possiblePreload,    // 可能预加载（无点击）
                // 兼容旧字段
                opened: (info.total_opens || 0) > 0,
                clicked: totalClicks > 0,
                emails_count: Object.keys(info.emails || {}).length
            };
        });

        // 按最后活动时间排序
        recipients.sort((a, b) => {
            if (!a.last_activity) return 1;
            if (!b.last_activity) return -1;
            return new Date(b.last_activity) - new Date(a.last_activity);
        });

        // 统计
        const totalOpens = recipients.reduce((sum, r) => sum + r.total_opens, 0);
        const totalHumanOpens = recipients.reduce((sum, r) => sum + r.human_opens, 0);
        const totalBotOpens = recipients.reduce((sum, r) => sum + r.bot_opens, 0);
        const totalClicks = recipients.reduce((sum, r) => sum + r.total_clicks, 0);

        const confirmedCount = recipients.filter(r => r.confirmed_read).length;
        const possiblePreloadCount = recipients.filter(r => r.possible_preload).length;
        const notOpenedCount = recipients.filter(r => !r.opened).length;

        return res.json({
            total_contacts: recipients.length,
            // 阅读统计（新）
            confirmed_reads: confirmedCount,           // 确认阅读数
            possible_preloads: possiblePreloadCount,   // 可能预加载数
            not_opened: notOpenedCount,                // 未打开数
            // 详细统计
            total_opens: totalOpens,
            human_opens: totalHumanOpens,
            bot_opens: totalBotOpens,
            total_clicks: totalClicks,
            // 打开率（基于确认阅读）
            confirmed_rate: recipients.length > 0 ? ((confirmedCount / recipients.length) * 100).toFixed(1) + '%' : '0%',
            open_rate: recipients.length > 0 ? ((recipients.filter(r => r.opened).length / recipients.length) * 100).toFixed(1) + '%' : '0%',
            // 收件人列表
            recipients: recipients,
            storage: result.storage,
            data_version: result.version
        });
    }

    // 原始数据
    res.json({
        contacts: data.contacts,
        storage: result.storage,
        data_version: result.version
    });
};
