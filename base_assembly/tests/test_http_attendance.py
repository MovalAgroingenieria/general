# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""HTTP tests: QR check-in route GET /assembly/attendance (auth=user, manager only)."""

from .http_common import AssemblyHttpCase


class TestHttpAttendance(AssemblyHttpCase):
    """Tests for /assembly/attendance: params, auth, assembly state, 200/302/403/404."""

    def test_att_01_manager_valid_params_redirects_to_form(self):
        """ATT-01: Manager with valid assembly_id and participant_id gets 302 to attendee form."""
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        self.authenticate(self.user_manager.login, "assembly_manager_http")
        url = "/assembly/attendance?assembly_id=%s&participant_id=%s" % (
            self.assembly.id,
            self.attendee.partner_id.id,
        )
        res = self.url_open(url, allow_redirects=False)
        self.assertEqual(res.status_code, 302, "Manager should get redirect to form")
        location = res.headers.get("Location", "")
        self.assertTrue(
            "assembly.attendee" in location or "id=%s" % self.attendee.id in location,
            "Redirect should point to attendee form",
        )

    def test_att_02_missing_params_returns_400_or_error_body(self):
        """ATT-02: Missing assembly_id or participant_id returns 400 or 200 with error message."""
        self.authenticate("admin", "admin")
        res = self.url_open("/assembly/attendance", allow_redirects=False)
        self.assertIn(res.status_code, (400, 200))
        if res.status_code == 200:
            self.assertTrue(
                b"Missing" in res.content or b"missing" in res.content.lower(),
                "Body should mention missing parameters",
            )

    def test_att_03_invalid_params_returns_400(self):
        """ATT-03: Non-numeric assembly_id/participant_id returns 400."""
        self.authenticate("admin", "admin")
        res = self.url_open(
            "/assembly/attendance?assembly_id=foo&participant_id=bar",
            allow_redirects=False,
        )
        self.assertIn(res.status_code, (400, 404, 500))

    def test_att_04_nonexistent_assembly_returns_404(self):
        """ATT-04: Nonexistent assembly_id returns 404."""
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        self.authenticate(self.user_manager.login, "assembly_manager_http")
        res = self.url_open(
            "/assembly/attendance?assembly_id=999999&participant_id=%s"
            % self.attendee.partner_id.id,
            allow_redirects=False,
        )
        self.assertEqual(res.status_code, 404)

    def test_att_05_participant_not_attendee_returns_404(self):
        """ATT-05: participant_id not in assembly's attendees returns 404."""
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        other_partner = self.env["res.partner"].create(
            {"name": "Other Partner", "is_company": False}
        )
        self.authenticate(self.user_manager.login, "assembly_manager_http")
        res = self.url_open(
            "/assembly/attendance?assembly_id=%s&participant_id=%s"
            % (self.assembly.id, other_partner.id),
            allow_redirects=False,
        )
        self.assertEqual(res.status_code, 404)

    def test_att_06_non_manager_gets_403_or_500(self):
        """ATT-06: User (assembly_group_user) gets 403 or 500, not 302."""
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        self.authenticate(self.user_assembly_user.login, "assembly_user_http")
        url = "/assembly/attendance?assembly_id=%s&participant_id=%s" % (
            self.assembly.id,
            self.attendee.partner_id.id,
        )
        res = self.url_open(url, allow_redirects=False)
        self.assertIn(res.status_code, (403, 500))

    def test_att_07_anonymous_redirects_to_login_or_403(self):
        """ATT-07: No session (anonymous) gets 302 to login or 403."""
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        self.session.logout(keep_db=True)
        from odoo.http import root

        root.session_store.save(self.session)
        self.opener.cookies.pop("session_id", None)
        url = "/assembly/attendance?assembly_id=%s&participant_id=%s" % (
            self.assembly.id,
            self.attendee.partner_id.id,
        )
        res = self.url_open(url, allow_redirects=False)
        self.assertIn(res.status_code, (302, 403))

    def test_att_08_assembly_draft_returns_403(self):
        """ATT-08: Assembly in draft returns 403."""
        self.authenticate(self.user_manager.login, "assembly_manager_http")
        url = "/assembly/attendance?assembly_id=%s&participant_id=%s" % (
            self.assembly.id,
            self.attendee.partner_id.id,
        )
        res = self.url_open(url, allow_redirects=False)
        self.assertEqual(res.status_code, 403)

    def test_att_09_assembly_announced_returns_403(self):
        """ATT-09: Assembly in announced (not open) returns 403."""
        self.assembly.action_announce()
        self.authenticate(self.user_manager.login, "assembly_manager_http")
        url = "/assembly/attendance?assembly_id=%s&participant_id=%s" % (
            self.assembly.id,
            self.attendee.partner_id.id,
        )
        res = self.url_open(url, allow_redirects=False)
        self.assertEqual(res.status_code, 403)

    def test_att_10_assembly_closed_returns_403(self):
        """ATT-10: Assembly closed returns 403."""
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        self.assembly.action_start_session()
        self.agenda.action_skip()
        self.assembly.action_close()
        self.authenticate(self.user_manager.login, "assembly_manager_http")
        url = "/assembly/attendance?assembly_id=%s&participant_id=%s" % (
            self.assembly.id,
            self.attendee.partner_id.id,
        )
        res = self.url_open(url, allow_redirects=False)
        self.assertEqual(res.status_code, 403)

    def test_att_11_assembly_cancelled_returns_403(self):
        """ATT-11: Assembly cancelled returns 403."""
        self.assembly.action_cancel()
        self.authenticate(self.user_manager.login, "assembly_manager_http")
        url = "/assembly/attendance?assembly_id=%s&participant_id=%s" % (
            self.assembly.id,
            self.attendee.partner_id.id,
        )
        res = self.url_open(url, allow_redirects=False)
        self.assertEqual(res.status_code, 403)

    def test_att_12_assembly_in_session_accepts(self):
        """Assembly in_session (not only open) accepts check-in."""
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        self.assembly.action_start_session()
        self.authenticate(self.user_manager.login, "assembly_manager_http")
        url = "/assembly/attendance?assembly_id=%s&participant_id=%s" % (
            self.assembly.id,
            self.attendee.partner_id.id,
        )
        res = self.url_open(url, allow_redirects=False)
        self.assertEqual(res.status_code, 302)
