import crypto from 'node:crypto';
import { getDatabase } from '@netlify/database/dist/main.js';

export const db = () => getDatabase();

export function requiredEnv(name) {
  const value = process.env[name];
  if (!value) throw new Error(`Missing required environment variable: ${name}`);
  return value;
}

export function hashToken(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

export function newToken() {
  return crypto.randomBytes(32).toString('base64url');
}

export function json(statusCode, body, headers = {}) {
  const responseHeaders = new Headers({ 'content-type': 'application/json; charset=utf-8', ...headers });
  return new Response(JSON.stringify(body), { status: statusCode, headers: responseHeaders });
}

export function parseJson(event) {
  try { return JSON.parse(event.body || '{}'); } catch { return null; }
}

export function cookie(name, value, maxAge) {
  return `${name}=${value}; Max-Age=${maxAge}; Path=/; HttpOnly; Secure; SameSite=Lax`;
}

export function readCookie(event, name) {
  const raw = event.headers?.get ? (event.headers.get('cookie') || '') : (event.headers?.cookie || event.headers?.Cookie || '');
  const part = raw.split(';').map((item) => item.trim()).find((item) => item.startsWith(`${name}=`));
  return part ? decodeURIComponent(part.slice(name.length + 1)) : null;
}

export async function currentUser(event) {
  const token = readCookie(event, 'mv_session');
  if (!token) return null;
  const sql = db();
  const result = await sql`
    SELECT u.id, u.name, u.email, u.role, u.disabled_at,
           (SELECT MAX(g.expires_at) FROM access_grants g WHERE g.user_id = u.id AND g.status = 'active' AND (g.expires_at IS NULL OR g.expires_at > NOW())) AS access_expires_at,
           EXISTS (
             SELECT 1 FROM access_grants g
             WHERE g.user_id = u.id AND g.status = 'active'
               AND (g.expires_at IS NULL OR g.expires_at > NOW())
           ) AS has_access
    FROM auth_sessions s JOIN app_users u ON u.id = s.user_id
    WHERE s.token_hash = ${hashToken(token)} AND s.revoked_at IS NULL AND s.expires_at > NOW()
    LIMIT 1`;
  const user = result.rows?.[0];
  if (user && !user.disabled_at) {
    user.accessExpiresAt = user.access_expires_at;
    delete user.access_expires_at;
    return user;
  }
  return null;
}
