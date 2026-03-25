# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Especificación de ``assembly_state``: transiciones válidas, acciones y prerequisitos."""

from odoo.addons.base_assembly.models.assembly_assembly import (
    _ASSEMBLY_ALLOWED_STATE_TRANSITIONS,
    _ASSEMBLY_SEQUENTIAL_TRANSITIONS,
)
from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblyStateTransitionsSpec(AssemblyTestMixin, TransactionCase):
    """Cobertura funcional del grafo de estados y validaciones por acción."""

    def test_all_structural_edges_in_allow_list(self):
        """(1) El conjunto documentado coincide con la especificación."""
        sequential = {
            ("draft", "announced"),
            ("announced", "open"),
            ("open", "in_session"),
            ("in_session", "closed"),
        }
        self.assertEqual(_ASSEMBLY_SEQUENTIAL_TRANSITIONS, frozenset(sequential))
        for src in (
            "draft",
            "announced",
            "open",
            "in_session",
            "closed",
            "cancelled",
        ):
            self.assertIn(
                (src, "cancelled"),
                _ASSEMBLY_ALLOWED_STATE_TRANSITIONS,
            )
        self.assertIn(("cancelled", "draft"), _ASSEMBLY_ALLOWED_STATE_TRANSITIONS)

    def test_valid_linear_path_via_actions(self):
        """(1) Secuencia feliz draft → … → closed por acciones."""
        assembly, agenda = self._create_assembly_with_agenda()
        self.assertEqual(assembly.assembly_state, "draft")
        assembly.action_announce()
        self.assertEqual(assembly.assembly_state, "announced")
        assembly.action_open_registration()
        self.assertEqual(assembly.assembly_state, "open")
        assembly.action_start_session()
        self.assertEqual(assembly.assembly_state, "in_session")
        agenda.action_skip()
        assembly.action_close()
        self.assertEqual(assembly.assembly_state, "closed")

    def test_invalid_skip_step_blocked(self):
        """(2) Saltos no permitidos."""
        assembly, _ = self._create_assembly_with_agenda()
        with self.assertRaises(UserError):
            assembly.write({"assembly_state": "open"})

    def test_cancel_from_closed_then_reopen_draft(self):
        """(3)(4) Cerrada → cancelada → borrador."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_skip()
        assembly.action_close()
        assembly.action_cancel()
        self.assertEqual(assembly.assembly_state, "cancelled")
        assembly.action_reopen()
        self.assertEqual(assembly.assembly_state, "draft")

    def test_action_announce_requires_agenda(self):
        """(5) Prerequisito: anunciar sin puntos de agenda."""
        env = self.env
        vote_type = self._create_vote_type(env, name="ST agenda req")
        atype = self._create_assembly_type(env, name="ST type", vote_type=vote_type)
        partners = self._create_partners(env, 2)
        assembly = env["assembly.assembly"].create(
            {
                "name": "No agenda",
                "assembly_type_id": atype.id,
                "partner_domain": "[('id', 'in', %s)]" % partners.ids,
                "quorum_type": "percentage",
                "quorum_value": 50.0,
            }
        )
        if not assembly.vote_type_ids:
            assembly.write(
                {"vote_type_ids": [(6, 0, assembly.assembly_type_id.vote_type_ids.ids)]}
            )
        with self.assertRaises(UserError) as ex:
            assembly.action_announce()
        self.assertIn("agenda", str(ex.exception).lower())

    def test_action_cancel_reachable_from_draft_announced_and_open(self):
        """cancelled alcanzable desde draft, announced y open vía ``action_cancel``."""
        for label, setup in (
            ("draft", lambda a, ag: None),
            ("announced", lambda a, ag: a.action_announce()),
            (
                "open",
                lambda a, ag: (a.action_announce(), a.action_open_registration()),
            ),
        ):
            with self.subTest(phase=label):
                assembly, agenda = self._create_assembly_with_agenda()
                setup(assembly, agenda)
                assembly.action_cancel()
                self.assertEqual(
                    assembly.assembly_state,
                    "cancelled",
                    "action_cancel from %s" % label,
                )

    def test_action_reopen_clears_attendees_votings_resets_agendas(self):
        """cancelled → draft: sin asistentes ni votaciones; puntos de agenda en pending."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_generate_attendees()
        self.assertTrue(assembly.attendee_ids)
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        self.assertTrue(voting)
        assembly.action_cancel()
        self.assertEqual(assembly.assembly_state, "cancelled")
        assembly.action_reopen()
        self.assertEqual(assembly.assembly_state, "draft")
        self.assertFalse(assembly.attendee_ids)
        self.assertFalse(
            self.env["assembly.voting"].search_count(
                [("agenda_id.assembly_id", "=", assembly.id)]
            )
        )
        self.assertTrue(all(a.agenda_state == "pending" for a in assembly.agenda_ids))
