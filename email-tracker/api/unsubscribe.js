const crypto = require('crypto');
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

const SECRET_KEY = process.env.UNSUBSCRIBE_SECRET_KEY || '';

function normalizeEmail(email) {
    return (email || '').trim().toLowerCase();
}

function verifyToken(email, token) {
    if (!SECRET_KEY) return false;
    const normalized = normalizeEmail(email);
    const expected = crypto.createHmac('sha256', SECRET_KEY).update(normalized).digest('hex');
    try {
        return crypto.timingSafeEqual(Buffer.from(expected, 'hex'), Buffer.from(token, 'hex'));
    } catch {
        return false;
    }
}

function decodeEmail(encoded) {
    try {
        return Buffer.from(encoded, 'base64url').toString('utf-8');
    } catch {
        try {
            return Buffer.from(encoded, 'base64').toString('utf-8');
        } catch {
            return null;
        }
    }
}

function confirmationPage(email, success) {
    const status = success
        ? '<h2 style="color:#16a34a;">You have been unsubscribed</h2><p>We will no longer send emails to <b>' + email + '</b>.</p>'
        : '<h2 style="color:#16a34a;">Already unsubscribed</h2><p><b>' + email + '</b> is already on our suppression list.</p>';

    return `<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Unsubscribe - Utopai Studios</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#000;color:#fff;}
.card{background:#111;border-radius:12px;padding:48px;max-width:480px;text-align:center;border:1px solid #333;}
h2{margin-top:0;font-size:24px;}
p{color:#aaa;line-height:1.6;}
a{color:#60a5fa;text-decoration:none;}
</style></head><body>
<div class="card">
<img src="https://342866168.fs1.hubspotusercontent-na3.net/hubfs/342866168/newsletter%20fixed%20images/utopai_logo_new.png" alt="UTOPAI" width="120" style="margin-bottom:32px;">
${status}
<p style="margin-top:24px;font-size:14px;">If this was a mistake, please contact us at <a href="mailto:marketing@utopaistudios.com">marketing@utopaistudios.com</a></p>
</div></body></html>`;
}

function errorPage(message) {
    return `<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Error - Utopai Studios</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#000;color:#fff;}
.card{background:#111;border-radius:12px;padding:48px;max-width:480px;text-align:center;border:1px solid #333;}
h2{margin-top:0;color:#ef4444;}
p{color:#aaa;line-height:1.6;}
</style></head><body>
<div class="card">
<h2>Invalid Request</h2>
<p>${message}</p>
</div></body></html>`;
}

module.exports = async (req, res) => {
    const { email: encodedEmail, token } = req.query;

    if (!encodedEmail || !token) {
        res.status(400).send(errorPage('Missing email or token parameter.'));
        return;
    }

    const email = decodeEmail(encodedEmail);
    if (!email || !email.includes('@')) {
        res.status(400).send(errorPage('Invalid email parameter.'));
        return;
    }

    const normalized = normalizeEmail(email);

    if (!verifyToken(normalized, token)) {
        res.status(403).send(errorPage('Invalid or expired unsubscribe link.'));
        return;
    }

    // GET: show confirmation page (do not unsubscribe yet)
    if (req.method === 'GET') {
        // Check if already unsubscribed
        let alreadyUnsubscribed = false;
        if (redis) {
            try {
                alreadyUnsubscribed = await redis.sismember('unsubscribe_set', normalized);
            } catch (e) {
                console.error('Redis check error:', e);
            }
        }

        res.setHeader('Content-Type', 'text/html; charset=utf-8');
        res.send(`<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Unsubscribe - Utopai Studios</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#000;color:#fff;}
.card{background:#111;border-radius:12px;padding:48px;max-width:480px;text-align:center;border:1px solid #333;}
h2{margin-top:0;font-size:24px;}
p{color:#aaa;line-height:1.6;}
button{background:#fff;color:#000;border:none;padding:14px 32px;border-radius:8px;font-size:16px;font-weight:500;cursor:pointer;margin-top:16px;}
button:hover{background:#e5e5e5;}
a{color:#60a5fa;text-decoration:none;font-size:14px;}
</style></head><body>
<div class="card">
<img src="https://342866168.fs1.hubspotusercontent-na3.net/hubfs/342866168/newsletter%20fixed%20images/utopai_logo_new.png" alt="UTOPAI" width="120" style="margin-bottom:32px;">
${alreadyUnsubscribed
    ? '<h2 style="color:#16a34a;">Already unsubscribed</h2><p><b>' + email + '</b> is already on our suppression list.</p>'
    : '<h2>Unsubscribe from our emails?</h2><p>We will stop sending emails to <b>' + email + '</b>.</p><form method="POST" action="/api/unsubscribe?email=' + encodeURIComponent(encodedEmail) + '&token=' + encodeURIComponent(token) + '"><button type="submit">Confirm Unsubscribe</button></form>'}
<p style="margin-top:24px;"><a href="mailto:marketing@utopaistudios.com">Contact us</a></p>
</div></body></html>`);
        return;
    }

    // POST: actually unsubscribe
    if (req.method === 'POST') {
        let alreadyUnsubscribed = false;
        if (redis) {
            try {
                alreadyUnsubscribed = await redis.sismember('unsubscribe_set', normalized);
                if (!alreadyUnsubscribed) {
                    await redis.sadd('unsubscribe_set', normalized);
                    // Also mark in tracking data
                    const data = await redis.get('tracking_data_v2');
                    if (data && data.contacts && data.contacts[normalized]) {
                        data.contacts[normalized].unsubscribed = true;
                        data.contacts[normalized].unsubscribed_at = new Date().toISOString();
                        await redis.set('tracking_data_v2', data);
                    }
                }
                console.log(`[UNSUBSCRIBE] ${normalized} at ${new Date().toISOString()}`);
            } catch (e) {
                console.error('Redis unsubscribe error:', e);
                res.status(500).send(errorPage('An error occurred. Please try again later.'));
                return;
            }
        }

        res.setHeader('Content-Type', 'text/html; charset=utf-8');
        res.send(confirmationPage(email, !alreadyUnsubscribed));
        return;
    }

    res.status(405).send(errorPage('Method not allowed.'));
};
