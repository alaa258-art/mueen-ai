# MUEEN AI V6.3 — Staging security smoke tests

This suite uses **Python standard library only**. It tests the *deployed* `mueen-teacher-admin` function; it does not assert that the GitHub file is identical to the deployed function.

## Before running

Use a separate Supabase **staging** project and fake users. Never commit credentials, JWTs, `.env` files, or `service_role` keys. The suite never needs a service-role key. Confirm the endpoint belongs to staging, not production. Tokens must be short-lived, obtained through an authorized test login, and set as environment variables **locally or in protected CI secrets**, never in public logs.

Set `MUEEN_PROJECT_LABEL=staging`, `MUEEN_STAGING_URL=https://YOUR-STAGING-PROJECT.supabase.co`, and `MUEEN_SCHOOL_ID=YOUR-STAGING-SCHOOL-UUID`. Optionally set `MUEEN_PUBLISHABLE_KEY` (public key), `MUEEN_PRINCIPAL_JWT`, `MUEEN_TEACHER_JWT`, `MUEEN_COORDINATOR_JWT`, and `MUEEN_OTHER_SCHOOL_ID` to unlock authorization tests.

Run:

```bash
python -m unittest -v test_teacher_admin.py
```

A **SKIP** is not a PASS. Without test accounts, only the anonymous/invalid-token checks run. No invitation is sent in the default suite. Optional `test_11` changes an existing fake teacher's active status and is disabled unless `MUEEN_ALLOW_MUTATIONS=YES_STAGING_ONLY` and `MUEEN_FAKE_TEACHER_USER_ID` are set. Do not enable against real users.

## Important gaps before merge

- A real new-user invitation, duplicate invitation, account activation, and email delivery require a disposable staging mailbox and a dedicated integration harness with cleanup/reconciliation; **not covered** here.
- Revocation should be tested by logging in as a fake teacher, deactivating them, then verifying school-scoped DB queries fail even with the old JWT; **not covered** here.
- Cross-school student data isolation, subject/class permissions, audit-log completeness, and V6.2 executive-report regressions require separate tests.
- Current `index.ts` has no transactional guarantee across Auth invitation and membership insert, and no administrative audit log. Central administrator is not implemented.
- The deployed code previously shown in Supabase was longer/different from the uploaded 70-line GitHub file. Verify deployed source parity before merge.
- The `Verify JWT with legacy secret` toggle being OFF is acceptable only if function-level JWT validation remains enforced and tested.

**Merge gate:** all mandatory tests pass, zero unexplained skips, full invitation/revocation/isolation coverage, deployment parity, and explicit staging signoff.

References: https://supabase.com/docs/guides/functions/auth ; https://supabase.com/docs/guides/database/postgres/row-level-security
