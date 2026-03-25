# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Production-grade tests for assembly.create() without onchange.

Tests that assembly.create() correctly inherits all fields from assembly.type
even when called via RPC/API/import (no onchange triggered).
"""

from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblyCreateWithoutOnchange(AssemblyTestMixin, TransactionCase):
    """Test assembly.create() inheritance without onchange."""

    def test_create_inherits_vote_type_ids_without_onchange(self):
        """create() inherits vote_type_ids without onchange."""
        vote_type1 = self._create_vote_type(self.env, name="VT1", code="VT1")
        # pylint: disable=protected-access
        vote_type2 = self._create_vote_type(self.env, name="VT2", code="VT2")
        # pylint: disable=protected-access
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Test Type",
                "code": "TEST",
                "vote_type_ids": [(6, 0, [vote_type1.id, vote_type2.id])],
                "default_quorum_type": "percentage",
                "default_quorum_value": 50.0,
                "default_quorum_second_call_type": "any",
                "default_quorum_second_call_value": 0.0,
                "partner_domain": "[]",
            }
        )

        # Create assembly via create() (simulates RPC/import, no onchange)
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Test Assembly",
                "assembly_type_id": assembly_type.id,
                # No explicit vote_type_ids - should inherit
            }
        )

        # Verify inheritance
        self.assertEqual(
            assembly.vote_type_ids,
            assembly_type.vote_type_ids,
            "create() should inherit vote_type_ids",
        )
        self.assertEqual(len(assembly.vote_type_ids), 2, "Should inherit 2 vote types")

    def test_create_inherits_all_fields_without_onchange(self):
        """create() inherits all required fields without onchange."""
        vote_type = self._create_vote_type(self.env, name="VT", code="VT")
        # pylint: disable=protected-access
        partners = self._create_partners(
            self.env, 3
        )  # pylint: disable=protected-access
        domain = "[('id', 'in', %s)]" % partners.ids

        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Test Type",
                "code": "TEST",
                "vote_type_ids": [(6, 0, [vote_type.id])],
                "default_quorum_type": "percentage",
                "default_quorum_value": 75.0,
                "default_quorum_second_call_type": "fixed",
                "default_quorum_second_call_value": 10.0,
                "partner_domain": domain,
                "default_street": "Test Street",
                "default_city": "Test City",
                "default_zip": "12345",
            }
        )

        # Create assembly via create() (no onchange)
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Test Assembly",
                "assembly_type_id": assembly_type.id,
            }
        )

        # Verify all fields inherited
        self.assertEqual(assembly.vote_type_ids, assembly_type.vote_type_ids)
        self.assertEqual(assembly.quorum_type, "percentage")
        self.assertEqual(assembly.quorum_value, 75.0)
        self.assertEqual(assembly.quorum_second_call_type, "fixed")
        self.assertEqual(assembly.quorum_second_call_value, 10.0)
        self.assertEqual(assembly.partner_domain, domain)
        self.assertEqual(assembly.street, "Test Street")
        self.assertEqual(assembly.city, "Test City")
        self.assertEqual(assembly.zip, "12345")

    def test_create_respects_explicit_values_without_onchange(self):
        """create() respects explicit values even when type has defaults."""
        vote_type1 = self._create_vote_type(
            self.env, name="VT1", code="VT1"
        )  # noqa: F841
        # pylint: disable=protected-access
        vote_type2 = self._create_vote_type(self.env, name="VT2", code="VT2")
        # pylint: disable=protected-access
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Test Type",
                "code": "TEST",
                "vote_type_ids": [(6, 0, [vote_type1.id])],
                "default_quorum_value": 50.0,
                "default_city": "Default City",
            }
        )

        # Create assembly with explicit values (should override inheritance)
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Test Assembly",
                "assembly_type_id": assembly_type.id,
                "vote_type_ids": [(6, 0, [vote_type2.id])],  # Explicit
                "quorum_value": 80.0,  # Explicit
                "city": "Explicit City",  # Explicit
            }
        )

        # Explicit values should be kept
        self.assertEqual(assembly.vote_type_ids, vote_type2, "Explicit vote types kept")
        self.assertEqual(assembly.quorum_value, 80.0, "Explicit quorum_value kept")
        self.assertEqual(assembly.city, "Explicit City", "Explicit city kept")

    def test_create_inherits_empty_vote_type_ids_without_onchange(self):
        """create() inherits empty vote_type_ids to match onchange behavior."""
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Type Without Votes",
                "code": "NOWOTES",
                "vote_type_ids": False,  # Explicitly empty
                "default_quorum_type": "percentage",
                "default_quorum_value": 50.0,
                "default_quorum_second_call_type": "any",
                "default_quorum_second_call_value": 0.0,
                "partner_domain": "[]",
            }
        )

        # Create assembly via create() (no onchange)
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Test Assembly",
                "assembly_type_id": assembly_type.id,
            }
        )

        # Should inherit empty vote_type_ids (matching onchange behavior)
        self.assertEqual(
            len(assembly.vote_type_ids), 0, "Should inherit empty vote_type_ids"
        )

    def test_create_inheritance_matches_onchange_behavior(self):
        """create() inheritance matches onchange() behavior exactly."""
        vote_type = self._create_vote_type(self.env, name="VT", code="VT")  # noqa: F841
        # pylint: disable=protected-access
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Test Type",
                "code": "TEST",
                "vote_type_ids": [(6, 0, [vote_type.id])],
                "default_quorum_type": "percentage",
                "default_quorum_value": 60.0,
                "default_quorum_second_call_type": "any",
                "default_quorum_second_call_value": 0.0,
                "partner_domain": "[('id', '=', 1)]",
            }
        )

        # Create via create() (no onchange)
        assembly_create = self.env["assembly.assembly"].create(
            {
                "name": "Assembly via create()",
                "assembly_type_id": assembly_type.id,
            }
        )

        # Create via form (with onchange) - simulate form behavior
        assembly_onchange = self.env["assembly.assembly"].new(
            {
                "name": "Assembly via onchange",
                "assembly_type_id": assembly_type.id,
            }
        )
        assembly_onchange._onchange_assembly_type_id()  # pylint: disable=protected-access
        # Create from onchange values (simulate form save)
        onchange_vals = {  # noqa: F841
            "name": assembly_onchange.name,
            "assembly_type_id": assembly_onchange.assembly_type_id.id,
            "vote_type_ids": [(6, 0, assembly_onchange.vote_type_ids.ids)],
            "quorum_type": assembly_onchange.quorum_type,
            "quorum_value": assembly_onchange.quorum_value,
            "quorum_second_call_type": assembly_onchange.quorum_second_call_type,
            "quorum_second_call_value": assembly_onchange.quorum_second_call_value,
            "partner_domain": assembly_onchange.partner_domain,
        }
        assembly_onchange = self.env["assembly.assembly"].create(onchange_vals)

        # Both should have same inherited values
        self.assertEqual(
            assembly_create.vote_type_ids,
            assembly_onchange.vote_type_ids,
            "create() should match onchange() for vote_type_ids",
        )
        self.assertEqual(
            assembly_create.quorum_type,
            assembly_onchange.quorum_type,
            "create() should match onchange() for quorum_type",
        )
        self.assertEqual(
            assembly_create.quorum_value,
            assembly_onchange.quorum_value,
            "create() should match onchange() for quorum_value",
        )
        self.assertEqual(
            assembly_create.partner_domain,
            assembly_onchange.partner_domain,
            "create() should match onchange() for partner_domain",
        )
