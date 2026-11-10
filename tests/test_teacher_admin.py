"""MUEEN V6.3 staging smoke/security tests. Python 3.10+, standard library only.
Read-only by default. Optional mutation tests require explicit opt-in and dedicated fake accounts.
"""
import json, os, re, sys, urllib.request, urllib.error, unittest
from pathlib import Path

BASE = os.getenv('MUEEN_STAGING_URL', '').rstrip('/')
FUNCTION = BASE + '/functions/v1/mueen-teacher-admin' if BASE else ''
SCHOOL = os.getenv('MUEEN_SCHOOL_ID', '')
OTHER = os.getenv('MUEEN_OTHER_SCHOOL_ID', '')
PRINCIPAL = os.getenv('MUEEN_PRINCIPAL_JWT', '')
TEACHER = os.getenv('MUEEN_TEACHER_JWT', '')
COORD = os.getenv('MUEEN_COORDINATOR_JWT', '')
PUBLISHABLE = os.getenv('MUEEN_PUBLISHABLE_KEY', '')
ALLOW_MUTATIONS = os.getenv('MUEEN_ALLOW_MUTATIONS') == 'YES_STAGING_ONLY'
FAKE_TARGET = os.getenv('MUEEN_FAKE_TEACHER_USER_ID', '')


def request(body, token=None, method='POST'):
    headers = {'Content-Type': 'application/json'}
    if token: headers['Authorization'] = 'Bearer ' + token
    if PUBLISHABLE: headers['apikey'] = PUBLISHABLE
    payload = json.dumps(body).encode('utf-8') if method == 'POST' else None
    req = urllib.request.Request(FUNCTION, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            return res.status, json.loads(res.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        try: data = json.loads(exc.read().decode('utf-8'))
        except Exception: data = {}
        return exc.code, data


class MueenSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not BASE or not SCHOOL:
            raise unittest.SkipTest('Set MUEEN_STAGING_URL and MUEEN_SCHOOL_ID')
        if 'staging' not in os.getenv('MUEEN_PROJECT_LABEL', '').lower():
            raise unittest.SkipTest('Set MUEEN_PROJECT_LABEL=staging to confirm environment')

    def test_01_anonymous_denied(self):
        status, data = request({'action': 'list', 'school_id': SCHOOL})
        self.assertEqual(status, 401, data)

    def test_02_invalid_jwt_denied(self):
        status, data = request({'action': 'list', 'school_id': SCHOOL}, 'invalid.jwt.token')
        self.assertEqual(status, 401, data)

    @unittest.skipUnless(TEACHER, 'Requires MUEEN_TEACHER_JWT')
    def test_03_teacher_cannot_list(self):
        status, data = request({'action': 'list', 'school_id': SCHOOL}, TEACHER)
        self.assertEqual(status, 403, data)

    @unittest.skipUnless(TEACHER, 'Requires MUEEN_TEACHER_JWT')
    def test_04_teacher_cannot_invite(self):
        status, data = request({'action': 'invite', 'school_id': SCHOOL, 'email': 'no-send@example.invalid', 'role': 'teacher'}, TEACHER)
        self.assertEqual(status, 403, data)

    @unittest.skipUnless(TEACHER, 'Requires MUEEN_TEACHER_JWT')
    def test_05_teacher_cannot_deactivate(self):
        status, data = request({'action': 'set_active', 'school_id': SCHOOL, 'user_id': SCHOOL, 'is_active': False}, TEACHER)
        self.assertEqual(status, 403, data)

    @unittest.skipUnless(COORD, 'Requires MUEEN_COORDINATOR_JWT')
    def test_06_coordinator_cannot_list(self):
        status, data = request({'action': 'list', 'school_id': SCHOOL}, COORD)
        self.assertEqual(status, 403, data)

    @unittest.skipUnless(PRINCIPAL, 'Requires MUEEN_PRINCIPAL_JWT')
    def test_07_principal_can_list(self):
        status, data = request({'action': 'list', 'school_id': SCHOOL}, PRINCIPAL)
        self.assertEqual(status, 200, data)
        self.assertIsInstance(data.get('members'), list)

    @unittest.skipUnless(PRINCIPAL and OTHER, 'Requires principal JWT and another school ID')
    def test_08_principal_cannot_list_other_school(self):
        status, data = request({'action': 'list', 'school_id': OTHER}, PRINCIPAL)
        self.assertEqual(status, 403, data)

    @unittest.skipUnless(PRINCIPAL, 'Requires principal JWT')
    def test_09_invalid_role_invite_rejected(self):
        status, data = request({'action': 'invite', 'school_id': SCHOOL, 'email': 'no-send@example.invalid', 'role': 'principal'}, PRINCIPAL)
        self.assertEqual(status, 400, data)

    @unittest.skipUnless(PRINCIPAL, 'Requires principal JWT')
    def test_10_invalid_target_rejected(self):
        status, data = request({'action': 'set_active', 'school_id': SCHOOL, 'user_id': 'not-a-uuid', 'is_active': False}, PRINCIPAL)
        self.assertEqual(status, 400, data)

    @unittest.skipUnless(ALLOW_MUTATIONS and PRINCIPAL and FAKE_TARGET, 'Requires explicit mutation opt-in and fake target')
    def test_11_deactivate_and_reactivate_fake_teacher(self):
        # WARNING: only use an isolated fake teacher account on staging.
        for active in (False, True):
            status, data = request({'action': 'set_active', 'school_id': SCHOOL, 'user_id': FAKE_TARGET, 'is_active': active}, PRINCIPAL)
            self.assertEqual(status, 200, data)
            self.assertEqual(data.get('ok'), True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
