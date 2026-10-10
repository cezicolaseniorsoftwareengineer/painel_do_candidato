import bcrypt from 'bcryptjs';
import { db, json, newToken, hashToken, cookie, parseJson } from './_auth.js';

export const handler = async (event) => {
  if ((event.httpMethod || event.method) !== 'POST') return json(405, { error: 'method_not_allowed' });
  const input = event.body === undefined ? await event.json().catch(() => null) : parseJson(event);
  const email = input?.email?.trim().toLowerCase();
  if (!email || typeof input.password !== 'string') return json(400, { error: 'email_password_required' });
  const sql = db();
  const result = await sql`SELECT id, name, email, role, password_hash FROM app_users WHERE email = ${email} AND disabled_at IS NULL LIMIT 1`;
  const user = result?.[0];
  if (!user || !(await bcrypt.compare(input.password, user.password_hash))) return json(401, { error: 'invalid_credentials' });
  const token = newToken();
  await sql`INSERT INTO auth_sessions(user_id, token_hash, expires_at) VALUES (${user.id}, ${hashToken(token)}, NOW() + INTERVAL '30 days')`;
  await sql`UPDATE app_users SET last_login_at = NOW() WHERE id = ${user.id}`;
  delete user.password_hash;
  return json(200, { user }, { 'set-cookie': cookie('mv_session', token, 2592000) });
};
