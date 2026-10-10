import bcrypt from 'bcryptjs';
import { currentUser, db, json } from './_auth.js';

const forbidden = () => json(403, { error: 'admin_only' });
const bodyOf = async event => typeof event.json === 'function' ? await event.json().catch(() => ({})) : JSON.parse(event.body || '{}');

export const handler = async event => {
  if ((event.httpMethod || event.method) !== 'GET' && (event.httpMethod || event.method) !== 'POST' && (event.httpMethod || event.method) !== 'PATCH' && (event.httpMethod || event.method) !== 'DELETE') return json(405, { error: 'method_not_allowed' });
  const actor = await currentUser(event);
  if (!actor || actor.role !== 'admin') return forbidden();
  const sql = db();
  const input = await bodyOf(event);
  if ((event.httpMethod || event.method) === 'GET') {
    const users = await sql`SELECT u.id,u.name,u.email,u.role,u.created_at,u.last_login_at,u.disabled_at,
      COALESCE((SELECT json_agg(g ORDER BY g.created_at DESC) FROM access_grants g WHERE g.user_id=u.id),'[]') AS grants
      FROM app_users u ORDER BY u.created_at DESC LIMIT 1000`;
    const payments = await sql`SELECT event_name,payment_id,received_at,processed_at FROM asaas_webhook_events ORDER BY received_at DESC LIMIT 500`;
    return json(200, { users, payments });
  }
  if ((event.httpMethod || event.method) === 'POST') {
    if (!input.name || !input.email || !input.password || input.password.length < 10) return json(400, { error: 'name_email_password_required' });
    const hash = await bcrypt.hash(input.password, 12);
    const users = await sql`INSERT INTO app_users(name,email,password_hash,role) VALUES (${input.name.trim()},${input.email.trim().toLowerCase()},${hash},${input.role === 'admin' ? 'admin' : 'user'}) RETURNING id,name,email,role,created_at`;
    return json(201, { user: users[0] });
  }
  if (!input.userId) return json(400, { error: 'user_id_required' });
  if ((event.httpMethod || event.method) === 'DELETE') { await sql`DELETE FROM app_users WHERE id=${input.userId}`; return json(200, { ok: true }); }
  if (input.action === 'revoke') await sql`UPDATE access_grants SET status='revoked' WHERE user_id=${input.userId} AND status='active'`;
  if (input.action === 'lifetime') await sql`INSERT INTO access_grants(user_id,grant_type,starts_at,expires_at) VALUES (${input.userId},'lifetime',NOW(),NULL)`;
  if (input.action === 'year') await sql`INSERT INTO access_grants(user_id,grant_type,starts_at,expires_at) VALUES (${input.userId},'paid',NOW(),NOW()+INTERVAL '365 days')`;
  if (input.action === 'disable') await sql`UPDATE app_users SET disabled_at=NOW() WHERE id=${input.userId}`;
  if (input.action === 'enable') await sql`UPDATE app_users SET disabled_at=NULL WHERE id=${input.userId}`;
  if (input.name || input.email) await sql`UPDATE app_users SET name=COALESCE(${input.name || null},name),email=COALESCE(${input.email?.trim().toLowerCase() || null},email) WHERE id=${input.userId}`;
  return json(200, { ok: true });
};
