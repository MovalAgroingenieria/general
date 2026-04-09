# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Vote recompute: delegator without attendee row transfers only ``partner.vote`` to the delegate."""

from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestVoteRecomputeNonAttendeeDelegator(AssemblyTestMixin, TransactionCase):
    """``delegated_in`` from partner.vote; no attendee.vote rows for external delegator."""

    @staticmethod
    def _vote_lines_for_partner_on_assembly(env, assembly, partner):
        AttVote = env["assembly.attendee.vote"].sudo()
        attendees = env["assembly.attendee"].search(
            [
                ("assembly_id", "=", assembly.id),
                ("partner_id", "=", partner.id),
            ]
        )
        if not attendees:
            return AttVote.browse()
        return AttVote.search([("attendee_id", "in", attendees.ids)])

    def _setup_assembly_with_excluded_delegator(self):
        """Delegator excluded from attendee generation; delegate and another partner convoked."""
        env = self.env
        p_del = env["res.partner"].create(
            {"name": "ExtDelegator", "is_company": False, "assembly_excluded": True}
        )
        p_def = env["res.partner"].create(
            {"name": "DelegateAtt", "is_company": False, "assembly_excluded": False}
        )
        p_other = env["res.partner"].create(
            {"name": "OtherAtt", "is_company": False, "assembly_excluded": False}
        )
        domain = "[('id', 'in', %s)]" % ([p_del.id, p_def.id, p_other.id],)
        assembly, _ = self._create_assembly_with_agenda(partner_domain=domain)
        assembly.action_generate_attendees()
        self.assertFalse(
            assembly.attendee_ids.filtered(lambda a: a.partner_id == p_del),
            "Excluded delegator must not have an attendee row",
        )
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        return assembly, vote_type, p_del, p_def, p_other

    def test_non_attendee_delegator_transfers_own_partner_vote_to_delegate(self):
        """(1)(2) No delegator attendee row: delegate receives delegated_in from partner.vote."""
        assembly, vote_type, p_del, p_def, _p_other = (
            self._setup_assembly_with_excluded_delegator()
        )
        self._give_partner_votes(p_del, vote_type, 10)
        self._give_partner_votes(p_def, vote_type, 4)
        delegate_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_def)
        delegate_att.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": p_del.id,
                "delegate_partner_id": p_def.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        delegate_att.recompute_attendee_vote_lines()
        lines_del = self._vote_lines_for_partner_on_assembly(self.env, assembly, p_del)
        self.assertFalse(
            lines_del,
            "Delegator without attendee row must not have assembly.attendee.vote",
        )
        line_def = self._vote_lines_for_partner_on_assembly(
            self.env, assembly, p_def
        ).filtered(lambda r: r.vote_type_id == vote_type)
        self.assertTrue(line_def)
        self.assertEqual(line_def.delegated_in_votes, 10.0)
        self.assertEqual(line_def.own_votes, 4.0)

    def test_batch_recompute_all_attendees_non_attendee_delegator_transfers(self):
        """QA: ``assembly.attendee_ids.recompute`` without delegator row still sums partner.vote."""
        assembly, vote_type, p_del, p_def, _p_other = (
            self._setup_assembly_with_excluded_delegator()
        )
        self._give_partner_votes(p_del, vote_type, 10)
        self._give_partner_votes(p_def, vote_type, 4)
        delegate_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_def)
        delegate_att.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": p_del.id,
                "delegate_partner_id": p_def.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        assembly.attendee_ids.recompute_attendee_vote_lines()
        self.assertFalse(
            self._vote_lines_for_partner_on_assembly(self.env, assembly, p_del),
        )
        line_def = self._vote_lines_for_partner_on_assembly(
            self.env, assembly, p_def
        ).filtered(lambda r: r.vote_type_id == vote_type)
        self.assertEqual(line_def.delegated_in_votes, 10.0)

    def test_removed_delegation_does_not_transfer(self):
        """(5) After unlink, inbound delegation no longer counts."""
        assembly, vote_type, p_del, p_def, _p_other = (
            self._setup_assembly_with_excluded_delegator()
        )
        self._give_partner_votes(p_del, vote_type, 10)
        self._give_partner_votes(p_def, vote_type, 4)
        delegate_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_def)
        delegate_att.action_confirm()
        del_rec = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": p_del.id,
                "delegate_partner_id": p_def.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        delegate_att.recompute_attendee_vote_lines()
        line_def = self._vote_lines_for_partner_on_assembly(
            self.env, assembly, p_def
        ).filtered(lambda r: r.vote_type_id == vote_type)
        self.assertEqual(line_def.delegated_in_votes, 10.0)
        del_rec.unlink()
        delegate_att.recompute_attendee_vote_lines()
        line_def = self._vote_lines_for_partner_on_assembly(
            self.env, assembly, p_def
        ).filtered(lambda r: r.vote_type_id == vote_type)
        self.assertEqual(line_def.delegated_in_votes, 0.0)

    def test_without_delegation_no_transfer(self):
        """(5) No delegation row → no inbound transfer."""
        assembly, vote_type, p_del, p_def, _p_other = (
            self._setup_assembly_with_excluded_delegator()
        )
        self._give_partner_votes(p_del, vote_type, 10)
        self._give_partner_votes(p_def, vote_type, 4)
        delegate_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_def)
        delegate_att.action_confirm()
        delegate_att.recompute_attendee_vote_lines()
        line_def = self._vote_lines_for_partner_on_assembly(
            self.env, assembly, p_def
        ).filtered(lambda r: r.vote_type_id == vote_type)
        self.assertEqual(line_def.delegated_in_votes, 0.0)

    def test_registered_delegator_contributes_delegated_in(self):
        """Delegator left in registered state still contributes ``partner.vote`` to confirmed delegate."""
        env = self.env
        p_del = env["res.partner"].create(
            {"name": "RegDelegator", "is_company": False, "assembly_excluded": False}
        )
        p_def = env["res.partner"].create(
            {"name": "DelConfirm", "is_company": False, "assembly_excluded": False}
        )
        p_other = env["res.partner"].create(
            {"name": "OtherM", "is_company": False, "assembly_excluded": False}
        )
        domain = "[('id', 'in', %s)]" % ([p_del.id, p_def.id, p_other.id],)
        assembly, _ = self._create_assembly_with_agenda(partner_domain=domain)
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        self._give_partner_votes(p_del, vote_type, 8)
        self._give_partner_votes(p_def, vote_type, 2)
        delegate_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_def)
        delegate_att.action_confirm()
        del_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_del)
        self.assertEqual(del_att.attendee_state, "registered")
        env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": p_del.id,
                "delegate_partner_id": p_def.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        delegate_att.recompute_attendee_vote_lines()
        line_def = self._vote_lines_for_partner_on_assembly(
            env, assembly, p_def
        ).filtered(lambda r: r.vote_type_id == vote_type)
        self.assertEqual(line_def.delegated_in_votes, 8.0)

    def test_delegator_becomes_confirmed_attendee_no_duplicate_delegate_totals(self):
        """(3)(4) After delegator is added and confirmed, delegate totals stay deduplicated."""
        assembly, vote_type, p_del, p_def, _p_other = (
            self._setup_assembly_with_excluded_delegator()
        )
        self._give_partner_votes(p_del, vote_type, 10)
        self._give_partner_votes(p_def, vote_type, 3)
        delegate_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_def)
        delegate_att.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": p_del.id,
                "delegate_partner_id": p_def.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        delegate_att.recompute_attendee_vote_lines()
        line_def = self._vote_lines_for_partner_on_assembly(
            self.env, assembly, p_def
        ).filtered(lambda r: r.vote_type_id == vote_type)
        total_before = line_def.attendee_vote_total
        self.assertEqual(total_before, 13.0)  # 3 own + 10 in

        p_del.write({"assembly_excluded": False})
        assembly.action_generate_attendees()
        delegator_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_del)
        self.assertTrue(delegator_att)
        delegator_att.action_confirm()

        assembly.attendee_ids.recompute_attendee_vote_lines()
        line_def.invalidate_recordset()
        line_def = self._vote_lines_for_partner_on_assembly(
            self.env, assembly, p_def
        ).filtered(lambda r: r.vote_type_id == vote_type)
        line_del = self._vote_lines_for_partner_on_assembly(
            self.env, assembly, p_del
        ).filtered(lambda r: r.vote_type_id == vote_type)
        self.assertTrue(line_del)
        self.assertEqual(
            line_def.delegated_in_votes,
            10.0,
            "delegated_in remains only delegator partner.vote",
        )
        self.assertEqual(
            line_def.attendee_vote_total,
            13.0,
            "Regression duplicate: delegate total must not jump to 23",
        )
        self.assertEqual(line_del.delegated_out_votes, 10.0)

    def test_regression_delegate_inbound_sum_not_doubled_after_delegator_confirms(self):
        """Regression: single contribution of 10 in delegated_in after delegator confirms."""
        assembly, vote_type, p_del, p_def, _p_other = (
            self._setup_assembly_with_excluded_delegator()
        )
        self._give_partner_votes(p_del, vote_type, 10)
        self._give_partner_votes(p_def, vote_type, 2)
        delegate_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_def)
        delegate_att.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": p_del.id,
                "delegate_partner_id": p_def.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        delegate_att.recompute_attendee_vote_lines()
        p_del.write({"assembly_excluded": False})
        assembly.action_generate_attendees()
        assembly.attendee_ids.filtered(lambda a: a.partner_id == p_del).action_confirm()
        assembly.attendee_ids.recompute_attendee_vote_lines()

        delegate_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_def)
        self.assertEqual(
            self.env["assembly.attendee.vote"].search_count(
                [
                    ("attendee_id", "in", delegate_att.ids),
                    ("vote_type_id", "=", vote_type.id),
                ]
            ),
            1,
            "Single persisted row (attendee, vote type)",
        )
        line_def = self._vote_lines_for_partner_on_assembly(
            self.env, assembly, p_def
        ).filtered(lambda r: r.vote_type_id == vote_type)
        self.assertEqual(line_def.delegated_in_votes, 10.0)
        n_inbound = self.env["assembly.delegation"].search_count(
            [
                ("assembly_id", "=", assembly.id),
                ("delegate_partner_id", "=", p_def.id),
            ]
        )
        self.assertEqual(n_inbound, 1)

    def test_delegated_in_sums_only_delegators_partner_vote(self):
        """(4) Several external delegators: ``delegated_in`` = sum of their ``partner.vote``."""
        env = self.env
        p_a = env["res.partner"].create(
            {"name": "ExtDelA", "is_company": False, "assembly_excluded": True}
        )
        p_b = env["res.partner"].create(
            {"name": "ExtDelB", "is_company": False, "assembly_excluded": True}
        )
        p_def = env["res.partner"].create(
            {"name": "DelegateBoth", "is_company": False, "assembly_excluded": False}
        )
        domain = "[('id', 'in', %s)]" % ([p_a.id, p_b.id, p_def.id],)
        assembly, _agenda = self._create_assembly_with_agenda(partner_domain=domain)
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        self._give_partner_votes(p_a, vote_type, 7)
        self._give_partner_votes(p_b, vote_type, 3)
        self._give_partner_votes(p_def, vote_type, 1)
        delegate_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_def)
        delegate_att.action_confirm()
        Delegation = env["assembly.delegation"]
        Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": p_a.id,
                "delegate_partner_id": p_def.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": p_b.id,
                "delegate_partner_id": p_def.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        assembly.attendee_ids.recompute_attendee_vote_lines()
        line_def = self._vote_lines_for_partner_on_assembly(
            env, assembly, p_def
        ).filtered(lambda r: r.vote_type_id == vote_type)
        self.assertEqual(line_def.delegated_in_votes, 10.0)
        self.assertEqual(line_def.own_votes, 1.0)
        self.assertEqual(line_def.attendee_vote_total, 11.0)


class TestNonAttendeeDelegatorMandatoryQA(TestVoteRecomputeNonAttendeeDelegator):
    """Mandatory QA: ``partner.vote`` source, no manual ``recompute``, no duplicates."""

    def test_mandatory_non_attendee_transfers_match_partner_vote_on_create_hook(self):
        """Delegator without attendee row: post-``create`` leaves ``delegated_in`` = ``partner.vote``."""
        assembly, vote_type, p_del, p_def, _p_other = (
            self._setup_assembly_with_excluded_delegator()
        )
        self._give_partner_votes(p_del, vote_type, 8)
        self._give_partner_votes(p_def, vote_type, 2)
        delegate_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_def)
        delegate_att.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": p_del.id,
                "delegate_partner_id": p_def.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        self.assertFalse(
            self._vote_lines_for_partner_on_assembly(self.env, assembly, p_del),
            "External delegator: no assembly.attendee.vote row",
        )
        pv = self.env["partner.vote"].search(
            [
                ("partner_id", "=", p_del.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        self.assertTrue(pv)
        line_def = self._vote_lines_for_partner_on_assembly(
            self.env, assembly, p_def
        ).filtered(lambda r: r.vote_type_id == vote_type)
        self.assertTrue(line_def)
        self.assertEqual(
            line_def.delegated_in_votes,
            float(pv.vote_count_display),
            "delegated_in must match delegator partner.vote",
        )

    def test_mandatory_unlink_delegation_clears_delegated_in_via_orm_hook(self):
        """Unlink triggers vote recompute without manual ``recompute_attendee_vote_lines``."""
        assembly, vote_type, p_del, p_def, _p_other = (
            self._setup_assembly_with_excluded_delegator()
        )
        self._give_partner_votes(p_del, vote_type, 6)
        self._give_partner_votes(p_def, vote_type, 1)
        delegate_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_def)
        delegate_att.action_confirm()
        del_rec = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": p_del.id,
                "delegate_partner_id": p_def.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        line_def = self._vote_lines_for_partner_on_assembly(
            self.env, assembly, p_def
        ).filtered(lambda r: r.vote_type_id == vote_type)
        self.assertEqual(line_def.delegated_in_votes, 6.0)
        del_rec.unlink()
        line_def = self._vote_lines_for_partner_on_assembly(
            self.env, assembly, p_def
        ).filtered(lambda r: r.vote_type_id == vote_type)
        self.assertEqual(line_def.delegated_in_votes, 0.0)

    def test_mandatory_delegator_becomes_attendee_recompute_votes_no_duplicate_inbound(
        self,
    ):
        """After delegator becomes attendee, ``recompute_votes`` does not duplicate ``delegated_in``."""
        Attendee = self.env["assembly.attendee"]
        assembly, vote_type, p_del, p_def, _p_other = (
            self._setup_assembly_with_excluded_delegator()
        )
        self._give_partner_votes(p_del, vote_type, 5)
        self._give_partner_votes(p_def, vote_type, 4)
        delegate_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_def)
        delegate_att.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": p_del.id,
                "delegate_partner_id": p_def.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        p_del.write({"assembly_excluded": False})
        assembly.action_generate_attendees()
        delegator_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_del)
        self.assertTrue(delegator_att)
        delegator_att.action_confirm()
        Attendee.recompute_votes(assembly.attendee_ids)
        line_def = self._vote_lines_for_partner_on_assembly(
            self.env, assembly, p_def
        ).filtered(lambda r: r.vote_type_id == vote_type)
        self.assertEqual(
            self.env["assembly.attendee.vote"].search_count(
                [
                    ("attendee_id", "=", delegate_att.id),
                    ("vote_type_id", "=", vote_type.id),
                ]
            ),
            1,
        )
        self.assertEqual(line_def.delegated_in_votes, 5.0)
        self.assertEqual(line_def.attendee_vote_total, 9.0)
        line_del = self._vote_lines_for_partner_on_assembly(
            self.env, assembly, p_del
        ).filtered(lambda r: r.vote_type_id == vote_type)
        self.assertEqual(line_del.delegated_out_votes, 5.0)
