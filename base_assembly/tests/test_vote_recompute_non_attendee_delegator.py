# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Vote recompute: delegator sin fila de asistente transfiere solo ``partner.vote`` al delegado."""

from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestVoteRecomputeNonAttendeeDelegator(AssemblyTestMixin, TransactionCase):
    """``delegated_in`` desde partner.vote; sin filas attendee.vote para delegador externo."""

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
        """Delegador excluido de generación de asistentes; delegado y otro convocados."""
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
            "Delegador excluido no debe tener fila de asistente",
        )
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        return assembly, vote_type, p_del, p_def, p_other

    def test_non_attendee_delegator_transfers_own_partner_vote_to_delegate(self):
        """(1)(2) Sin asistente delegador: delegado recibe delegated_in desde partner.vote."""
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
                "delegation_state": "confirmed",
            }
        )
        delegate_att.recompute_attendee_vote_lines()
        lines_del = self._vote_lines_for_partner_on_assembly(self.env, assembly, p_del)
        self.assertFalse(
            lines_del,
            "Delegador sin asistente no debe tener assembly.attendee.vote",
        )
        line_def = self._vote_lines_for_partner_on_assembly(
            self.env, assembly, p_def
        ).filtered(lambda r: r.vote_type_id == vote_type)
        self.assertTrue(line_def)
        self.assertEqual(line_def.delegated_in_votes, 10.0)
        self.assertEqual(line_def.own_votes, 4.0)

    def test_batch_recompute_all_attendees_non_attendee_delegator_transfers(self):
        """QA: ``assembly.attendee_ids.recompute`` sin fila delegador sigue sumando partner.vote."""
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
                "delegation_state": "confirmed",
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

    def test_negative_revoked_delegation_does_not_transfer(self):
        """(5) Revocada: deja de contar como inbound efectivo."""
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
                "delegation_state": "confirmed",
            }
        )
        delegate_att.recompute_attendee_vote_lines()
        line_def = self._vote_lines_for_partner_on_assembly(
            self.env, assembly, p_def
        ).filtered(lambda r: r.vote_type_id == vote_type)
        self.assertEqual(line_def.delegated_in_votes, 10.0)
        del_rec.write({"delegation_state": "revoked"})
        delegate_att.recompute_attendee_vote_lines()
        line_def = self._vote_lines_for_partner_on_assembly(
            self.env, assembly, p_def
        ).filtered(lambda r: r.vote_type_id == vote_type)
        self.assertEqual(line_def.delegated_in_votes, 0.0)

    def test_negative_draft_delegation_does_not_transfer(self):
        """(5) Borrador: no hay transferencia efectiva."""
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
                "delegation_state": "draft",
            }
        )
        delegate_att.recompute_attendee_vote_lines()
        line_def = self._vote_lines_for_partner_on_assembly(
            self.env, assembly, p_def
        ).filtered(lambda r: r.vote_type_id == vote_type)
        self.assertEqual(line_def.delegated_in_votes, 0.0)

    def test_delegator_becomes_confirmed_attendee_no_duplicate_delegate_totals(self):
        """(3)(4) Tras alta y confirmación del delegador, totales del delegado sin duplicar."""
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
                "delegation_state": "confirmed",
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
            "delegated_in sigue siendo solo partner.vote del delegador",
        )
        self.assertEqual(
            line_def.attendee_vote_total,
            13.0,
            "Regresión duplicación: total delegado no debe pasar a 23",
        )
        self.assertEqual(line_del.delegated_out_votes, 10.0)

    def test_regression_delegate_inbound_sum_not_doubled_after_delegator_confirms(self):
        """Regresión: una sola aportación 10 en delegated_in tras confirmar delegador."""
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
                "delegation_state": "confirmed",
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
            "Una sola fila persistida (asistente, tipo de voto)",
        )
        line_def = self._vote_lines_for_partner_on_assembly(
            self.env, assembly, p_def
        ).filtered(lambda r: r.vote_type_id == vote_type)
        self.assertEqual(line_def.delegated_in_votes, 10.0)
        n_inbound = self.env["assembly.delegation"].search_count(
            [
                ("assembly_id", "=", assembly.id),
                ("delegation_state", "=", "confirmed"),
                ("delegate_partner_id", "=", p_def.id),
            ]
        )
        self.assertEqual(n_inbound, 1)

    def test_delegated_in_sums_only_delegators_partner_vote(self):
        """(4) Varios delegadores externos: ``delegated_in`` = suma de sus ``partner.vote``."""
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
                "delegation_state": "confirmed",
            }
        )
        Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": p_b.id,
                "delegate_partner_id": p_def.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
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
    """QA obligatoria: fuente ``partner.vote``, hooks sin ``recompute`` manual, sin duplicar."""

    def test_mandatory_non_attendee_transfers_match_partner_vote_on_create_hook(self):
        """Delegador sin asistente: el hook post-``create`` deja ``delegated_in`` = ``partner.vote``."""
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
                "delegation_state": "confirmed",
            }
        )
        self.assertFalse(
            self._vote_lines_for_partner_on_assembly(self.env, assembly, p_del),
            "Delegador externo: ninguna fila assembly.attendee.vote",
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
            "delegated_in debe coincidir con partner.vote del delegador",
        )

    def test_mandatory_revoke_delegation_clears_delegated_in_via_write_hook_only(self):
        """Revocar solo con ``write``: sin ``recompute_attendee_vote_lines`` manual."""
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
                "delegation_state": "confirmed",
            }
        )
        line_def = self._vote_lines_for_partner_on_assembly(
            self.env, assembly, p_def
        ).filtered(lambda r: r.vote_type_id == vote_type)
        self.assertEqual(line_def.delegated_in_votes, 6.0)
        del_rec.write({"delegation_state": "revoked"})
        line_def = self._vote_lines_for_partner_on_assembly(
            self.env, assembly, p_def
        ).filtered(lambda r: r.vote_type_id == vote_type)
        self.assertEqual(line_def.delegated_in_votes, 0.0)

    def test_mandatory_delegator_becomes_attendee_recompute_votes_no_duplicate_inbound(
        self,
    ):
        """Tras alta del delegador como asistente, ``recompute_votes`` no duplica ``delegated_in``."""
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
                "delegation_state": "confirmed",
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
