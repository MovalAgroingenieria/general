# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Estados de asistente: transiciones, confirmación y efecto en líneas de voto."""

from odoo.addons.base_assembly.models.assembly_attendee import (
    _ATTENDEE_ALLOWED_STATE_TRANSITIONS,
)
from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAttendeeStateTransitionsSpec(AssemblyTestMixin, TransactionCase):
    """Reglas: registered / confirmed / absent; recomputo al confirmar y al ausentar."""

    def test_model_helper_matches_documented_graph(self):
        Att = self.env["assembly.attendee"]
        for old, allowed in _ATTENDEE_ALLOWED_STATE_TRANSITIONS.items():
            for new in allowed:
                self.assertTrue(
                    Att._attendee_is_allowed_registration_state_transition(old, new),
                    f"{old!r} -> {new!r}",
                )
        self.assertFalse(
            Att._attendee_is_allowed_registration_state_transition(
                "confirmed", "registered"
            )
        )

    def test_registered_to_confirmed_and_vote_rows(self):
        """(1)(4) Confirmar genera/actualiza filas ``assembly.attendee.vote``."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vt = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vt, 7)
        self.assertEqual(att.attendee_state, "registered")
        att.action_confirm()
        self.assertEqual(att.attendee_state, "confirmed")
        line = self.env["assembly.attendee.vote"].search(
            [("attendee_id", "=", att.id), ("vote_type_id", "=", vt.id)], limit=1
        )
        self.assertTrue(line)
        self.assertEqual(line.own_votes, 7.0)
        self.assertEqual(line.delegated_out_votes, 0.0)
        self.assertEqual(line.delegated_in_votes, 0.0)
        self.assertEqual(line.attendee_vote_total, 7.0)

    def test_confirmed_to_absent_clears_delegation_vote_effect_on_others(self):
        """(2)(5) Ausente: sin delegación efectiva hacia/desde ese asistente."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vt = assembly.assembly_type_id.vote_type_ids[0]
        a, b = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(a.partner_id, vt, 4)
        self._give_partner_votes(b.partner_id, vt, 2)
        (a | b).action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": b.partner_id.id,
                "vote_type_ids": [(6, 0, vt.ids)],
                "delegation_state": "confirmed",
            }
        )
        assembly.attendee_ids.recompute_attendee_vote_lines()
        lb_before = self.env["assembly.attendee.vote"].search(
            [("attendee_id", "=", b.id), ("vote_type_id", "=", vt.id)], limit=1
        )
        self.assertEqual(lb_before.delegated_in_votes, 4.0)
        a.action_mark_absent()
        la = self.env["assembly.attendee.vote"].search(
            [("attendee_id", "=", a.id), ("vote_type_id", "=", vt.id)], limit=1
        )
        lb = self.env["assembly.attendee.vote"].search(
            [("attendee_id", "=", b.id), ("vote_type_id", "=", vt.id)], limit=1
        )
        self.assertEqual(a.attendee_state, "absent")
        self.assertEqual(la.delegated_out_votes, 0.0)
        self.assertEqual(la.delegated_in_votes, 0.0)
        self.assertEqual(lb.delegated_in_votes, 0.0)
        self.assertEqual(lb.attendee_vote_total, 2.0)

    def test_invalid_transition_confirmed_to_registered_blocked(self):
        """(3) Transición no permitida vía ``write``."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        att = assembly.attendee_ids[0]
        att.action_confirm()
        with self.assertRaises(UserError):
            att.write({"attendee_state": "registered"})

    def test_absent_then_confirmed_allowed(self):
        """(2) absent -> confirmed restablece flujo."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        att = assembly.attendee_ids[0]
        att.action_mark_absent()
        self.assertEqual(att.attendee_state, "absent")
        att.action_confirm()
        self.assertEqual(att.attendee_state, "confirmed")
