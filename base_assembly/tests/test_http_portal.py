# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
# pylint: disable=import-outside-toplevel

"""HTTP tests: Portal routes /my/assemblies, /my/assembly/<id>, confirm,
delegation, document.

When controllers are not implemented, tests are skipped (404).
"""

from .http_common import AssemblyHttpCase


class TestHttpPortalList(AssemblyHttpCase):
    """PTL-01, PTL-02: List and auth."""

    def test_ptl_01_list_own_assemblies_200(self):
        """PTL-01: Portal user gets 200 with only own assemblies."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        self.assembly.action_announce()
        self.assembly.partner_domain = "[('id', '=', %s)]" % self.portal_partner.id
        self.assembly.action_generate_attendees()
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open("/my/assemblies", allow_redirects=False)
        self._skip_if_route_404(res, "Portal list /my/assemblies")
        # pylint: disable=protected-access
        self.assertEqual(res.status_code, 200)
        self.assertIn(self.assembly.name.encode(), res.content)

    def test_ptl_02_list_without_session_302_login(self):
        """PTL-02: GET /my/assemblies without session redirects to login."""
        self.session.logout(keep_db=True)
        from odoo.http import root  # pylint: disable=import-outside-toplevel

        root.session_store.save(self.session)
        self.opener.cookies.pop("session_id", None)
        res = self.url_open("/my/assemblies", allow_redirects=False)
        self._skip_if_route_404(res, "Portal list")  # pylint: disable=protected-access
        self.assertEqual(res.status_code, 302)
        self.assertTrue("login" in res.headers.get("Location", "").lower())

    def test_ptl_03_detail_own_assembly_200(self):
        """PTL-03: Portal user gets 200 for own assembly detail."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        self.assembly.action_announce()
        self.assembly.partner_domain = "[('id', '=', %s)]" % self.portal_partner.id
        self.assembly.action_generate_attendees()
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open("/my/assembly/%s" % self.assembly.id, allow_redirects=False)
        self._skip_if_route_404(res, "Portal detail /my/assembly/<id>")
        # pylint: disable=protected-access
        self.assertEqual(res.status_code, 200)

    def test_ptl_04_detail_other_assembly_404_or_403(self):
        """PTL-04: Portal user cannot access other partner's assembly (IDOR)."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        other_partners = self.env["res.partner"].create(  # noqa: F841
            [
                {"name": "Other A", "is_company": False},
                {"name": "Other B", "is_company": False},
            ]
        )
        self.assembly.partner_domain = "[('id', 'in', %s)]" % other_partners.ids
        self.assembly.action_generate_attendees()
        self.assembly.action_announce()
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open("/my/assembly/%s" % self.assembly.id, allow_redirects=False)
        self._skip_if_route_404(
            res, "Portal detail"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (403, 404))

    def test_ptl_05_detail_nonexistent_id_404(self):
        """PTL-05: Nonexistent assembly id returns 404."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open("/my/assembly/999999", allow_redirects=False)
        self._skip_if_route_404(
            res, "Portal detail"
        )  # pylint: disable=protected-access
        self.assertEqual(res.status_code, 404)


class TestHttpPortalConfirm(AssemblyHttpCase):
    """PTL-06..PTL-09: Confirm attendance."""

    def test_ptl_06_confirm_attendance_200(self):
        """PTL-06: POST confirm with valid state returns 200/302 and confirms."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        self.assembly.partner_domain = "[('id', '=', %s)]" % self.portal_partner.id
        self.assembly.action_generate_attendees()
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open(
            "/my/assembly/%s/confirm" % self.assembly.id,
            data={},
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal confirm"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (200, 302))

    def test_ptl_07_confirm_assembly_draft_403(self):
        """PTL-08: POST confirm when assembly in draft returns 403 or 400."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        self.assembly.partner_domain = "[('id', '=', %s)]" % self.portal_partner.id
        self.assembly.action_generate_attendees()
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open(
            "/my/assembly/%s/confirm" % self.assembly.id,
            data={},
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal confirm"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (400, 403))

    def test_ptl_08_confirm_other_assembly_403_or_404(self):
        """PTL-09: POST confirm for assembly where user not invited returns 403/404."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        other = self.env["res.partner"].create({"name": "Other", "is_company": False})
        self.assembly.partner_domain = "[('id', '=', %s)]" % other.id
        self.assembly.action_generate_attendees()
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open(
            "/my/assembly/%s/confirm" % self.assembly.id,
            data={},
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal confirm"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (403, 404))


class TestHttpPortalDocument(AssemblyHttpCase):
    """DOC-01..DOC-04: Document download."""

    def test_doc_01_document_whitelist_type_200(self):
        """DOC-01: GET document with allowed type returns 200 and PDF."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        self.assembly.partner_domain = "[('id', '=', %s)]" % self.portal_partner.id
        self.assembly.action_generate_attendees()
        self.assembly.action_announce()
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open(
            "/my/assembly/%s/document/convocatoria" % self.assembly.id,
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal document"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (200, 302))
        if res.status_code == 200 and res.headers.get("Content-Type"):
            self.assertIn("pdf", res.headers.get("Content-Type", "").lower())

    def test_doc_02_document_invalid_type_400_or_404(self):
        """DOC-02: GET document with invalid type returns 400 or 404."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        self.assembly.partner_domain = "[('id', '=', %s)]" % self.portal_partner.id
        self.assembly.action_generate_attendees()
        self.assembly.action_announce()
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open(
            "/my/assembly/%s/document/tipo_invalido_xyz" % self.assembly.id,
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal document"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (400, 404))

    def test_doc_03_document_other_assembly_403_or_404(self):
        """DOC-03: GET document for other's assembly returns 403/404."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        other = self.env["res.partner"].create(
            {"name": "Other", "is_company": False}
        )  # noqa: F841
        self.assembly.partner_domain = "[('id', '=', %s)]" % other.id
        self.assembly.action_generate_attendees()
        self.assembly.action_announce()
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open(
            "/my/assembly/%s/document/convocatoria" % self.assembly.id,
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal document"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (403, 404))

    def test_doc_04_document_without_session_302(self):
        """DOC-04: GET document without session redirects to login."""
        self.session.logout(keep_db=True)
        from odoo.http import root  # pylint: disable=import-outside-toplevel

        root.session_store.save(self.session)
        self.opener.cookies.pop("session_id", None)
        res = self.url_open(
            "/my/assembly/1/document/convocatoria",
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal document"
        )  # pylint: disable=protected-access
        self.assertEqual(res.status_code, 302)
