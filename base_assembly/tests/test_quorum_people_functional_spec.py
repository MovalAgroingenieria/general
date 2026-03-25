# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Quorum = distinct people (spec): confirmed, represented delegators, negatives, ratios.

Canonical quorum regression for the BASE module (replaces older split files).
"""

from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestQuorumPeopleFunctionalSpec(AssemblyTestMixin, TransactionCase):
    """Prove assembly.assembly quorum matches people-based functional rules."""

    def _assembly_four_partners(self):
        partners = self._create_partners(self.env, 4, prefix="QSpec")
        domain = "[('id', 'in', %s)]" % partners.ids
        assembly, _ = self._create_assembly_with_agenda(
            partner_domain=domain,
        )
        assembly.action_generate_attendees()
        return assembly, partners

    def test_spec_confirmed_attendees_are_present(self):
        """(QA1) Only confirmed attendee rows count as present; registered alone does not."""
        assembly, _partners = self._assembly_four_partners()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att0, att1 = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(att0.partner_id, vote_type, 1)
        self._give_partner_votes(att1.partner_id, vote_type, 1)
        att0.action_confirm()
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_present_attendees, 1)
        self.assertIn(att0.partner_id.id, assembly._get_present_partner_ids())

    def test_spec_registered_delegator_counts_when_delegate_confirmed_and_delegation_effective(
        self,
    ):
        """(QA2) Convoked but non-confirmed delegator counts if quorum-effective delegation exists."""
        assembly, _partners = self._assembly_four_partners()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 1)
        self._give_partner_votes(delegate.partner_id, vote_type, 1)
        delegate.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        assembly.invalidate_recordset()
        present = assembly._get_present_partner_ids()
        self.assertEqual(len(present), 2)
        self.assertIn(delegator.partner_id.id, present)
        self.assertIn(delegate.partner_id.id, present)

    def test_spec_confirmed_delegator_counted_only_once(self):
        """(QA3) Partner confirmed and delegator: single distinct count."""
        assembly, _partners = self._assembly_four_partners()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 1)
        self._give_partner_votes(delegate.partner_id, vote_type, 1)
        delegator.action_confirm()
        delegate.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_present_attendees, 2)

    def test_spec_partial_delegation_still_counts_delegator_for_quorum(self):
        """(QA4) Partial vote_type coverage on delegation still counts for quorum presence."""
        env = self.env
        vt1 = self._create_vote_type(env, name="QSpec VT1")
        vt2 = self._create_vote_type(env, name="QSpec VT2")
        atype = self._create_assembly_type(env, name="QSpec type", vote_type=vt1)
        atype.write({"vote_type_ids": [(4, vt2.id)]})
        partners = self._create_partners(env, 3, prefix="QSpecP")
        assembly, _ = self._create_assembly_with_agenda(
            assembly_type=atype,
            partner_domain="[('id', 'in', %s)]" % partners.ids,
        )
        assembly.vote_type_ids = [(6, 0, [vt1.id, vt2.id])]
        assembly.action_generate_attendees()
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        for vt in (vt1, vt2):
            self._give_partner_votes(delegator.partner_id, vt, 1)
            self._give_partner_votes(delegate.partner_id, vt, 1)
        delegate.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, [vt1.id])],
                "delegation_state": "confirmed",
            }
        )
        assembly.invalidate_recordset()
        present = assembly._get_present_partner_ids()
        self.assertEqual(len(present), 2)
        self.assertIn(delegator.partner_id.id, present)

    def test_spec_partner_vote_weights_do_not_affect_present_count(self):
        """(QA5) Many vs few partner.votes: same number of confirmed people → same present."""
        assembly, _partners = self._assembly_four_partners()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att0, att1 = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(att0.partner_id, vote_type, 100)
        self._give_partner_votes(att1.partner_id, vote_type, 1)
        att0.action_confirm()
        att1.action_confirm()
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_present_attendees, 2)

    def test_spec_negative_draft_delegation_does_not_add_delegator(self):
        """(QA6) Non-confirmed delegator + draft delegation → delegator not present."""
        assembly, _partners = self._assembly_four_partners()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 1)
        self._give_partner_votes(delegate.partner_id, vote_type, 1)
        delegate.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "draft",
            }
        )
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_present_attendees, 1)
        self.assertNotIn(delegator.partner_id.id, assembly._get_present_partner_ids())

    def test_spec_negative_revoked_delegation_does_not_add_delegator(self):
        """(QA6) After revoke, registered delegator no longer represented."""
        assembly, _partners = self._assembly_four_partners()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 1)
        self._give_partner_votes(delegate.partner_id, vote_type, 1)
        delegate.action_confirm()
        del_rec = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_present_attendees, 2)
        del_rec.write({"delegation_state": "revoked"})
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_present_attendees, 1)
        self.assertNotIn(delegator.partner_id.id, assembly._get_present_partner_ids())

    def test_spec_negative_no_effective_delegation_delegate_unconfirmed(self):
        """(QA6) Delegate not confirmed: only draft/revoked counts as ineffective; present = confirmed only."""
        assembly, _partners = self._assembly_four_partners()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 1)
        self._give_partner_votes(delegate.partner_id, vote_type, 1)
        delegator.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "draft",
            }
        )
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_present_attendees, 1)
        self.assertNotIn(delegate.partner_id.id, assembly._get_present_partner_ids())

    def test_spec_assembly_excluded_delegator_counts_for_quorum_when_delegation_confirmed(
        self,
    ):
        """Delegador sin fila de asistente pero en dominio convocable: cuenta como presente."""
        env = self.env
        p_del = env["res.partner"].create(
            {"name": "QSpec ExclDel", "is_company": False, "assembly_excluded": True}
        )
        p_def = env["res.partner"].create(
            {"name": "QSpec Delegate", "is_company": False, "assembly_excluded": False}
        )
        domain = "[('id', 'in', %s)]" % ([p_del.id, p_def.id],)
        assembly, _ = self._create_assembly_with_agenda(partner_domain=domain)
        assembly.action_generate_attendees()
        self.assertFalse(
            assembly.attendee_ids.filtered(lambda a: a.partner_id == p_del),
        )
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        self._give_partner_votes(p_del, vote_type, 1)
        self._give_partner_votes(p_def, vote_type, 1)
        delegate_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_def)
        delegate_att.action_confirm()
        env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": p_del.id,
                "delegate_partner_id": p_def.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        assembly.invalidate_recordset()
        present = assembly._get_present_partner_ids()
        self.assertEqual(len(present), 2)
        self.assertIn(p_del.id, present)
        self.assertIn(p_def.id, present)

    def test_spec_negative_excluded_delegator_draft_delegation_not_quorum_present(self):
        """Sin confirmar delegación, el delegador externo no entra en el cómputo de presentes."""
        env = self.env
        p_del = env["res.partner"].create(
            {"name": "QSpec ExclDraft", "is_company": False, "assembly_excluded": True}
        )
        p_def = env["res.partner"].create(
            {"name": "QSpec DelDraft", "is_company": False, "assembly_excluded": False}
        )
        domain = "[('id', 'in', %s)]" % ([p_del.id, p_def.id],)
        assembly, _ = self._create_assembly_with_agenda(partner_domain=domain)
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        self._give_partner_votes(p_del, vote_type, 1)
        self._give_partner_votes(p_def, vote_type, 1)
        delegate_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_def)
        delegate_att.action_confirm()
        env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": p_del.id,
                "delegate_partner_id": p_def.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "draft",
            }
        )
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_present_attendees, 1)
        self.assertNotIn(p_del.id, assembly._get_present_partner_ids())

    def test_regression_two_excluded_delegators_distinct_people_in_quorum(self):
        """Regresión: dos delegadores externos + delegado confirmado → tres personas presentes."""
        env = self.env
        p_a = env["res.partner"].create(
            {"name": "QSpec ExA", "is_company": False, "assembly_excluded": True}
        )
        p_b = env["res.partner"].create(
            {"name": "QSpec ExB", "is_company": False, "assembly_excluded": True}
        )
        p_def = env["res.partner"].create(
            {"name": "QSpec ExDef", "is_company": False, "assembly_excluded": False}
        )
        domain = "[('id', 'in', %s)]" % ([p_a.id, p_b.id, p_def.id],)
        assembly, _ = self._create_assembly_with_agenda(partner_domain=domain)
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        for p in (p_a, p_b, p_def):
            self._give_partner_votes(p, vote_type, 1)
        delegate_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_def)
        delegate_att.action_confirm()
        Delegation = env["assembly.delegation"]
        for p_del in (p_a, p_b):
            Delegation.create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": p_del.id,
                    "delegate_partner_id": p_def.id,
                    "vote_type_ids": [(6, 0, vote_type.ids)],
                    "delegation_state": "confirmed",
                }
            )
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_present_attendees, 3)
        present = assembly._get_present_partner_ids()
        self.assertEqual(len(present), 3)

    def _assembly_three_partners_domain(self):
        partners = self._create_partners(self.env, 3, prefix="QSpec3")
        domain = "[('id', 'in', %s)]" % partners.ids
        assembly, _agenda = self._create_assembly_with_agenda(partner_domain=domain)
        assembly.action_generate_attendees()
        return assembly, partners

    def test_spec_three_confirmed_yields_three_distinct_partner_ids(self):
        """Tres socios convocados y confirmados → tres personas presentes distintas."""
        assembly, _partners = self._assembly_three_partners_domain()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        for att in assembly.attendee_ids:
            self._give_partner_votes(att.partner_id, vote_type, 1)
            att.action_confirm()
        assembly.invalidate_recordset()
        present = assembly._get_present_partner_ids()
        self.assertEqual(len(present), 3)
        self.assertEqual(len(set(present)), 3)
        self.assertEqual(assembly.total_present_attendees, 3)

    def test_spec_delegator_outside_convocation_not_counted_via_delegation(self):
        """Delegador fuera del dominio de convocatoria no entra en presentes aunque exista delegación."""
        env = self.env
        p_in = env["res.partner"].create(
            {"name": "QSpec InDom", "is_company": False, "assembly_excluded": False}
        )
        p_out = env["res.partner"].create(
            {"name": "QSpec OutDom", "is_company": False, "assembly_excluded": False}
        )
        domain = "[('id', 'in', %s)]" % ([p_in.id],)
        assembly, _agenda = self._create_assembly_with_agenda(partner_domain=domain)
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        self._give_partner_votes(p_in, vote_type, 1)
        self._give_partner_votes(p_out, vote_type, 1)
        assembly.attendee_ids.filtered(lambda a: a.partner_id == p_in).action_confirm()
        env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": p_out.id,
                "delegate_partner_id": p_in.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        assembly.invalidate_recordset()
        present = assembly._get_present_partner_ids()
        self.assertEqual(present, frozenset({p_in.id}))
        self.assertNotIn(p_out.id, present)
        self.assertEqual(assembly.total_present_attendees, 1)

    def test_spec_vote_line_recompute_does_not_change_quorum(self):
        """Recomputar ``assembly.attendee.vote`` no altera conteo de presentes ni porcentaje."""
        assembly, _partners = self._assembly_three_partners_domain()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        a_att, b_att, _c = assembly.attendee_ids.sorted("id")
        self._give_partner_votes(a_att.partner_id, vote_type, 3)
        self._give_partner_votes(b_att.partner_id, vote_type, 7)
        a_att.action_confirm()
        b_att.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": a_att.partner_id.id,
                "delegate_partner_id": b_att.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        assembly.invalidate_recordset()
        partners_before = assembly._get_present_partner_ids()
        total_before = assembly.total_present_attendees
        pct_before = assembly.quorum_percentage
        for _ in range(8):
            assembly.attendee_ids.recompute_attendee_vote_lines()
        assembly.invalidate_recordset()
        self.assertEqual(assembly._get_present_partner_ids(), partners_before)
        self.assertEqual(assembly.total_present_attendees, total_before)
        self.assertEqual(assembly.quorum_percentage, pct_before)

    def test_spec_cancelled_assembly_stored_present_is_zero(self):
        """Asamblea cancelada: presentes almacenados y porcentaje a cero."""
        assembly, _agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att0, att1 = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(att0.partner_id, vote_type, 1)
        self._give_partner_votes(att1.partner_id, vote_type, 1)
        att0.action_confirm()
        att1.action_confirm()
        assembly.invalidate_recordset()
        self.assertGreater(assembly.total_present_attendees, 0)
        assembly.action_cancel()
        assembly.invalidate_recordset()
        self.assertEqual(assembly.assembly_state, "cancelled")
        self.assertEqual(assembly.total_present_attendees, 0)
        self.assertFalse(assembly.quorum_reached)
        self.assertEqual(assembly.quorum_percentage, 0.0)
        self.assertEqual(len(assembly._get_present_partner_ids()), 0)

    def test_spec_quorum_percentage_matches_people_ratio(self):
        """``quorum_percentage`` = presentes / posibles × 100 (solo personas)."""
        assembly, _partners = self._assembly_three_partners_domain()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att0, att1, _att2 = assembly.attendee_ids.sorted("id")
        self._give_partner_votes(att0.partner_id, vote_type, 1)
        self._give_partner_votes(att1.partner_id, vote_type, 1)
        att0.action_confirm()
        att1.action_confirm()
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_possible_attendees, 3)
        self.assertEqual(assembly.total_present_attendees, 2)
        self.assertAlmostEqual(
            assembly.quorum_percentage, (2.0 / 3.0) * 100.0, places=9
        )

    # --- Hardening: ``assembly.assembly._get_present_partner_ids`` (single source) ---

    def test_hardening_present_partner_ids_no_double_count(self):
        """Dos personas distintas; ``len(ids) == len(set(ids))`` y coincide con almacenado."""
        assembly, _partners = self._assembly_four_partners()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 1)
        self._give_partner_votes(delegate.partner_id, vote_type, 1)
        delegator.action_confirm()
        delegate.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        assembly.invalidate_recordset()
        ids = assembly._get_present_partner_ids()
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 2)
        self.assertEqual(len(ids), assembly.total_present_attendees)

    def test_hardening_non_attendee_delegator_in_present_partner_ids(self):
        """Delegador convocable sin fila de asistente entra en el frozenset de presentes."""
        env = self.env
        p_del = env["res.partner"].create(
            {"name": "QHard ExDel", "is_company": False, "assembly_excluded": True}
        )
        p_def = env["res.partner"].create(
            {"name": "QHard Delegate", "is_company": False, "assembly_excluded": False}
        )
        domain = "[('id', 'in', %s)]" % ([p_del.id, p_def.id],)
        assembly, _ = self._create_assembly_with_agenda(partner_domain=domain)
        assembly.action_generate_attendees()
        self.assertFalse(
            assembly.attendee_ids.filtered(lambda a: a.partner_id == p_del),
        )
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        self._give_partner_votes(p_del, vote_type, 1)
        self._give_partner_votes(p_def, vote_type, 1)
        assembly.attendee_ids.filtered(lambda a: a.partner_id == p_def).action_confirm()
        env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": p_del.id,
                "delegate_partner_id": p_def.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        assembly.invalidate_recordset()
        present = assembly._get_present_partner_ids()
        self.assertIn(p_del.id, present)
        self.assertIn(p_def.id, present)
        self.assertEqual(len(present), 2)

    def test_hardening_partial_delegation_single_delegator_id(self):
        """Delegación parcial (un solo vote_type): delegador cuenta una vez en el conjunto."""
        env = self.env
        vt1 = self._create_vote_type(env, name="QHard VT1")
        vt2 = self._create_vote_type(env, name="QHard VT2")
        atype = self._create_assembly_type(env, name="QHard type", vote_type=vt1)
        atype.write({"vote_type_ids": [(4, vt2.id)]})
        partners = self._create_partners(env, 3, prefix="QHardP")
        assembly, _ = self._create_assembly_with_agenda(
            assembly_type=atype,
            partner_domain="[('id', 'in', %s)]" % partners.ids,
        )
        assembly.vote_type_ids = [(6, 0, [vt1.id, vt2.id])]
        assembly.action_generate_attendees()
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        for vt in (vt1, vt2):
            self._give_partner_votes(delegator.partner_id, vt, 1)
            self._give_partner_votes(delegate.partner_id, vt, 1)
        delegate.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, [vt1.id])],
                "delegation_state": "confirmed",
            }
        )
        assembly.invalidate_recordset()
        ids = assembly._get_present_partner_ids()
        self.assertEqual(len(ids), 2)
        self.assertIn(delegator.partner_id.id, ids)

    def test_hardening_vote_weights_do_not_change_present_partner_ids(self):
        """Cambiar magnitudes en ``partner.vote`` no altera ``_get_present_partner_ids``."""
        assembly, _partners = self._assembly_four_partners()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att0, att1 = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(att0.partner_id, vote_type, 1)
        self._give_partner_votes(att1.partner_id, vote_type, 1)
        att0.action_confirm()
        att1.action_confirm()
        assembly.invalidate_recordset()
        before = assembly._get_present_partner_ids()
        self._give_partner_votes(att0.partner_id, vote_type, 50)
        assembly.invalidate_recordset()
        after = assembly._get_present_partner_ids()
        self.assertEqual(before, after)
        self.assertEqual(len(after), 2)

    def test_contract_quorum_helpers_single_source(self):
        """``total_present_attendees``, ``_count_present_attendees`` y ``_get_quorum_present_people_count`` alineados con ``_get_present_partner_ids``; quorum alcanzado coherente."""
        assembly, _partners = self._assembly_three_partners_domain()
        att0, att1, _att2 = assembly.attendee_ids.sorted("id")
        att0.action_confirm()
        att1.action_confirm()
        assembly.invalidate_recordset()
        pids = assembly._get_present_partner_ids()
        self.assertEqual(assembly._get_quorum_present_people_count(), len(pids))
        self.assertEqual(assembly._count_present_attendees(), len(pids))
        self.assertEqual(assembly.total_present_attendees, len(pids))
        possible = assembly._get_possible_attendees_count()
        self.assertEqual(
            assembly._is_quorum_reached(
                pids, possible, quorum_percentage=assembly.quorum_percentage
            ),
            assembly.quorum_reached,
        )
