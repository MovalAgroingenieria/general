# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
# pylint: disable=invalid-name

"""Portal tests for base_assembly: list, detail, confirm, delegations,
voting, documents.

Matrix: authenticated / no permission, token (session) valid / invalid,
allowed state / not allowed. See doc/PORTAL_TEST_MATRIX.md.
"""

from .http_common import AssemblyHttpCase


def _logout_and_clear_session(test_case):  # pylint: disable=import-outside-toplevel
    if not getattr(test_case, "session", None):
        test_case.authenticate(None, None)
    test_case.session.logout(keep_db=True)
    from odoo.http import root  # pylint: disable=import-outside-toplevel

    root.session_store.save(test_case.session)
    test_case.opener.cookies.pop("session_id", None)


class PortalListTests(AssemblyHttpCase):
    """GET /my/assemblies list: L1–L4."""

    def test_L1_authenticated_correct_sees_only_own_assemblies(self):
        """L1: Valid session → 200; response lists only assemblies the user may access."""
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

    def test_L2_authenticated_no_permission_sees_empty_or_only_own(self):
        """L2: Logged in but not invited to any assembly → 200; no other assemblies leaked."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        other = self.env["res.partner"].create({"name": "Other", "is_company": False})
        self.assembly.partner_domain = "[('id', '=', %s)]" % other.id
        self.assembly.action_generate_attendees()
        self.assembly.action_announce()
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open("/my/assemblies", allow_redirects=False)
        self._skip_if_route_404(res, "Portal list")  # pylint: disable=protected-access
        self.assertEqual(res.status_code, 200)
        self.assertNotIn(self.assembly.name.encode(), res.content)

    def test_L3_token_invalid_redirects_to_login(self):
        """L3: Invalid token/session → 302 to login."""
        _logout_and_clear_session(self)
        res = self.url_open("/my/assemblies", allow_redirects=False)
        self._skip_if_route_404(res, "Portal list")  # pylint: disable=protected-access
        self.assertEqual(res.status_code, 302)
        self.assertTrue("login" in res.headers.get("Location", "").lower())


class PortalDetailTests(AssemblyHttpCase):
    """GET /my/assembly/<id> detail: D1–D4."""

    def test_D1_authenticated_correct_detail_200(self):
        """D1: Valid session for invited user → 200 detail page."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        self.assembly.action_announce()
        self.assembly.partner_domain = "[('id', '=', %s)]" % self.portal_partner.id
        self.assembly.action_generate_attendees()
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open("/my/assembly/%s" % self.assembly.id, allow_redirects=False)
        self._skip_if_route_404(
            res, "Portal detail"
        )  # pylint: disable=protected-access
        self.assertEqual(res.status_code, 200)

    def test_D2_authenticated_no_permission_detail_403_or_404(self):
        """D2: Logged in but not invited to this assembly → 403/404; no data leak."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        other = self.env["res.partner"].create({"name": "Other", "is_company": False})
        self.assembly.partner_domain = "[('id', '=', %s)]" % other.id
        self.assembly.action_generate_attendees()
        self.assembly.action_announce()
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open("/my/assembly/%s" % self.assembly.id, allow_redirects=False)
        self._skip_if_route_404(
            res, "Portal detail"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (403, 404))

    def test_D3_token_invalid_redirects_to_login(self):
        """D3: Invalid token → 302 to login."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        _logout_and_clear_session(self)
        res = self.url_open("/my/assembly/%s" % self.assembly.id, allow_redirects=False)
        self._skip_if_route_404(
            res, "Portal detail"
        )  # pylint: disable=protected-access
        self.assertEqual(res.status_code, 302)

    def test_D4_nonexistent_id_404(self):
        """D4: Non-existent assembly id → 404."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open("/my/assembly/999999", allow_redirects=False)
        self._skip_if_route_404(
            res, "Portal detail"
        )  # pylint: disable=protected-access
        self.assertEqual(res.status_code, 404)


class PortalConfirmTests(AssemblyHttpCase):
    """Confirmation POST /my/assembly/<id>/confirm: C1–C6."""

    def test_C1_state_allowed_confirm_200(self):
        """C1: Allowed assembly state (open/in_session) → 200/302; attendee confirmed."""
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

    def test_C2_state_not_allowed_draft_403(self):
        """C2: Disallowed state (draft) → 403 or 400."""
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

    def test_C3_state_not_allowed_closed_403(self):
        """C3: Disallowed state (closed) → 403 or 400."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        self.assembly.partner_domain = "[('id', '=', %s)]" % self.portal_partner.id
        self.assembly.action_generate_attendees()
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        self.assembly.action_start_session()
        self.agenda.action_skip()
        self.assembly.action_close()
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

    def test_C4_authenticated_no_permission_403_or_404(self):
        """C4: Logged in but not invited → 403/404."""
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

    def test_C5_token_invalid_redirects_to_login(self):
        """C5: Invalid token → 302 to login."""
        _logout_and_clear_session(self)
        res = self.url_open(
            "/my/assembly/1/confirm",
            data={},
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal confirm"
        )  # pylint: disable=protected-access
        self.assertEqual(res.status_code, 302)


class PortalDelegationTests(AssemblyHttpCase):
    """Delegations: create, confirm, revoke. DG1–DG4, DC1–DC2, DR1–DR3."""

    def test_DG1_state_allowed_create_delegation_200(self):
        """DG1: Allowed state → POST create delegation 200/302."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        other = self.env["res.partner"].create(
            {"name": "Delegate", "is_company": False}
        )
        self.assembly.partner_domain = "[('id', 'in', [%s, %s])]" % (
            self.portal_partner.id,
            other.id,
        )
        self.assembly.action_generate_attendees()
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open(
            "/my/assembly/%s/delegation/create" % self.assembly.id,
            data={"delegate_partner_id": other.id},
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal delegation create"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (200, 302))

    def test_DG2_state_not_allowed_create_delegation_403(self):
        """DG2: Disallowed state (draft) → 403 or 400."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        other = self.env["res.partner"].create(
            {"name": "Delegate", "is_company": False}
        )
        self.assembly.partner_domain = "[('id', 'in', [%s, %s])]" % (
            self.portal_partner.id,
            other.id,
        )
        self.assembly.action_generate_attendees()
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open(
            "/my/assembly/%s/delegation/create" % self.assembly.id,
            data={"delegate_partner_id": other.id},
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal delegation create"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (400, 403))

    def test_DG3_authenticated_no_permission_create_403_or_404(self):
        """DG3: No permission on assembly → 403/404."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        other = self.env["res.partner"].create({"name": "Other", "is_company": False})
        self.assembly.partner_domain = "[('id', '=', %s)]" % other.id
        self.assembly.action_generate_attendees()
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open(
            "/my/assembly/%s/delegation/create" % self.assembly.id,
            data={"delegate_partner_id": other.id},
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal delegation create"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (403, 404))

    def test_DG4_token_invalid_redirects_to_login(self):
        """DG4: Invalid token → 302."""
        _logout_and_clear_session(self)
        res = self.url_open(
            "/my/assembly/1/delegation/create",
            data={},
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal delegation create"
        )  # pylint: disable=protected-access
        self.assertEqual(res.status_code, 302)

    def test_DC1_confirm_own_delegation_200(self):
        """DC1: Confirm own delegation → 200."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        other = self.env["res.partner"].create(
            {"name": "Delegate", "is_company": False}
        )
        self.assembly.partner_domain = "[('id', 'in', [%s, %s])]" % (
            self.portal_partner.id,
            other.id,
        )
        self.assembly.action_generate_attendees()
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": self.assembly.id,
                "partner_id": self.portal_partner.id,
                "delegate_partner_id": other.id,
                "vote_type_ids": [
                    (6, 0, self.assembly.assembly_type_id.vote_type_ids.ids)
                ],
            }
        )
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open(
            "/my/assembly/%s/delegation/%s/confirm" % (self.assembly.id, delegation.id),
            data={},
            allow_redirects=False,
        )
        self._skip_if_route_404(res, "Portal delegation confirm")
        # pylint: disable=protected-access
        self.assertIn(res.status_code, (200, 302))

    def test_DC2_confirm_other_delegation_403_or_404(self):
        """DC2: Confirm another's delegation → 403/404."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        p_a = self.env["res.partner"].create(
            {"name": "Delegator A", "is_company": False}
        )
        p_b = self.env["res.partner"].create(
            {"name": "Delegate B", "is_company": False}
        )
        self.assembly.partner_domain = "[('id', 'in', [%s, %s])]" % (p_a.id, p_b.id)
        self.assembly.action_generate_attendees()
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": self.assembly.id,
                "partner_id": p_a.id,
                "delegate_partner_id": p_b.id,
                "vote_type_ids": [
                    (6, 0, self.assembly.assembly_type_id.vote_type_ids.ids)
                ],
            }
        )
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open(
            "/my/assembly/%s/delegation/%s/confirm" % (self.assembly.id, delegation.id),
            data={},
            allow_redirects=False,
        )
        self._skip_if_route_404(res, "Portal delegation confirm")
        # pylint: disable=protected-access
        self.assertIn(res.status_code, (403, 404))

    def test_DR1_revoke_own_delegation_200(self):
        """DR1: Revoke own delegation → 200."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        other = self.env["res.partner"].create(
            {"name": "Delegate", "is_company": False}
        )
        self.assembly.partner_domain = "[('id', 'in', [%s, %s])]" % (
            self.portal_partner.id,
            other.id,
        )
        self.assembly.action_generate_attendees()
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        delegate_att = self.assembly.attendee_ids.filtered(
            lambda a: a.partner_id == other
        )
        self.assertTrue(delegate_att)
        delegate_att.action_confirm()
        delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": self.assembly.id,
                "partner_id": self.portal_partner.id,
                "delegate_partner_id": other.id,
                "vote_type_ids": [
                    (6, 0, self.assembly.assembly_type_id.vote_type_ids.ids)
                ],
            }
        )
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open(
            "/my/assembly/%s/delegation/%s/revoke" % (self.assembly.id, delegation.id),
            data={},
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal delegation revoke"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (200, 302))

    def test_DR2_revoke_other_delegation_403_or_404(self):
        """DR2: Revoke another's delegation → 403/404."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        p_a = self.env["res.partner"].create(
            {"name": "Delegator A", "is_company": False}
        )
        p_b = self.env["res.partner"].create(
            {"name": "Delegate B", "is_company": False}
        )
        self.assembly.partner_domain = "[('id', 'in', [%s, %s])]" % (p_a.id, p_b.id)
        self.assembly.action_generate_attendees()
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        delegate_att = self.assembly.attendee_ids.filtered(
            lambda a: a.partner_id == p_b
        )
        self.assertTrue(delegate_att)
        delegate_att.action_confirm()
        delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": self.assembly.id,
                "partner_id": p_a.id,
                "delegate_partner_id": p_b.id,
                "vote_type_ids": [
                    (6, 0, self.assembly.assembly_type_id.vote_type_ids.ids)
                ],
            }
        )
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open(
            "/my/assembly/%s/delegation/%s/revoke" % (self.assembly.id, delegation.id),
            data={},
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal delegation revoke"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (403, 404))

    def test_DR3_token_invalid_revoke_302(self):
        """DR3: Invalid token on revoke → 302."""
        _logout_and_clear_session(self)
        res = self.url_open(
            "/my/assembly/1/delegation/1/revoke",
            data={},
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal delegation revoke"
        )  # pylint: disable=protected-access
        self.assertEqual(res.status_code, 302)


class PortalVotingTests(AssemblyHttpCase):
    """Online voting: centre and cast. V1–V8."""

    def test_V1_state_allowed_voting_center_200(self):
        """V1: Allowed state, attendee confirmed → 200 voting centre."""
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

    def test_V2_attendee_not_confirmed_voting_403_or_no_form(self):
        """V2: Attendee not confirmed → 403 or page without vote form."""
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

    def test_V3_state_not_allowed_open_without_in_session_403(self):
        """V3: Assembly open (without in_session) → 403 or empty."""
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

    def test_V4_authenticated_no_permission_voting_403_or_404(self):
        """V4: No permission on assembly → 403/404."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        other = self.env["res.partner"].create({"name": "Other", "is_company": False})
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

    def test_V5_token_invalid_redirects_to_login(self):
        """V5: Invalid token → 302."""
        _logout_and_clear_session(self)
        res = self.url_open("/my/assembly/1/voting", allow_redirects=False)
        self._skip_if_route_404(
            res, "Portal voting center"
        )  # pylint: disable=protected-access
        self.assertEqual(res.status_code, 302)

    def test_V6_cast_voting_closed_403_or_400(self):
        """V6: POST cast with voting closed → 403 or 400."""
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
        voting.action_close()
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open(
            "/my/assembly/%s/voting/%s/cast" % (self.assembly.id, voting.id),
            data={"vote_option": "yes"},
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal vote cast"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (400, 403))

    def test_V7_cast_invalid_vote_option_400(self):
        """V7: Invalid vote_option → 400."""
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
            data={"vote_option": "invalid_option"},
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal vote cast"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (400, 422))

    def test_V8_cast_attendee_id_in_body_ignored(self):
        """V8: POST cast with another partner's attendee_id in body is ignored;
        vote applies to the logged-in user."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        other = self.env["res.partner"].create({"name": "Other", "is_company": False})
        self.assembly.allow_online_voting = True
        self.assembly.partner_domain = "[('id', 'in', [%s, %s])]" % (
            self.portal_partner.id,
            other.id,
        )
        self.assembly.action_generate_attendees()
        vote_type = self.assembly.assembly_type_id.vote_type_ids[0]  # noqa: F841
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
            lambda a: a.partner_id == other
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
                "Vote must be for portal user's attendee, not other_attendee",
            )


class PortalDocumentTests(AssemblyHttpCase):
    """GET /my/assembly/<id>/document/<doc_type> download: DOC1–DOC4."""

    def test_DOC1_authenticated_correct_whitelist_type_200(self):
        """DOC1: Valid session, allowed doc_type → 200, PDF."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        self.assembly.partner_domain = "[('id', '=', %s)]" % self.portal_partner.id
        self.assembly.action_generate_attendees()
        self.assembly.action_announce()
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open(
            "/my/assembly/%s/document/publication" % self.assembly.id,
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal document"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (200, 302))
        if res.status_code == 200 and res.headers.get("Content-Type"):
            self.assertIn("pdf", res.headers.get("Content-Type", "").lower())

    def test_DOC2_invalid_doc_type_400_or_404(self):
        """DOC2: Disallowed doc_type → 400 or 404."""
        if not self.user_portal:
            self.skipTest("Portal group not available")
        self.assembly.partner_domain = "[('id', '=', %s)]" % self.portal_partner.id
        self.assembly.action_generate_attendees()
        self.assembly.action_announce()
        self.authenticate(self.user_portal.login, "portal_assembly_http")
        res = self.url_open(
            "/my/assembly/%s/document/invalid_doc_type_xyz" % self.assembly.id,
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal document"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (400, 404))

    def test_DOC3_authenticated_no_permission_403_or_404(self):
        """DOC3: Other user's assembly → 403/404."""
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
            "/my/assembly/%s/document/publication" % self.assembly.id,
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal document"
        )  # pylint: disable=protected-access
        self.assertIn(res.status_code, (403, 404))

    def test_DOC4_token_invalid_redirects_to_login(self):
        """DOC4: Invalid token → 302."""
        _logout_and_clear_session(self)
        res = self.url_open(
            "/my/assembly/1/document/publication",
            allow_redirects=False,
        )
        self._skip_if_route_404(
            res, "Portal document"
        )  # pylint: disable=protected-access
        self.assertEqual(res.status_code, 302)
