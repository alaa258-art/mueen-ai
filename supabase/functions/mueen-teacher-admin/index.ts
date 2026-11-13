import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), {
  status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }
});
const uuid = (v: unknown) => typeof v === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v);

Deno.serve(async (req) => {
  if (req.method !== 'POST') return json({ error: 'Method not allowed' }, 405);
  const url = Deno.env.get('SUPABASE_URL');
  const anon = Deno.env.get('SUPABASE_ANON_KEY');
  const service = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
  if (!url || !anon || !service) return json({ error: 'Server configuration missing' }, 500);
  const bearer = req.headers.get('authorization') || '';
  if (!/^Bearer\s+\S+$/.test(bearer)) return json({ error: 'Authentication required' }, 401);
  const jwt = bearer.replace(/^Bearer\s+/i, '');
  const userClient = createClient(url, anon, { global: { headers: { Authorization: `Bearer ${jwt}` } } });
  const { data: identity, error: authError } = await userClient.auth.getUser(jwt);
  if (authError || !identity.user) return json({ error: 'Invalid session' }, 401);
  let body: Record<string, unknown>;
  try { body = await req.json(); } catch { return json({ error: 'Invalid JSON' }, 400); }
  if (!uuid(body.school_id)) return json({ error: 'Invalid school ID' }, 400);
  const schoolId = body.school_id as string;
  const admin = createClient(url, service, { auth: { autoRefreshToken: false, persistSession: false } });
  // NEVER authorize from a client-supplied role. Verify live DB membership.
  const { data: principal, error: roleError } = await admin.from('school_memberships')
    .select('id').eq('school_id', schoolId).eq('user_id', identity.user.id)
    .eq('role', 'principal').eq('is_active', true).maybeSingle();
  if (roleError || !principal) return json({ error: 'Principal access required' }, 403);

  
if (body.action === 'list') {
  const { data, error } = await admin
    .from('school_memberships')
    .select('user_id,role,is_active,created_at')
    .eq('school_id', schoolId)
    .order('created_at');

  if (error) {
    return json({ error: 'Unable to list memberships' }, 500);
  }

  const members = await Promise.all(
    (data || []).map(async (member) => {
      const { data: authData, error: authError } =
        await admin.auth.admin.getUserById(member.user_id);

      return {
        ...member,
        email: authError ? null : (authData.user?.email ?? null),
      };
    })
  );

  return json({ members });
}

  if (body.action === 'invite') {
    const email = String(body.email || '').trim().toLowerCase();
    const role = body.role;
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || email.length > 254 || !['teacher','coordinator'].includes(String(role)))
      return json({ error: 'Invalid email or role' }, 400);
    // Existing accounts must be linked by a separate verified admin workflow.
    // Supabase inviteUserByEmail may reject an existing account: do not silently grant membership.
    const { data: invited, error: inviteError } = await admin.auth.admin.inviteUserByEmail(email);
    if (inviteError || !invited.user) return json({ error: 'Invite failed. Existing accounts require administrator review.' }, 409);
    const { error: membershipError } = await admin.from('school_memberships').insert({
      school_id: schoolId, user_id: invited.user.id, role, is_active: true
    });
    if (membershipError) {
      // Fail closed: no school membership; do not report success.
      return json({ error: 'Invitation created but school membership failed; administrator must reconcile.' }, 500);
    }
    return json({ ok: true });
  }
  if (body.action === 'set_active') {
    if (!uuid(body.user_id) || typeof body.is_active !== 'boolean') return json({ error: 'Invalid input' }, 400);
    if (body.user_id === identity.user.id) return json({ error: 'Cannot change your own membership' }, 403);
    const { data: target, error: targetError } = await admin.from('school_memberships')
      .select('id,role').eq('school_id', schoolId).eq('user_id', body.user_id).maybeSingle();
    if (targetError || !target || !['teacher','coordinator'].includes(target.role))
      return json({ error: 'Only teacher/coordinator memberships can be changed' }, 403);
    const { error } = await admin.from('school_memberships').update({ is_active: body.is_active })
      .eq('id', target.id).eq('school_id', schoolId);
    if (error) return json({ error: 'Unable to update membership' }, 500);
    return json({ ok: true });
  }
  return json({ error: 'Unknown action' }, 400);
});
