# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
# pylint: disable=invalid-name,import-outside-toplevel,consider-using-from-import,protected-access

"""Base ``HttpCase`` for HTTP tests in this module.

Provides a sample assembly, attendees, and users (manager / assembly user). The
mandatory contract for ``GET /assembly/attendance`` is asserted with concrete
status codes (without :meth:`_skip_if_route_404`).

:meth:`_skip_if_route_404` is for optional or environment-dependent routes
(portal, public display, HTTP voting), not for the manager deep link.
"""

import unittest

from odoo.tests import HttpCase

from .common import AssemblyTestMixin


class AssemblyHttpCase(AssemblyTestMixin, HttpCase):
    """Shared setup: HTTP server, logins, ``assembly`` + ``attendee``."""

    @classmethod
    def setUpClass(cls):
        try:
            from odoo.service import server  # pylint: disable=import-outside-toplevel

            if not getattr(getattr(server, "server", None), "httpd", None):
                raise unittest.SkipTest(
                    "HTTP server not running (e.g. --stop-after-init)"
                )
        except (AttributeError, TypeError) as exc:
            raise unittest.SkipTest("HTTP server not running") from exc
        super().setUpClass()
        cls.group_user = cls.env.ref("base_assembly.assembly_group_user")
        cls.group_manager = cls.env.ref("base_assembly.assembly_group_manager")
        cls.base_user = cls.env.ref("base.group_user")
        cls.group_portal = cls.env.ref("base.group_portal", raise_if_not_found=False)

        try:
            cls.user_manager = cls.env["res.users"].create(
                {
                    "name": "Assembly Manager HTTP",
                    "login": "assembly_manager_http",
                    "password": "assembly_manager_http",
                    "groups_id": [(6, 0, [cls.base_user.id, cls.group_manager.id])],
                }
            )
            cls.user_assembly_user = cls.env["res.users"].create(
                {
                    "name": "Assembly User HTTP",
                    "login": "assembly_user_http",
                    "password": "assembly_user_http",
                    "groups_id": [(6, 0, [cls.base_user.id, cls.group_user.id])],
                }
            )
        except Exception as e:
            if "calendar_default_privacy" in str(e) or "not null" in str(e).lower():
                raise unittest.SkipTest(
                    "res.users.settings requires calendar_default_privacy"
                ) from e
            raise
        mixin = AssemblyTestMixin()
        mixin.env = cls.env
        cls.assembly, cls.agenda = mixin._create_assembly_with_agenda()
        cls.assembly.action_generate_attendees()
        cls.attendee = cls.assembly.attendee_ids[0]
        if cls.group_portal:
            cls.portal_partner = cls.env["res.partner"].create(
                {"name": "Portal User", "is_company": False}
            )
            cls.user_portal = cls.env["res.users"].create(
                {
                    "name": "Portal User",
                    "login": "portal_assembly_http",
                    "password": "portal_assembly_http",
                    "groups_id": [(6, 0, [cls.group_portal.id])],
                    "partner_id": cls.portal_partner.id,
                }
            )
        else:
            cls.portal_partner = None
            cls.user_portal = None

    def _skip_if_route_404(self, response, route_description):
        """Skip the test if the response is 404 (routes not always deployed)."""
        if response.status_code == 404:
            self.skipTest("Route not implemented: %s" % route_description)
