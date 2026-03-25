# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblyTypeInheritanceConsistency(AssemblyTestMixin, TransactionCase):
    """Test that assembly_type_id inheritance works consistently
    in create() and onchange()."""

    def test_create_inherits_vote_type_ids_even_if_empty(self):
        """create() inherits vote_type_ids even if assembly_type has none
        (matches onchange)."""
        # Create assembly type with NO vote types
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
        # Create assembly via create() (simulating RPC/import/backend)
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Test Assembly",
                "assembly_type_id": assembly_type.id,
                # vote_type_ids NOT in vals - should be inherited (empty)
            }
        )
        # Verify inheritance: should be empty, matching onchange behavior
        self.assertEqual(
            len(assembly.vote_type_ids),
            0,
            "create() should inherit empty vote_type_ids to match onchange()",
        )

    def test_create_inherits_all_required_fields(self):
        """create() inherits all required fields from assembly_type_id."""
        vote_type1 = self._create_vote_type(self.env, name="VT1", code="VT1")
        # pylint: disable=protected-access
        vote_type2 = self._create_vote_type(self.env, name="VT2", code="VT2")
        # pylint: disable=protected-access
        partners = self._create_partners(
            self.env, 3
        )  # pylint: disable=protected-access
        domain = "[('id', 'in', %s)]" % partners.ids

        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Complete Type",
                "code": "COMPLETE",
                "vote_type_ids": [(6, 0, (vote_type1 | vote_type2).ids)],
                "default_quorum_type": "fixed",
                "default_quorum_value": 15.0,
                "default_quorum_second_call_type": "percentage",
                "default_quorum_second_call_value": 25.0,
                "partner_domain": domain,
            }
        )

        # Create assembly WITHOUT any of these fields (simulating RPC/import)
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Test Assembly",
                "assembly_type_id": assembly_type.id,
                # None of the fields in vals - all should be inherited
            }
        )

        # Verify ALL fields are inherited correctly
        self.assertEqual(
            assembly.vote_type_ids,
            vote_type1 | vote_type2,
            "vote_type_ids should be inherited",
        )
        self.assertEqual(
            assembly.quorum_type,
            "fixed",
            "quorum_type should be inherited",
        )
        self.assertEqual(
            assembly.quorum_value,
            15.0,
            "quorum_value should be inherited",
        )
        self.assertEqual(
            assembly.quorum_second_call_type,
            "percentage",
            "quorum_second_call_type should be inherited",
        )
        self.assertEqual(
            assembly.quorum_second_call_value,
            25.0,
            "quorum_second_call_value should be inherited",
        )
        self.assertEqual(
            assembly.partner_domain,
            domain,
            "partner_domain should be inherited",
        )

    def test_create_respects_explicit_values(self):
        """create() respects explicit values even if assembly_type has defaults."""
        vote_type1 = self._create_vote_type(self.env, name="VT1", code="VT1")
        # pylint: disable=protected-access
        vote_type2 = self._create_vote_type(self.env, name="VT2", code="VT2")
        # pylint: disable=protected-access
        vote_type3 = self._create_vote_type(self.env, name="VT3", code="VT3")
        # pylint: disable=protected-access
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Type With Defaults",
                "code": "DEFAULTS",
                "vote_type_ids": [(6, 0, (vote_type1 | vote_type2).ids)],
                "default_quorum_type": "percentage",
                "default_quorum_value": 50.0,
                "default_quorum_second_call_type": "any",
                "default_quorum_second_call_value": 0.0,
                "partner_domain": "[('id', '=', 1)]",
            }
        )

        # Create assembly WITH explicit values (should NOT be overridden)
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Test Assembly",
                "assembly_type_id": assembly_type.id,
                "vote_type_ids": [
                    (6, 0, vote_type3.ids)
                ],  # Explicit: different from type
                "quorum_type": "fixed",  # Explicit: different from type
                "quorum_value": 20.0,  # Explicit: different from type
                "quorum_second_call_type": "percentage",  # Explicit: diff from type
                "quorum_second_call_value": 10.0,  # Explicit: different from type
                "partner_domain": "[('id', '=', 2)]",  # Explicit: different from type
            }
        )

        # Verify explicit values are kept (not overridden by inheritance)
        self.assertEqual(
            assembly.vote_type_ids,
            vote_type3,
            "Explicit vote_type_ids should be kept",
        )
        self.assertEqual(
            assembly.quorum_type,
            "fixed",
            "Explicit quorum_type should be kept",
        )
        self.assertEqual(
            assembly.quorum_value,
            20.0,
            "Explicit quorum_value should be kept",
        )
        self.assertEqual(
            assembly.quorum_second_call_type,
            "percentage",
            "Explicit quorum_second_call_type should be kept",
        )
        self.assertEqual(
            assembly.quorum_second_call_value,
            10.0,
            "Explicit quorum_second_call_value should be kept",
        )
        self.assertEqual(
            assembly.partner_domain,
            "[('id', '=', 2)]",
            "Explicit partner_domain should be kept",
        )

    def test_create_inheritance_matches_onchange_behavior(self):
        """create() inheritance behavior matches onchange() behavior exactly."""
        vote_type1 = self._create_vote_type(self.env, name="VT1", code="VT1")
        # pylint: disable=protected-access
        vote_type2 = self._create_vote_type(self.env, name="VT2", code="VT2")
        # pylint: disable=protected-access
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Test Type",
                "code": "TEST",
                "vote_type_ids": [(6, 0, (vote_type1 | vote_type2).ids)],
                "default_quorum_type": "fixed",
                "default_quorum_value": 12.0,
                "default_quorum_second_call_type": "percentage",
                "default_quorum_second_call_value": 30.0,
                "partner_domain": "[('active', '=', True)]",
            }
        )

        # Test 1: create() without explicit values
        assembly_create = self.env["assembly.assembly"].create(
            {
                "name": "Assembly via create()",
                "assembly_type_id": assembly_type.id,
            }
        )

        # Test 2: onchange() behavior
        assembly_onchange = self.env["assembly.assembly"].new(
            {
                "name": "Assembly via onchange()",
            }
        )
        assembly_onchange.assembly_type_id = assembly_type
        assembly_onchange._onchange_assembly_type_id()  # pylint: disable=protected-access

        onchange_vt_ids = {
            (r._origin.id if getattr(r, "_origin", None) and r._origin.id else r.id)
            for r in assembly_onchange.vote_type_ids
        }
        self.assertEqual(
            set(assembly_create.vote_type_ids.ids),
            onchange_vt_ids,
            "vote_type_ids should match between create() and onchange()",
        )
        self.assertEqual(
            assembly_create.quorum_type,
            assembly_onchange.quorum_type,
            "quorum_type should match between create() and onchange()",
        )
        self.assertEqual(
            assembly_create.quorum_value,
            assembly_onchange.quorum_value,
            "quorum_value should match between create() and onchange()",
        )
        self.assertEqual(
            assembly_create.quorum_second_call_type,
            assembly_onchange.quorum_second_call_type,
            "quorum_second_call_type should match between create() and onchange()",
        )
        self.assertEqual(
            assembly_create.quorum_second_call_value,
            assembly_onchange.quorum_second_call_value,
            "quorum_second_call_value should match between create() and onchange()",
        )
        self.assertEqual(
            assembly_create.partner_domain,
            assembly_onchange.partner_domain,
            "partner_domain should match between create() and onchange()",
        )

    def test_create_with_partial_explicit_values(self):
        """create() inherits missing fields even when some are explicitly provided."""
        vote_type1 = self._create_vote_type(self.env, name="VT1", code="VT1")
        # pylint: disable=protected-access
        vote_type2 = self._create_vote_type(self.env, name="VT2", code="VT2")
        # pylint: disable=protected-access
        assembly_type = self.env["assembly.type"].create(  # noqa: F841
            {
                "name": "Type With Defaults",
                "code": "DEFAULTS",
                "vote_type_ids": [(6, 0, (vote_type1 | vote_type2).ids)],
                "default_quorum_type": "percentage",
                "default_quorum_value": 60.0,
                "default_quorum_second_call_type": "any",
                "default_quorum_second_call_value": 0.0,
                "partner_domain": "[('id', '>', 0)]",
            }
        )

        # Create assembly with SOME explicit values
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Test Assembly",
                "assembly_type_id": assembly_type.id,
                "quorum_type": "fixed",  # Explicit
                "quorum_value": 25.0,  # Explicit
                # vote_type_ids, quorum_second_call_type, quorum_second_call_value,
                # partner_domain NOT provided - should be inherited
            }
        )

        # Verify explicit values are kept
        self.assertEqual(assembly.quorum_type, "fixed")
        self.assertEqual(assembly.quorum_value, 25.0)

        # Verify missing values are inherited
        self.assertEqual(
            assembly.vote_type_ids,
            vote_type1 | vote_type2,
            "vote_type_ids should be inherited when not provided",
        )
        self.assertEqual(
            assembly.quorum_second_call_type,
            "any",
            "quorum_second_call_type should be inherited when not provided",
        )
        self.assertEqual(
            assembly.quorum_second_call_value,
            0.0,
            "quorum_second_call_value should be inherited when not provided",
        )
        self.assertEqual(
            assembly.partner_domain,
            "[('id', '>', 0)]",
            "partner_domain should be inherited when not provided",
        )
