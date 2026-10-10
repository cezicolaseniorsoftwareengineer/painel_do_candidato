import bcrypt from 'bcryptjs';
import { db, json, newToken, hashToken, cookie, parseJson, requiredEnv } from './_auth.js';

export const handler = async (event) => {
  if (event.httpMethod !== 'POST') return json(405, { error: 'method_not_allowed' });
  const input = parseJson(event);
  if (!input || typeof input.name !== 'string' || typeof input.email !== 'string' || typeof input.password !== 'string') return json(400, { error: 'name_email_password_required' });
  const name = input.name.trim().slice(0, 160);
  const email = input.email.trim().toLowerCase().slice(0, 320);
  if (name.length < 2 || !/^\S+@\S+\.\S+$/.test(email) || input.password.length < 10) return json(400, { error: 'invalid_registration' });
  const sql = db();
  const existing = await sql`SELECT id FROM app_users WHERE email = ${email} LIMIT 1`;
  if (existing.rows?.length) return json(409, { error: 'email_already_registered' });
  const passwordHash = await bcrypt.hash(input.password, 12);
  const user = await sql`INSERT INTO app_users(name, email, password_hash) VALUES (${name}, ${email}, ${passwordHash}) RETURNING id, name, email, role`;
  const userId = user.rows[0].id;
  await sql`INSERT INTO access_grants(user_id, grant_type, starts_at, expires_at) VALUES (${userId}, 'trial', NOW(), NOW() + INTERVAL '24 hours')`;
  const token = newToken();
  await sql`INSERT INTO auth_sessions(user_id, token_hash, expires_at) VALUES (${userId}, ${hashToken(token)}, NOW() + INTERVAL '30 days')`;
  requiredEnv('SESSION_SECRET');
  return json(201, { user: user.rows[0], access: { type: 'trial', expiresAt: new Date(Date.now() + 86400000).toISOString() } }, { 'set-cookie': cookie('mv_session', token, 2592000) });
};
