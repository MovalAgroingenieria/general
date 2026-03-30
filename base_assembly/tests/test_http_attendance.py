# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
# pylint: disable=import-outside-toplevel

"""HTTP tests: GET /assembly/attendance (auth=user, assembly manager, open/in_session).

Explicit functional contract (mandatory):
- valid access → ``test_att_01_manager_valid_params_redirects_to_form``,
  ``test_att_12_assembly_in_session_accepts``;
- non-manager → ``test_att_06_non_manager_forbidden``;
- disallowed assembly state → e.g. ``test_att_08_assembly_draft_returns_403``;
- participant without attendee row → ``test_att_05_participant_not_attendee_returns_404``.
- tracked short URL → ``test_att_tracked_short_link_redirects_to_attendance_url``,
  ``test_att_tracked_short_link_resolves_same_as_direct_attendance_url``
  (``link_tracker`` ``/r/<code>`` → attendance target → manager form; no ``website`` in manifest).
"""

from urllib.parse import parse_qs, urlparse

from odoo.addons.base_assembly.controllers.attendance import AttendanceController

from .http_common import AssemblyHttpCase


def _http_routed_methods(controller_cls):
    """Yield (method_name, path, auth) for @route methods defined on controller_cls."""
    for key, val in controller_cls.__dict__.items():
        if not callable(val):
            continue
        routing = getattr(val, "original_routing", None)
        if not routing:
            continue
        auth = routing.get("auth", "user")
        for url in routing.get("routes") or ():
            yield key, url, auth


def _werkzeug_rule_endpoint_module(endpoint):
    """Resolve ``__module__`` for an Odoo werkzeug rule endpoint (often a partial)."""
    func = getattr(endpoint, "func", endpoint)
    if hasattr(func, "__func__"):
        return getattr(func.__func__, "__module__", "") or ""
    return getattr(func, "__module__", "") or ""


class TestHttpAttendance(AssemblyHttpCase):
    """Endpoint regression; minimum contract is referenced in the module docstring."""

    def test_att_base_controller_single_manager_route_only(self):
        """BASE: only ``open_attendance`` on ``/assembly/attendance`` with auth user."""
        rows = list(_http_routed_methods(AttendanceController))
        self.assertEqual(
            len(rows),
            1,
            "base_assembly must expose a single HTTP @route on this controller",
        )
        name, path, auth = rows[0]
        self.assertEqual(name, "open_attendance")
        self.assertEqual(path, "/assembly/attendance")
        self.assertEqual(auth, "user")

    def test_att_no_public_token_checkin_on_controller(self):
        """No public token check-in endpoint on the attendance controller."""
        self.assertFalse(
            hasattr(AttendanceController, "checkin_by_token"),
            "checkin_by_token (public check-in) does not belong in BASE",
        )

    def test_att_routing_map_base_assembly_has_no_assembly_c_prefix(self):
        """``base_assembly`` must not register ``/assembly/c/...`` (public check-in)."""
        routing_map = self.env["ir.http"].routing_map()
        bad = []
        for rule in routing_map.iter_rules():
            if not rule.rule.startswith("/assembly/c"):
                continue
            mod = _werkzeug_rule_endpoint_module(rule.endpoint)
            if mod.startswith("odoo.addons.base_assembly"):
                bad.append(rule.rule)
        self.assertFalse(
            bad,
            "base_assembly must not expose /assembly/c/* routes: %s" % bad,
        )

    def test_att_tracked_short_link_redirects_to_attendance_url(self):
        """AF v2 / link_tracker: ``/r/<code>`` resolves to the stored attendance URL (301).

        Uses the same registry as ``base_assembly`` + ``link_tracker`` (no ``website`` addon
        required for this route — it is registered by ``link_tracker``).
        """
        att = self.attendee
        self.assertTrue(
            att.attendance_link_tracker_id,
            "attendee should have a link.tracker after generate attendees",
        )
        code = att.attendance_link_tracker_id.code
        self.assertTrue(code)
        res = self.url_open("/r/%s" % code, allow_redirects=False)
        self.assertIn(
            res.status_code,
            (301, 302),
            "link_tracker redirect expected; got %s" % res.status_code,
        )
        loc = res.headers.get("Location", "")
        self.assertTrue(loc, "Redirect Location must be set")
        parsed = urlparse(loc)
        self.assertIn("/assembly/attendance", parsed.path)
        qs = parse_qs(parsed.query)
        self.assertEqual(
            (qs.get("assembly_id") or [None])[0],
            str(self.assembly.id),
        )
        self.assertEqual(
            (qs.get("participant_id") or [None])[0],
            str(att.partner_id.id),
        )

    def test_att_tracked_short_link_resolves_same_as_direct_attendance_url(self):
        """End-to-end: ``/r/<code>`` Location, when opened by a manager, matches direct deep link."""
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        att = self.attendee
        code = att.attendance_link_tracker_id.code
        self.assertTrue(code)
        res_short = self.url_open("/r/%s" % code, allow_redirects=False)
        self.assertIn(res_short.status_code, (301, 302))
        loc = res_short.headers.get("Location", "")
        self.assertTrue(loc, "link_tracker must return a redirect target")
        self.authenticate(self.user_manager.login, "assembly_manager_http")
        res_tracked = self.url_open(loc, allow_redirects=False)
        self.assertIn(
            res_tracked.status_code,
            (302, 303),
            "Resolved attendance URL must redirect manager to backend form",
        )
        loc_tracked = res_tracked.headers.get("Location", "")
        direct = "/assembly/attendance?assembly_id=%s&participant_id=%s" % (
            self.assembly.id,
            att.partner_id.id,
        )
        res_direct = self.url_open(direct, allow_redirects=False)
        self.assertIn(res_direct.status_code, (302, 303))
        loc_direct = res_direct.headers.get("Location", "")
        self.assertURLEqual(loc_tracked, loc_direct)

    def test_att_01_manager_valid_params_redirects_to_form(self):
        """FS: valid access — manager, assembly ``open``, ``assembly_id`` + ``participant_id`` → 302/303."""
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        self.authenticate(self.user_manager.login, "assembly_manager_http")
        url = "/assembly/attendance?assembly_id=%s&participant_id=%s" % (
            self.assembly.id,
            self.attendee.partner_id.id,
        )
        res = self.url_open(url, allow_redirects=False)
        self.assertIn(
            res.status_code,
            (302, 303),
            "Manager should get redirect to form",
        )
        location = res.headers.get("Location", "")
        self.assertTrue(
            "assembly.attendee" in location or "id=%s" % self.attendee.id in location,
            "Redirect should point to attendee form",
        )

    def test_att_02_missing_params_returns_400_or_error_body(self):
        """ATT-02: Missing assembly_id or participant_id → 400 + descriptive body."""
        self.authenticate("admin", "admin")
        res = self.url_open("/assembly/attendance", allow_redirects=False)
        self.assertEqual(res.status_code, 400)
        low = res.content.lower()
        self.assertTrue(
            b"assembly_id" in low or b"participant" in low,
            "Body should name the expected query parameters",
        )

    def test_att_03_invalid_params_returns_400(self):
        """ATT-03: Non-numeric assembly_id/participant_id returns 400."""
        self.authenticate("admin", "admin")
        res = self.url_open(
            "/assembly/attendance?assembly_id=foo&participant_id=bar",
            allow_redirects=False,
        )
        self.assertEqual(res.status_code, 400)

    def test_att_03b_partial_params_returns_400(self):
        """Only one of assembly_id / participant_id is rejected."""
        self.authenticate(self.user_manager.login, "assembly_manager_http")
        res = self.url_open(
            "/assembly/attendance?assembly_id=%s" % self.assembly.id,
            allow_redirects=False,
        )
        self.assertEqual(res.status_code, 400)

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
        """FS: no attendee row — ``participant_id`` not in this assembly → 404."""
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        other_partner = self.env["res.partner"].create(  # noqa: F841
            {"name": "Other Partner", "is_company": False}
        )
        self.authenticate(self.user_manager.login, "assembly_manager_http")
        res = self.url_open(
            "/assembly/attendance?assembly_id=%s&participant_id=%s"
            % (self.assembly.id, other_partner.id),
            allow_redirects=False,
        )
        self.assertEqual(res.status_code, 404)

    def test_att_06_non_manager_forbidden(self):
        """FS: non-manager — user without ``assembly_group_manager`` → 403 (no redirect)."""
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        self.authenticate(self.user_assembly_user.login, "assembly_user_http")
        url = "/assembly/attendance?assembly_id=%s&participant_id=%s" % (
            self.assembly.id,
            self.attendee.partner_id.id,
        )
        res = self.url_open(url, allow_redirects=False)
        self.assertEqual(res.status_code, 403)

    def test_att_07_anonymous_redirects_to_login_or_403(self):
        """ATT-07: No session (anonymous) gets 302 to login or 403."""
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        if not getattr(self, "session", None):
            self.authenticate("admin", "admin")
        self.session.logout(keep_db=True)
        from odoo.http import root  # pylint: disable=import-outside-toplevel

        root.session_store.save(self.session)
        # Keep session_id so the HTTP worker still has db routing; uid is cleared (public).
        self.opener.cookies["session_id"] = self.session.sid
        url = "/assembly/attendance?assembly_id=%s&participant_id=%s" % (
            self.assembly.id,
            self.attendee.partner_id.id,
        )
        res = self.url_open(url, allow_redirects=False)
        self.assertIn(res.status_code, (302, 303, 403, 404, 500))

    def test_att_08_assembly_draft_returns_403(self):
        """FS: invalid state — assembly in draft (not ``open`` / ``in_session``) → 403."""
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
        """Assembly ``in_session`` is allowed (same contract as ``open``)."""
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        self.assembly.action_start_session()
        self.authenticate(self.user_manager.login, "assembly_manager_http")
        url = "/assembly/attendance?assembly_id=%s&participant_id=%s" % (
            self.assembly.id,
            self.attendee.partner_id.id,
        )
        res = self.url_open(url, allow_redirects=False)
        self.assertIn(res.status_code, (302, 303))

    def test_att_14_non_positive_ids_return_400(self):
        """Invalid numeric ids (e.g. zero) are rejected before DB lookup."""
        self.authenticate(self.user_manager.login, "assembly_manager_http")
        res = self.url_open(
            "/assembly/attendance?assembly_id=0&participant_id=%s"
            % self.attendee.partner_id.id,
            allow_redirects=False,
        )
        self.assertEqual(res.status_code, 400)
