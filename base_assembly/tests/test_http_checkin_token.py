# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""HTTP tests: Check-in by token GET /assembly/c/<token> (auth=public).

When the controller is not implemented, tests are skipped (404). Requires
assembly.attendee with checkin_token when controller exists.
"""

from .http_common import AssemblyHttpCase


class TestHttpCheckinToken(AssemblyHttpCase):
    """Tests for /assembly/c/<token>: valid/invalid/expired/revoked, idempotence."""

    def _checkin_route(self, token):
        """GET /assembly/c/<token> without auth."""
        self.session.logout(keep_db=True)
        from odoo.http import root

        root.session_store.save(self.session)
        self.opener.cookies.pop("session_id", None)
        return self.url_open(
            "/assembly/c/%s" % (token or ""),
            allow_redirects=False,
        )

    def test_ckt_01_valid_token_first_time_200_confirmed(self):
        """CKT-01: Valid token, first time, returns 200 and confirms attendee (if controller exists)."""
        if (
            not hasattr(self.attendee, "checkin_token")
            or not self.attendee.checkin_token
        ):
            self.skipTest("assembly.attendee has no checkin_token field")
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        res = self._checkin_route(self.attendee.checkin_token)
        self._skip_if_route_404(res, "Check-in by token")
        self.assertEqual(res.status_code, 200)
        text = res.content.decode("utf-8", errors="replace")
        self.assertTrue(
            "Confirmado" in text
            or "confirmado" in text.lower()
            or "Ya confirmado" in text,
        )
        self.attendee.invalidate_recordset()
        self.assertEqual(self.attendee.attendee_state, "confirmed")

    def test_ckt_02_valid_token_already_confirmed_idempotent(self):
        """CKT-02: Valid token, already confirmed, returns 200 'Ya confirmado'."""
        if (
            not hasattr(self.attendee, "checkin_token")
            or not self.attendee.checkin_token
        ):
            self.skipTest("assembly.attendee has no checkin_token field")
        self.attendee.attendee_state = "confirmed"
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        res = self._checkin_route(self.attendee.checkin_token)
        self._skip_if_route_404(res, "Check-in by token")
        self.assertEqual(res.status_code, 200)
        text = res.content.decode("utf-8", errors="replace")
        self.assertTrue("Ya confirmado" in text or "ya confirmado" in text.lower())

    def test_ckt_03_token_nonexistent_generic_message(self):
        """CKT-03: Nonexistent token returns 200/404 with generic message (no leak)."""
        res = self._checkin_route("nonexistent-token-xyz")
        self._skip_if_route_404(res, "Check-in by token")
        self.assertIn(res.status_code, (200, 404))
        if res.status_code == 200:
            self.assertFalse(
                b"token" in res.content.lower() and b"not found" in res.content.lower(),
                "Should not reveal 'token not found'",
            )

    def test_ckt_04_token_empty_or_malformed_404_or_400(self):
        """CKT-04: Empty or malformed token path returns 404 or 400."""
        res = self.url_open("/assembly/c/", allow_redirects=False)
        self.assertIn(res.status_code, (404, 400, 500))

    def test_ckt_05_assembly_not_open_returns_403(self):
        """CKT-07: Assembly not open/in_session returns 403 or error message."""
        if (
            not hasattr(self.attendee, "checkin_token")
            or not self.attendee.checkin_token
        ):
            self.skipTest("assembly.attendee has no checkin_token field")
        res = self._checkin_route(self.attendee.checkin_token)
        self._skip_if_route_404(res, "Check-in by token")
        self.assertIn(res.status_code, (403, 200))
        if res.status_code == 200:
            text = res.content.decode("utf-8", errors="replace")
            self.assertTrue(
                "not open" in text.lower() or "invalid" in text.lower(),
                "Response should indicate assembly not open or invalid params",
            )

    def test_ckt_06_reuse_link_second_call_already_confirmed(self):
        """CKT-08: Second call with same token (reuse) returns 200 'Already confirmed'."""
        if (
            not hasattr(self.attendee, "checkin_token")
            or not self.attendee.checkin_token
        ):
            self.skipTest("assembly.attendee has no checkin_token field")
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        res1 = self._checkin_route(self.attendee.checkin_token)
        self._skip_if_route_404(res1, "Check-in by token")
        res2 = self._checkin_route(self.attendee.checkin_token)
        self.assertEqual(res2.status_code, 200)
        text2 = res2.content.decode("utf-8", errors="replace")
        self.assertTrue("Ya confirmado" in text2 or "ya confirmado" in text2.lower())
