
"""MUEEN V6.3 staging security tests."""
import json
import os
import re
import unittest
import urllib.request
import urllib.error

BASE = os.getenv("MUEEN_STAGING_URL", "").rstrip("/")
FUNCTION = BASE + "/functions/v1/mueen-teacher-admin"
PROJECT_LABEL = os.getenv("MUEEN_PROJECT_LABEL", "")
SCHOOL = os.getenv("MUEEN_SCHOOL_ID", "")
OTHER = os.getenv("MUEEN_OTHER_SCHOOL_ID", "")
PRINCIPAL = os.getenv("MUEEN_PRINCIPAL_JWT", "")
TEACHER = os.getenv("MUEEN_TEACHER_JWT", "")
COORD = os.getenv("MUEEN_COORDINATOR_JWT", "")
PUBLISHABLE = os.getenv("MUEEN_PUBLISHABLE_KEY", "")
ALLOW_MUTATIONS = os.getenv("MUEEN_ALLOW_MUTATIONS") == "YES_STAGING_ONLY"
FAKE_TARGET = os.getenv("MUEEN_FAKE_TEACHER_USER_ID", "")

UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}",
    re.I
)


def request(body, token=None):
    headers = {"Content-Type": "application/json"}

    if token:
        headers["Authorization"] = "Bearer " + token

    if PUBLISHABLE:
        headers["apikey"] = PUBLISHABLE

    req = urllib.request.Request(
        FUNCTION,
        data=json.dumps(body).encode(),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            data = json.loads(exc.read().decode())
        except (ValueError, UnicodeError):
            data = {}
        return exc.code, data





def require(condition, message):
    if not condition:
        raise RuntimeError(message)


class MueenSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require(PROJECT_LABEL.lower() == 'staging', 'MUEEN_PROJECT_LABEL must equal staging')
        require(BASE.startswith('https://') and '.supabase.co' in BASE,
                'Set a valid HTTPS Supabase MUEEN_STAGING_URL')
        require(all(UUID.fullmatch(v) for v in (SCHOOL, OTHER)),
                'Set valid MUEEN_SCHOOL_ID and MUEEN_OTHER_SCHOOL_ID')
        require(SCHOOL != OTHER, 'The two school IDs must differ')
        require(all((PRINCIPAL, TEACHER, COORD, PUBLISHABLE)),
                'Missing one or more required staging JWTs or publishable key')

    def test_01_anonymous_denied(self):
        status, data = request({'action': 'list', 'school_id': SCHOOL})
        self.assertEqual(status, 401, data)

    def test_02_invalid_jwt_denied(self):
        status, data = request({'action': 'list', 'school_id': SCHOOL}, 'invalid.jwt.token')
        self.assertEqual(status, 401, data)

    def test_03_teacher_cannot_list(self):
        status, data = request({'action': 'list', 'school_id': SCHOOL}, TEACHER)
        self.assertEqual(status, 403, data)

    def test_04_teacher_cannot_invite(self):
        status, data = request({'action': 'invite', 'school_id': SCHOOL,
                                'email': 'no-send@example.invalid', 'role': 'teacher'}, TEACHER)
        self.assertEqual(status, 403, data)

    def test_05_teacher_cannot_deactivate(self):
        status, data = request({'action': 'set_active', 'school_id': SCHOOL,
                                'user_id': SCHOOL, 'is_active': False}, TEACHER)
        self.assertEqual(status, 403, data)

    def test_06_coordinator_cannot_list(self):
        status, data = request({'action': 'list', 'school_id': SCHOOL}, COORD)
        self.assertEqual(status, 403, data)

    def test_07_principal_can_list(self):
        status, data = request({'action': 'list', 'school_id': SCHOOL}, PRINCIPAL)
        self.assertEqual(status, 200, data)
        self.assertIsInstance(data.get('members'), list)

    def test_08_principal_cannot_list_other_school(self):
        status, data = request({'action': 'list', 'school_id': OTHER}, PRINCIPAL)
        self.assertEqual(status, 403, data)

    def test_09_invalid_role_invite_rejected(self):
        status, data = request({'action': 'invite', 'school_id': SCHOOL,
                                'email': 'no-send@example.invalid', 'role': 'principal'}, PRINCIPAL)
        self.assertEqual(status, 400, data)

        def test_10_invalid_target_rejected(self):
        status, data = request(
            {
                'action': 'set_active',
                'school_id': SCHOOL,
                'user_id': 'not-a-uuid',
                'is_active': False
            },
            PRINCIPAL
        )
        self.assertEqual(status, 400, data)

    @unittest.skipUnless(
        ALLOW_MUTATIONS and PRINCIPAL and FAKE_TARGET,
        "Requires explicit mutation opt-in and fake target"
    )
    def test_11_deactivate_and_reactivate_fake_teacher(self):
            status, data = request(
                {
                    'action': 'set_active',
                    'school_id': SCHOOL,
                    'user_id': FAKE_TARGET,
                    'is_active': active
                },
                PRINCIPAL
            )
            self.assertEqual(status, 200, data)
            self.assertEqual(data.get('ok'), True))

    finally:
        status, data = request({
            'action': 'set_active',
            'school_id': SCHOOL,
            'user_id': FAKE_TARGET,
            'is_active': True
        }, PRINCIPAL)

        self.assertEqual(
            status, 200,
            f'CRITICAL: Reactivation failed: {data}'
        )
        self.assertEqual(data.get('ok'), True)(self):
        # A missing opt-in is a failure, not a silent skip in the full suite.
        require(ALLOW_MUTATIONS, 'Set MUEEN_ALLOW_MUTATIONS=YES_STAGING_ONLY explicitly')
        require(UUID.fullmatch(FAKE_TARGET or '') and FAKE_TARGET == FAKE_ALLOWLIST,
                'Fake teacher ID must be valid and match separately configured allowlist ID')
        require(FAKE_TARGET not in (SCHOOL, OTHER), 'Fake target cannot be a school ID')

        status, data = request({'action': 'list', 'school_id': SCHOOL}, PRINCIPAL)
        self.assertEqual(status, 200, data)
        members = [m for m in data.get('members', []) if m.get('user_id') == FAKE_TARGET]
        self.assertEqual(len(members), 1, 'Fake target must be a member of staging school')
        member = members[0]
        self.assertEqual(member.get('role'), 'teacher', 'Target must have teacher role')
        self.assertIs(type(member.get('is_active')), bool, 'Missing original active state')
        original = member['is_active']

        def set_active(value):
            status, payload = request({'action': 'set_active', 'school_id': SCHOOL,
                                       'user_id': FAKE_TARGET, 'is_active': value}, PRINCIPAL)
            self.assertEqual(status, 200, payload)
            self.assertIs(payload.get('ok'), True)

        def verify_active(expected):
            status, payload = request({'action': 'list', 'school_id': SCHOOL}, PRINCIPAL)
            self.assertEqual(status, 200, payload)
            rows = [m for m in payload.get('members', []) if m.get('user_id') == FAKE_TARGET]
            self.assertEqual(len(rows), 1)
            self.assertIs(rows[0].get('is_active'), expected)

        try:
            set_active(False)
            verify_active(False)
            set_active(True)
            verify_active(True)
        finally:
            # Always attempt to restore the initial membership state.
            set_active(original)
            verify_active(original)


if __name__ == '__main__':
    unittest.main(verbosity=2)
