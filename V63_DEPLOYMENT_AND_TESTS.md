# MUEEN AI V6.3 — Teacher administration (candidate, not deployed)

## Scope
- Only a **currently active principal** of the selected school may invite teachers/coordinators, list memberships, or activate/deactivate teacher/coordinator memberships.
- Central system administrator is **not yet implemented**: a dedicated trusted admin identity and cross-school authorization policy must be specified before adding it. Never equate `service_role` with a human administrator.
- Existing users cannot yet be attached through the invitation UI; they require a verified administrative workflow.
- The UI uses the user's Supabase JWT. The Edge Function independently checks principal status against `school_memberships` before using its server-only service role.
- No database migrations are required for the documented membership columns. This implementation assumes a unique constraint on `(school_id,user_id)`; verify it before deploying.

## Deployment (staging only)
1. Copy the package to a new Git branch `develop/v6.3-teachers`; do **not** deploy to `main` yet.
2. Verify `school_memberships` unique `(school_id,user_id)` and current RLS/GRANT, and inspect the Edge Function code.
3. Configure Supabase CLI and link **staging** project. Deploy `supabase functions deploy mueen-teacher-admin --no-verify-jwt` **only if** JWT verification is enforced inside the function as implemented. Prefer gateway JWT verification when compatible with your Supabase key configuration; never disable verification without independent token validation.
4. Ensure `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` are **Edge Function server-side only**. Never put `SERVICE_ROLE_KEY` into Streamlit secrets or GitHub.
5. Ensure Streamlit staging secrets contain only `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` (plus existing app secrets).
6. Confirm Supabase Auth URL configuration, invitation email templates, email sending rate limits/SMTP, and **disable public sign-ups** in Supabase Auth settings if invite-only access is required.
7. Test with staging accounts and fake student data, not real student data.

## Acceptance checklist
- [ ] Principal can list only own school memberships.
- [ ] Teacher and coordinator cannot invoke Edge Function even with manually crafted requests.
- [ ] Principal cannot target a different school ID.
- [ ] Principal can invite a NEW teacher and the invite email arrives.
- [ ] Invited teacher can activate account and sees only assigned school.
- [ ] Duplicate invitation/existing account fails safely; support process documented.
- [ ] Deactivated teacher loses access to school on a new request; existing JWT cannot bypass RLS.
- [ ] Principal cannot deactivate self or another principal.
- [ ] All errors are logged server-side without sensitive credentials; audit trail still needs implementation before production.
- [ ] School isolation and subject/class permissions tested separately.
- [ ] V6.2 executive report and intervention workflow regression tests pass.
- [ ] Staging reviewed and approved before one PR/merge to `main`.

## Important limitations
- This is a **test candidate**, not production-ready. No live Supabase access or end-to-end invitation testing has been performed here.
- There is no complete audit-log table or centralized admin UI in this package.
- Invitation and membership creation are not atomic across Auth and Postgres. A failed membership insert requires manual reconciliation.
- Membership listings show user IDs rather than emails, because the auth admin user list is not school-scoped.
- Confirm existing RLS policies enforce `is_active` on every school-scoped table and verify DB function EXECUTE privileges.

References: https://supabase.com/docs/guides/functions/auth ; https://supabase.com/docs/guides/auth ; https://supabase.com/docs/guides/database/postgres/row-level-security
