import { currentUser, db, json } from './_auth.js';

export default async (event) => {
  if (event.httpMethod !== 'GET') return json(405, { error: 'method_not_allowed' });
  const user = await currentUser(event);
  if (!user || user.role !== 'admin') return json(403, { error: 'admin_only' });
  const sql = db();
  const result = await sql`SELECT id, name, email, role, created_at, last_login_at, disabled_at FROM app_users ORDER BY created_at DESC LIMIT 500`;
  return json(200, { users: result.rows || [] });
};
