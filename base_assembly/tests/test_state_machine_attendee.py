# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Attendee ``attendee_state`` graph: allowed vs blocked (ORM + :meth:`_validate_attendee_state_transition`)."""

from odoo.addons.base_assembly.models.assembly_attendee import (
    _ATTENDEE_ALLOWED_STATE_TRANSITIONS,
    CTX_ATTENDEE_ALLOW_REGISTRATION_STATE_WRITE,
)
from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin

_ALLOWED_ATTENDEE_EDGES = frozenset(
    (old, new)
    for old, targets in _ATTENDEE_ALLOWED_STATE_TRANSITIONS.items()
    for new in targets
)


class TestAttendeeStateMachine(AssemblyTestMixin, TransactionCase):
    """Protects attendee registration state machine used by ``write`` and actions."""

    def _graph_shell(self):
        return self.env["assembly.attendee"].new({})

    def test_same_state_is_noop(self):
        shell = self._graph_shell()
        shell._validate_attendee_state_transition("registered", "registered")

    def test_all_documented_edges_allowed(self):
        shell = self._graph_shell()
        for old, new in sorted(_ALLOWED_ATTENDEE_EDGES):
            with self.subTest(old=old, new=new):
                shell._validate_attendee_state_transition(old, new)

    def test_disallowed_backward_edges_raise(self):
        shell = self._graph_shell()
        with self.assertRaises(UserError):
            shell._validate_attendee_state_transition("confirmed", "registered")
        with self.assertRaises(UserError):
            shell._validate_attendee_state_transition("absent", "registered")

    def test_invalid_state_token_raises(self):
        shell = self._graph_shell()
        with self.assertRaises(UserError):
            shell._validate_attendee_state_transition("registered", "bogus")

    def test_write_enforces_graph(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        attendee = assembly.attendee_ids[0]
        attendee.with_context(
            **{CTX_ATTENDEE_ALLOW_REGISTRATION_STATE_WRITE: True}
        ).write({"attendee_state": "absent"})
        self.assertEqual(attendee.attendee_state, "absent")
        attendee.with_context(
            **{CTX_ATTENDEE_ALLOW_REGISTRATION_STATE_WRITE: True}
        ).write({"attendee_state": "confirmed"})
        self.assertEqual(attendee.attendee_state, "confirmed")
        with self.assertRaises(UserError):
            attendee.with_context(
                **{CTX_ATTENDEE_ALLOW_REGISTRATION_STATE_WRITE: True}
            ).write({"attendee_state": "registered"})
