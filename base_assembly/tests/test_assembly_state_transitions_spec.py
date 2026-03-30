# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""``assembly_state`` spec: valid transitions, actions, and prerequisites."""

from odoo.addons.base_assembly.models.assembly_assembly import (
    _ASSEMBLY_ALLOWED_STATE_TRANSITIONS,
    _ASSEMBLY_SEQUENTIAL_TRANSITIONS,
)
from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblyStateTransitionsSpec(AssemblyTestMixin, TransactionCase):
    """Functional coverage of the state graph and per-action checks."""

    def test_all_structural_edges_in_allow_list(self):
        """(1) Documented edge set matches the specification."""
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
        """(1) Happy path draft → … → closed via actions."""
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
        """(2) Disallowed skip transitions."""
        assembly, _ = self._create_assembly_with_agenda()
        with self.assertRaises(UserError):
            assembly.write({"assembly_state": "open"})

    def test_cancel_from_closed_then_reopen_draft(self):
        """(3)(4) Closed → cancelled → draft."""
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
        """(5) Prerequisite: announce fails without agenda items."""
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
        """``cancelled`` reachable from draft, announced, and open via ``action_cancel``."""
        for label, setup in (
            ("draft", lambda a, ag: None),
            ("announced", lambda a, ag: a.action_announce()),
            (
                "open",
                lambda a, ag: (a.action_announce(), a.action_open_registration()),
            ),
        ):
            with self.subTest(phase=label):
                assembly, agenda = self._create_assembly_with_agenda(
                    name="Cancel reach asm %s" % label,
                )
                setup(assembly, agenda)
                assembly.action_cancel()
                self.assertEqual(
                    assembly.assembly_state,
                    "cancelled",
                    "action_cancel from %s" % label,
                )

    def test_action_reopen_clears_attendees_votings_resets_agendas(self):
        """cancelled → draft: no attendees or votings; agenda items reset to pending."""
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


class TestAssemblyStateMachine(AssemblyTestMixin, TransactionCase):
    """Protects :meth:`assembly.assembly._validate_state_transition` and write guards."""

    def _graph_shell(self):
        """In-memory row: only ``env`` is used by the validator."""
        return self.env["assembly.assembly"].new({"name": "state-machine shell"})

    def test_same_state_is_noop(self):
        shell = self._graph_shell()
        shell._validate_state_transition("draft", "draft")
        shell._validate_state_transition("closed", "closed")

    def test_all_documented_edges_allowed(self):
        shell = self._graph_shell()
        for old, new in sorted(_ASSEMBLY_ALLOWED_STATE_TRANSITIONS):
            with self.subTest(old=old, new=new):
                shell._validate_state_transition(old, new)

    def test_skip_forward_in_chain_raises(self):
        shell = self._graph_shell()
        with self.assertRaises(UserError):
            shell._validate_state_transition("draft", "open")
        with self.assertRaises(UserError):
            shell._validate_state_transition("announced", "in_session")
        with self.assertRaises(UserError):
            shell._validate_state_transition("draft", "closed")

    def test_closed_may_cancel_may_not_reopen_to_draft(self):
        shell = self._graph_shell()
        shell._validate_state_transition("closed", "cancelled")
        with self.assertRaises(UserError):
            shell._validate_state_transition("closed", "draft")
        with self.assertRaises(UserError):
            shell._validate_state_transition("closed", "open")

    def test_invalid_state_token_raises(self):
        shell = self._graph_shell()
        with self.assertRaises(UserError):
            shell._validate_state_transition("draft", "not_a_real_state")

    def test_write_enforces_graph_without_actions(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        with self.assertRaises(UserError):
            assembly.write({"assembly_state": "open"})
