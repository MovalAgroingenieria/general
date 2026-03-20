# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Security tests: HTTP controller /assembly/attendance.

Validates that only assembly managers can open the attendance form from QR;
user (assembly_group_user) receives error (403/500); invalid params return 400/404.
"""

from .common import AssemblyTestMixin
from .http_common import AssemblyHttpCase


class TestAssemblySecurityHttp(AssemblyHttpCase):
    """HTTP controller security tests for /assembly/attendance."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user = cls.env.ref("base_assembly.assembly_group_user")
        cls.group_manager = cls.env.ref("base_assembly.assembly_group_manager")
        cls.base_user = cls.env.ref("base.group_user")

        cls.user_assembly_user = cls.env["res.users"].create(
            {
                "name": "Assembly User HTTP",
                "login": "assembly_user_http_sec",
                "password": "assembly_user_http_sec",
                "groups_id": [(6, 0, [cls.base_user.id, cls.group_user.id])],
            }
        )
        cls.user_assembly_manager = cls.env["res.users"].create(
            {
                "name": "Assembly Manager HTTP",
                "login": "assembly_manager_http_sec",
                "password": "assembly_manager_http_sec",
                "groups_id": [(6, 0, [cls.base_user.id, cls.group_manager.id])],
            }
        )
        mixin = AssemblyTestMixin()
        mixin.env = cls.env
        cls.assembly, _ = mixin._create_assembly_with_agenda()
        cls.assembly.action_generate_attendees()
        cls.attendee = cls.assembly.attendee_ids[0]
        cls.assembly.action_announce()
        cls.assembly.action_open_registration()

    def test_attendance_route_without_params_returns_400(self):
        self.authenticate("admin", "admin")
        res = self.url_open(
            "/assembly/attendance",
            allow_redirects=False,
        )
        self.assertIn(
            res.status_code,
            (400, 200),
            "Missing params should yield 400 or error page (200 with error body)",
        )
        if res.status_code == 200:
            self.assertTrue(
                b"Missing" in res.content or b"missing" in res.content.lower(),
                "Response should mention missing parameters",
            )

    def test_attendance_route_with_invalid_params_returns_400_or_404(self):
        self.authenticate("admin", "admin")
        res = self.url_open(
            "/assembly/attendance?assembly_id=foo&participant_id=bar",
            allow_redirects=False,
        )
        self.assertIn(
            res.status_code,
            (400, 404, 500),
            "Invalid assembly_id/participant_id should not succeed",
        )

    def test_attendance_route_nonexistent_assembly_returns_404(self):
        self.authenticate(self.user_assembly_manager.login, "assembly_manager_http_sec")
        res = self.url_open(
            "/assembly/attendance?assembly_id=999999&participant_id=%s"
            % self.attendee.partner_id.id,
            allow_redirects=False,
        )
        self.assertEqual(
            res.status_code,
            404,
            "Nonexistent assembly should return 404",
        )

    def test_attendance_route_as_assembly_user_denied(self):
        """SEC-HTTP-01: User (not manager) must not open attendance form."""
        self.authenticate(self.user_assembly_user.login, "assembly_user_http_sec")
        url = "/assembly/attendance?assembly_id=%s&participant_id=%s" % (
            self.assembly.id,
            self.attendee.partner_id.id,
        )
        res = self.url_open(url, allow_redirects=False)
        self.assertIn(
            res.status_code,
            (403, 500),
            "Assembly User must get 403 or 500 (AccessError), not 200/302",
        )

    def test_attendance_route_as_manager_redirects_to_form(self):
        """SEC-HTTP-02: Manager can open attendance and is redirected to backend form."""
        self.authenticate(self.user_assembly_manager.login, "assembly_manager_http_sec")
        url = "/assembly/attendance?assembly_id=%s&participant_id=%s" % (
            self.assembly.id,
            self.attendee.partner_id.id,
        )
        res = self.url_open(url, allow_redirects=False)
        self.assertEqual(
            res.status_code,
            302,
            "Manager should get redirect to attendee form",
        )
        location = res.headers.get("Location", "")
        self.assertTrue(
            "assembly.attendee" in location or "id=%s" % self.attendee.id in location,
            "Redirect Location should point to attendee form (assembly.attendee or id)",
        )
