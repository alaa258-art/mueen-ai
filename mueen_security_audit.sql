-- MUEEN AI: read-only security audit (run in Supabase SQL Editor as project owner)
-- This inspects current settings; it does not change policies or grant permissions.

-- 1) Confirm RLS is enabled for the key tables.
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('schools', 'school_memberships', 'students', 'assessment_records')
ORDER BY tablename;

-- 2) Review policies on those tables.
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('schools', 'school_memberships', 'students', 'assessment_records')
ORDER BY tablename, policyname;

-- 3) Review table privileges granted to API roles.
SELECT grantee, table_name, privilege_type
FROM information_schema.role_table_grants
WHERE table_schema = 'public'
  AND table_name IN ('schools', 'school_memberships', 'students', 'assessment_records')
  AND grantee IN ('anon', 'authenticated')
ORDER BY table_name, grantee, privilege_type;

-- Do not disable RLS or grant broad privileges to anon.
-- Do not run destructive tests using real student data.
