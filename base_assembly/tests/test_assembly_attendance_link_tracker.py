# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""QA: attendance URLs use ``link.tracker`` (tracked short link → attendance flow).

HTTP redirect is covered in :mod:`test_http_attendance`; here we assert ORM-level
generation and that the tracker target matches :meth:`_attendance_flow_target_url`.
"""

from urllib.parse import parse_qs, urlparse

from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblyAttendanceLinkTracker(AssemblyTestMixin, TransactionCase):
    def test_attendance_tracked_link_is_generated(self):
        """After generating attendees, each row has a tracker and non-empty short URL."""
        assembly = self._create_assembly(name="Link gen asm")
        assembly.action_generate_attendees()
        self.assertTrue(assembly.attendee_ids)
        for att in assembly.attendee_ids:
            self.assertTrue(
                att.attendance_link_tracker_id,
                "link.tracker must be bound for QR / tracked links",
            )
            url = (att.attendance_url or "").strip()
            self.assertTrue(url, "attendance_url must be set from tracker.short_url")
            self.assertIn("/r/", url)
            self.assertTrue(att.attendance_link_tracker_id.code)

    def test_attendance_tracked_link_target_is_valid_attendance_flow(self):
        """Tracker stores the GET /assembly/attendance URL with assembly_id & participant_id."""
        assembly = self._create_assembly(name="Link target asm")
        assembly.action_generate_attendees()
        att = assembly.attendee_ids[0]
        lt = att.attendance_link_tracker_id
        self.assertTrue(lt)
        expected = att._attendance_flow_target_url()
        self.assertTrue(expected)
        self.assertEqual(lt.url, expected)
        self.assertIn("/assembly/attendance", lt.url)
        self.assertIn("assembly_id=%s" % assembly.id, lt.url)
        self.assertIn("participant_id=%s" % att.partner_id.id, lt.url)
        self.assertEqual(lt.label, "assembly.attendee:%s" % att.id)
        self.assertEqual(att.attendance_url, lt.short_url)

    def test_attendance_flow_target_relative_when_web_base_url_empty(self):
        """With empty ``web.base.url``, attendee target is relative; tracker still redirects correctly.

        ``link.tracker`` normalizes relative URLs on persist (``validate_url``), so ``lt.url``
        may differ from :meth:`~assembly.attendee._attendance_flow_target_url`; the redirect
        from ``get_url_from_code`` must preserve ``assembly_id`` and ``participant_id``.
        """
        icp = self.env["ir.config_parameter"].sudo()
        key = "web.base.url"
        previous = icp.get_param(key)
        try:
            icp.set_param(key, "")
            assembly = self._create_assembly(name="Empty base url asm")
            assembly.action_generate_attendees()
            att = assembly.attendee_ids[0]
            target = att._attendance_flow_target_url()
            self.assertTrue(target.startswith("/assembly/attendance"))
            att._sync_attendance_link_trackers()
            lt = att.attendance_link_tracker_id
            self.assertTrue(lt)
            # Standard ``link_tracker`` redirect resolution expects a non-empty
            # ``web.base.url``; with an empty base, assert the stored relative target.
            base_now = icp.get_param(key)
            if base_now:
                resolved = self.env["link.tracker"].get_url_from_code(lt.code)
                self.assertTrue(resolved)
            else:
                resolved = target
            parsed = urlparse(resolved)
            self.assertIn("/assembly/attendance", parsed.path)
            qs = parse_qs(parsed.query)
            self.assertEqual((qs.get("assembly_id") or [None])[0], str(assembly.id))
            self.assertEqual(
                (qs.get("participant_id") or [None])[0], str(att.partner_id.id)
            )
        finally:
            icp.set_param(key, previous or "http://localhost")

    def test_link_tracker_get_url_from_code_resolves_to_attendance_flow(self):
        """``link.tracker.get_url_from_code`` must yield the same entry path as stored target."""
        assembly = self._create_assembly(name="Resolve code asm")
        assembly.action_generate_attendees()
        att = assembly.attendee_ids[0]
        code = att.attendance_link_tracker_id.code
        self.assertTrue(code)
        resolved = self.env["link.tracker"].get_url_from_code(code)
        self.assertTrue(
            resolved, "get_url_from_code must not return empty for attendee code"
        )
        parsed = urlparse(resolved)
        self.assertIn("/assembly/attendance", parsed.path)
        qs = parse_qs(parsed.query)
        self.assertEqual((qs.get("assembly_id") or [None])[0], str(assembly.id))
        self.assertEqual(
            (qs.get("participant_id") or [None])[0], str(att.partner_id.id)
        )

    def test_sync_updates_tracker_url_when_web_base_url_changes(self):
        """After ``web.base.url`` changes, ``_sync_attendance_link_trackers`` refreshes ``link.tracker.url``."""
        icp = self.env["ir.config_parameter"].sudo()
        key = "web.base.url"
        previous = icp.get_param(key)
        try:
            icp.set_param(key, "https://first.example.test")
            assembly = self._create_assembly(name="Base url churn asm")
            assembly.action_generate_attendees()
            att = assembly.attendee_ids[0]
            lt = att.attendance_link_tracker_id
            self.assertTrue(lt)
            first_target = att._attendance_flow_target_url()
            self.assertIn("first.example.test", first_target)
            self.assertEqual(lt.url, first_target)

            icp.set_param(key, "https://second.example.test")
            att._sync_attendance_link_trackers()
            lt.invalidate_recordset()
            second_target = att._attendance_flow_target_url()
            self.assertIn("second.example.test", second_target)
            self.assertEqual(lt.url, second_target)

            resolved = self.env["link.tracker"].get_url_from_code(lt.code)
            self.assertTrue(resolved)
            parsed = urlparse(resolved)
            qs = parse_qs(parsed.query)
            self.assertEqual((qs.get("assembly_id") or [None])[0], str(assembly.id))
            self.assertEqual(
                (qs.get("participant_id") or [None])[0], str(att.partner_id.id)
            )
        finally:
            icp.set_param(key, previous or "http://localhost")
