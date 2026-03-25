# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Assembly ``assembly_state`` graph: allowed edges vs blocked edges (model integrity)."""

from odoo.addons.base_assembly.models.assembly_assembly import (
    _ASSEMBLY_ALLOWED_STATE_TRANSITIONS,
)
from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin

_ALLOWED_ASSEMBLY_EDGES = _ASSEMBLY_ALLOWED_STATE_TRANSITIONS


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
        for old, new in sorted(_ALLOWED_ASSEMBLY_EDGES):
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
