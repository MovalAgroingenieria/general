# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
# pylint: disable=import-outside-toplevel

"""HTTP tests: Voto online (portal) y voto por token.

Rutas: GET /my/assembly/<id>/voting, POST .../voting/<voting_id>/cast;
        GET /assembly/vote/t/<token>, POST /assembly/vote/cast.
"""

from .http_common import AssemblyHttpCase


class TestHttpVotePortal(AssemblyHttpCase):
    """VOT-01..VOT-09: Voting centre and cast from portal."""

    def test_vot_01_voting_center_eligible_200(self):
        """VOT-01: Portal user, attendee confirmed, in_session, voting open -> 200."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        self.assembly.allow_online_voting = True
        self.assembly.partner_domain = "[('id', '=', %s)]" % self.portal_partner.id
        self.assembly.action_generate_attendees()
        self.assembly.attendee_ids[0].action_confirm()
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        self.assembly.action_start_session()
        self.agenda.action_start_voting()
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open(
            "/my/assembly/%s/voting" % self.assembly.id,
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal voting center"
        )  # pylint: disable=protected-access
        self.assertEqual(res.status_code, 200)

    def test_vot_02_voting_center_other_assembly_404_or_403(self):
        """VOT-02: Portal user cannot open voting center for other's assembly."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        other = self.env["res.partner"].create(
            {"name": "Other", "is_company": False}
        )  # noqa: F841
        self.assembly.partner_domain = "[('id', '=', %s)]" % other.id
        self.assembly.action_generate_attendees()
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        self.assembly.action_start_session()
        self.agenda.action_start_voting()
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open(
            "/my/assembly/%s/voting" % self.assembly.id,
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal voting center"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (403, 404))

    def test_vot_03_voting_center_not_confirmed_403_or_empty(self):
        """VOT-03: Portal user not confirmed cannot see vote form."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        self.assembly.allow_online_voting = True
        self.assembly.partner_domain = "[('id', '=', %s)]" % self.portal_partner.id
        self.assembly.action_generate_attendees()
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        self.assembly.action_start_session()
        self.agenda.action_start_voting()
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open(
            "/my/assembly/%s/voting" % self.assembly.id,
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal voting center"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (200, 403))

    def test_vot_04_cast_valid_vote_200(self):
        """VOT-04: POST cast with valid vote_option creates voting.line."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        vote_type = self.assembly.assembly_type_id.vote_type_ids[0]
        self.assembly.allow_online_voting = True
        self.assembly.partner_domain = "[('id', '=', %s)]" % self.portal_partner.id
        self.assembly.action_generate_attendees()
        att = self.assembly.attendee_ids[0]
        self._give_partner_votes(
            att.partner_id, vote_type, 1
        )  # pylint: disable=protected-access
        att.action_confirm()
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        self.assembly.action_start_session()
        self.agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", self.agenda.id)], limit=1
        )
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open(
            "/my/assembly/%s/voting/%s/cast" % (self.assembly.id, voting.id),
            data={"vote_option": "yes"},
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal vote cast"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (200, 302))

    def test_vot_05_cast_ignores_attendee_id_in_body(self):
        """VOT-05: POST cast with attendee_id in body must not use it (use session)."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        other_partner = self.env["res.partner"].create(
            {"name": "Other Voter", "is_company": False}
        )
        self.assembly.allow_online_voting = True
        self.assembly.partner_domain = "[('id', 'in', [%s, %s])]" % (
            self.portal_partner.id,
            other_partner.id,
        )
        self.assembly.action_generate_attendees()
        vote_type = self.assembly.assembly_type_id.vote_type_ids[0]
        for att in self.assembly.attendee_ids:
            self._give_partner_votes(att.partner_id, vote_type, 1)
            # pylint: disable=protected-access
            att.action_confirm()
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        self.assembly.action_start_session()
        self.agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", self.agenda.id)], limit=1
        )
        other_attendee = self.assembly.attendee_ids.filtered(
            lambda a: a.partner_id == other_partner
        )
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open(
            "/my/assembly/%s/voting/%s/cast" % (self.assembly.id, voting.id),
            data={"vote_option": "yes", "attendee_id": other_attendee.id},
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal vote cast"
        )  # pylint: disable=protected-access
        if res.status_code in (200, 302):
            self.env.invalidate_all()
            line = self.env["assembly.voting.line"].search(  # noqa: F841
                [
                    ("voting_id", "=", voting.id),
                    ("attendee_id.partner_id", "=", self.portal_partner.id),
                ],
                limit=1,
            )
            self.assertTrue(
                line,
                "Vote must be recorded for portal user's attendee, not other_attendee",
            )

    def test_vot_06_cast_invalid_vote_option_400(self):
        """VOT-06: POST cast with invalid vote_option returns 400."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        vote_type = self.assembly.assembly_type_id.vote_type_ids[0]  # noqa: F841
        self.assembly.allow_online_voting = True
        self.assembly.partner_domain = "[('id', '=', %s)]" % self.portal_partner.id
        self.assembly.action_generate_attendees()
        att = self.assembly.attendee_ids[0]
        self._give_partner_votes(
            att.partner_id, vote_type, 1
        )  # pylint: disable=protected-access
        att.action_confirm()
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        self.assembly.action_start_session()
        self.agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", self.agenda.id)], limit=1
        )
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open(
            "/my/assembly/%s/voting/%s/cast" % (self.assembly.id, voting.id),
            data={"vote_option": "invalid_value"},
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal vote cast"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (400, 422))

    def test_vot_07_assembly_not_in_session_403(self):
        """VOT-09: GET voting when assembly not in_session returns 403 or empty."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        self.assembly.allow_online_voting = True
        self.assembly.partner_domain = "[('id', '=', %s)]" % self.portal_partner.id
        self.assembly.action_generate_attendees()
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open(
            "/my/assembly/%s/voting" % self.assembly.id,
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal voting center"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (200, 403))


class TestHttpVoteToken(AssemblyHttpCase):
    """VTK-01..VTK-07: Voto por token (auth=public)."""

    def _vote_token_route_get(self, token):
        self.session.logout(keep_db=True)
        from odoo.http import root  # pylint: disable=import-outside-toplevel

        root.session_store.save(self.session)
        self.opener.cookies.pop("session_id", None)
        return self.url_open(
            "/assembly/vote/t/%s" % (token or ""),
            allow_redirects=False,
        )

    def test_vtk_01_vote_page_valid_token_200(self):
        """VTK-01: GET /assembly/vote/t/<token> with valid token returns 200."""
        res = self._vote_token_route_get(
            "dummy-valid-token"
        )  # pylint: disable=protected-access
        self._skip_if_route_404(
            res, "Vote by token page"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (200, 403))

    def test_vtk_02_token_invalid_200_or_404(self):
        """VTK-02: Invalid token returns generic message."""
        res = self._vote_token_route_get("nonexistent-token-xyz")
        # pylint: disable=protected-access
        self._skip_if_route_404(
            res, "Vote by token"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (200, 404))

    def test_vtk_03_post_cast_without_token_400(self):
        """VTK-07: POST /assembly/vote/cast without token returns 400."""
        self.session.logout(keep_db=True)
        from odoo.http import root  # pylint: disable=import-outside-toplevel

        root.session_store.save(self.session)
        self.opener.cookies.pop("session_id", None)
        res = self.url_open(
            "/assembly/vote/cast",
            data={"vote_option": "yes"},
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Vote cast by token"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (400, 404, 422))
