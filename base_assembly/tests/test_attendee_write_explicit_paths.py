# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""``assembly.attendee.write``: sin recomputo oculto; estado vía acciones; identidad bloqueada."""

from odoo.addons.base_assembly.models.assembly_attendee import (
    CTX_ATTENDEE_ALLOW_IDENTITY_WRITE,
    CTX_ATTENDEE_ALLOW_REGISTRATION_STATE_WRITE,
)
from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAttendeeWriteExplicitPaths(AssemblyTestMixin, TransactionCase):
    """Estrategia: ``write`` mínimo; votos solo con ``recompute_votes`` en flujos explícitos."""

    def test_generic_write_cannot_change_registration_state(self):
        """Transición válida sin contexto interno ⇒ error (usar ``action_confirm``)."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vt = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vt, 5)
        with self.assertRaises(UserError) as ex:
            att.write({"attendee_state": "confirmed"})
        self.assertIn("generic save", str(ex.exception).lower())
        att.action_confirm()
        self.assertEqual(att.attendee_state, "confirmed")

    def test_internal_context_still_validates_state_graph(self):
        """Contexto interno no desactiva el grafo de estados."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        att = assembly.attendee_ids[0]
        att.action_confirm()
        with self.assertRaises(UserError):
            att.with_context(
                **{CTX_ATTENDEE_ALLOW_REGISTRATION_STATE_WRITE: True}
            ).write({"attendee_state": "registered"})

    def test_write_cannot_change_partner_without_bypass(self):
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        att = assembly.attendee_ids[0]
        other = self.env["res.partner"].create(
            {"name": "WrIsoPartner", "is_company": False}
        )
        with self.assertRaises(UserError):
            att.write({"partner_id": other.id})
        self.assertTrue(
            att.with_context(**{CTX_ATTENDEE_ALLOW_IDENTITY_WRITE: True}).write(
                {"partner_id": other.id}
            )
        )

    def test_repeated_safe_writes_do_not_duplicate_vote_rows(self):
        """Notas u otros campos seguros: mismas filas ``attendee.vote`` tras varios ``write``."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vt = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vt, 4)
        att.action_confirm()
        n_lines = self.env["assembly.attendee.vote"].search_count(
            [("attendee_id", "=", att.id)]
        )
        for i in range(5):
            att.write({"attendance_notes": "n%s" % i})
        att.invalidate_recordset()
        self.assertEqual(
            self.env["assembly.attendee.vote"].search_count(
                [("attendee_id", "=", att.id)]
            ),
            n_lines,
        )
        line = self.env["assembly.attendee.vote"].search(
            [("attendee_id", "=", att.id), ("vote_type_id", "=", vt.id)], limit=1
        )
        self.assertTrue(line)
        self.assertEqual(line.own_votes, 4.0)
