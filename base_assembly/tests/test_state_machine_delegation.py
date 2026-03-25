# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Delegation ``delegation_state`` graph: allowed vs blocked (ORM + :meth:`_validate_delegation_state_transition`)."""

from odoo.addons.base_assembly.models.assembly_delegation import (
    _DELEGATION_ALLOWED_STATE_TRANSITIONS,
)
from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin

_ALLOWED_DELEGATION_EDGES = frozenset(
    (old, new)
    for old, targets in _DELEGATION_ALLOWED_STATE_TRANSITIONS.items()
    for new in targets
)


class TestDelegationStateMachine(AssemblyTestMixin, TransactionCase):
    """Protects delegation status transitions before business rules on confirm."""

    def _graph_shell(self):
        return self.env["assembly.delegation"].new({})

    def test_same_state_is_noop(self):
        shell = self._graph_shell()
        shell._validate_delegation_state_transition("draft", "draft")

    def test_all_documented_edges_allowed(self):
        shell = self._graph_shell()
        for old, new in sorted(_ALLOWED_DELEGATION_EDGES):
            with self.subTest(old=old, new=new):
                shell._validate_delegation_state_transition(old, new)

    def test_disallowed_edges_raise(self):
        shell = self._graph_shell()
        with self.assertRaises(UserError):
            shell._validate_delegation_state_transition("confirmed", "draft")
        with self.assertRaises(UserError):
            shell._validate_delegation_state_transition("revoked", "draft")

    def test_invalid_state_token_raises(self):
        shell = self._graph_shell()
        with self.assertRaises(UserError):
            shell._validate_delegation_state_transition("draft", "not_a_state")

    def test_write_enforces_graph(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 1)
        self._give_partner_votes(delegate.partner_id, vote_type, 1)
        delegator.action_confirm()
        delegate.action_confirm()
        delegation = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "draft",
            }
        )
        delegation.write({"delegation_state": "confirmed"})
        self.assertEqual(delegation.delegation_state, "confirmed")
        with self.assertRaises(UserError):
            delegation.write({"delegation_state": "draft"})
