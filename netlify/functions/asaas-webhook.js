import crypto from 'node:crypto';
import { db, json, requiredEnv } from './_auth.js';

export const handler = async (event) => {
  if ((event.httpMethod || event.method) !== 'POST') return json(405, { error: 'method_not_allowed' });
  const expected = requiredEnv('ASAAS_WEBHOOK_TOKEN');
  const received = event.headers?.get ? event.headers.get('asaas-access-token') : (event.headers?.['asaas-access-token'] || event.headers?.['Asaas-Access-Token']);
  const receivedBuffer = Buffer.from(received || '');
  const expectedBuffer = Buffer.from(expected);
  if (!received || receivedBuffer.length !== expectedBuffer.length || !crypto.timingSafeEqual(receivedBuffer, expectedBuffer)) return json(401, { error: 'invalid_webhook_token' });
  let payload;
  try { payload = event.body === undefined ? await event.json() : JSON.parse(event.body || '{}'); } catch { return json(400, { error: 'invalid_json' }); }
  if (!payload.id || !payload.event) return json(400, { error: 'invalid_event' });
  const sql = db();
  const payment = payload.payment || {};
  const payloadHash = crypto.createHash('sha256').update(JSON.stringify(payload)).digest('hex');
  const inserted = await sql`INSERT INTO asaas_webhook_events(event_id, event_name, payment_id, payload_hash) VALUES (${payload.id}, ${payload.event}, ${payment.id || null}, ${payloadHash}) ON CONFLICT (event_id) DO NOTHING RETURNING event_id`;
  if (!inserted.rows?.length) return json(200, { ok: true, duplicate: true });
  if (['PAYMENT_CONFIRMED', 'PAYMENT_RECEIVED'].includes(payload.event) && payment.externalReference) {
    await sql`INSERT INTO access_grants(user_id, grant_type, starts_at, expires_at, asaas_customer_id, asaas_payment_id)
      SELECT ${payment.externalReference}::uuid, 'paid', NOW(), NOW() + INTERVAL '365 days', ${payment.customer || null}, ${payment.id || null}
      WHERE EXISTS (SELECT 1 FROM app_users WHERE id = ${payment.externalReference}::uuid)
        AND NOT EXISTS (SELECT 1 FROM access_grants WHERE asaas_payment_id = ${payment.id || null})`;
  }
  await sql`UPDATE asaas_webhook_events SET status = 'processed', processed_at = NOW() WHERE event_id = ${payload.id}`;
  return json(200, { ok: true });
};
