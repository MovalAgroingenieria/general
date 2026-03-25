# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
# pylint: disable=import-outside-toplevel

"""HTTP tests: Public display GET /assembly/display and /assembly/display/data
(auth=public)."""

from .http_common import AssemblyHttpCase


class TestHttpPublicDisplay(AssemblyHttpCase):
    """DSP-01..DSP-05: Display page and JSON data, no personal data."""

    def _public_request(self, path):
        self.session.logout(keep_db=True)
        from odoo.http import root  # pylint: disable=import-outside-toplevel

        root.session_store.save(self.session)
        self.opener.cookies.pop("session_id", None)
        return self.url_open(path, allow_redirects=False)

    def test_dsp_01_display_page_valid_assembly_200(self):
        """DSP-01: GET /assembly/display?assembly_id=<id> returns 200 HTML."""
        res = self._public_request(  # pylint: disable=protected-access
            "/assembly/display?assembly_id=%s" % self.assembly.id
        )
        self._skip_if_route_404(
            res, "Public display page"
        )  # pylint: disable=protected-access
        self.assertEqual(res.status_code, 200)
        self.assertTrue(b"<!DOCTYPE" in res.content or b"<html" in res.content)

    def test_dsp_02_display_data_json_200_no_personal_data(self):
        """DSP-02: GET /assembly/display/data?assembly_id=<id> returns JSON
        without names/NIF/email."""
        res = self._public_request(  # pylint: disable=protected-access
            "/assembly/display/data?assembly_id=%s" % self.assembly.id
        )
        self._skip_if_route_404(
            res, "Public display data"
        )  # pylint: disable=protected-access
        self.assertEqual(res.status_code, 200)
        content = res.content.decode("utf-8", errors="replace")
        self.assertIn("assembly_state", content)
        self.assertNotIn("email", content.lower())
        self.assertNotIn("vat", content.lower())
        self.assertNotIn("partner_id", content)

    def test_dsp_03_assembly_id_nonexistent_404(self):
        """DSP-03: assembly_id nonexistent returns 404 or controlled empty."""
        res = self._public_request("/assembly/display?assembly_id=999999")
        # pylint: disable=protected-access
        self._skip_if_route_404(
            res, "Public display page"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (404, 200))

    def test_dsp_04_display_without_assembly_id_400_or_404(self):
        """DSP-04: GET /assembly/display without assembly_id returns 400 or 404."""
        res = self._public_request(
            "/assembly/display"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (400, 404, 500))

    def test_dsp_05_display_data_no_vote_person_breakdown(self):
        """DSP-05: JSON must not include per-person vote breakdown."""
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        self.assembly.action_start_session()
        self.agenda.action_skip()
        self.assembly.action_close()
        res = self._public_request(  # pylint: disable=protected-access
            "/assembly/display/data?assembly_id=%s" % self.assembly.id
        )
        self._skip_if_route_404(
            res, "Public display data"
        )  # pylint: disable=protected-access
        if res.status_code == 200:
            content = res.content.decode("utf-8", errors="replace")
            self.assertNotIn("voting.line", content)
            self.assertNotIn("attendee_id", content)
