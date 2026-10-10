import { currentUser, json } from './_auth.js';

export const handler = async (event) => {
  if ((event.httpMethod || event.method) !== 'GET') return json(405, { error: 'method_not_allowed' });
  const user = await currentUser(event);
  if (!user) return json(401, { error: 'not_authenticated' });
  return json(200, { user, access: Boolean(user.has_access) });
};
