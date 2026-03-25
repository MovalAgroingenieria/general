# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblyCreateInheritance(AssemblyTestMixin, TransactionCase):
    """Tests for assembly.assembly.create() inheritance from assembly_type_id.

    These tests verify that create() inherits all values from assembly_type_id
    WITHOUT requiring onchange (simulating RPC/import/backend creation).
    """

    def test_create_inherits_vote_type_ids(self):
        """create() inherits vote_type_ids from assembly_type_id."""
        vote_type1 = self._create_vote_type(self.env, name="VT1", code="VT1")
        # pylint: disable=protected-access
        vote_type2 = self._create_vote_type(self.env, name="VT2", code="VT2")
        # pylint: disable=protected-access
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Test Type",
                "code": "TEST",
                "vote_type_ids": [(6, 0, (vote_type1 | vote_type2).ids)],
                "partner_domain": "[]",
            }
        )
        # Create assembly WITHOUT passing vote_type_ids (simulating RPC/import)
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Test Assembly",
                "assembly_type_id": assembly_type.id,
                # vote_type_ids NOT in vals - should be inherited
            }
        )
        # Verify inheritance
        self.assertEqual(assembly.vote_type_ids, vote_type1 | vote_type2)
        self.assertEqual(len(assembly.vote_type_ids), 2)

    def test_create_inherits_quorum_type(self):
        """create() inherits quorum_type from assembly_type_id."""
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Test Type",
                "code": "TEST",
                "default_quorum_type": "fixed",
                "partner_domain": "[]",
            }
        )
        # Create assembly WITHOUT passing quorum_type
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Test Assembly",
                "assembly_type_id": assembly_type.id,
                # quorum_type NOT in vals - should be inherited
            }
        )
        # Verify inheritance
        self.assertEqual(assembly.quorum_type, "fixed")

    def test_create_inherits_quorum_value(self):
        """create() inherits quorum_value from assembly_type_id."""
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Test Type",
                "code": "TEST",
                "default_quorum_value": 75.0,
                "partner_domain": "[]",
            }
        )
        # Create assembly WITHOUT passing quorum_value
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Test Assembly",
                "assembly_type_id": assembly_type.id,
                # quorum_value NOT in vals - should be inherited
            }
        )
        # Verify inheritance
        self.assertEqual(assembly.quorum_value, 75.0)

    def test_create_inherits_quorum_second_call_type(self):
        """create() inherits quorum_second_call_type from assembly_type_id."""
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Test Type",
                "code": "TEST",
                "default_quorum_second_call_type": "percentage",
                "partner_domain": "[]",
            }
        )
        # Create assembly WITHOUT passing quorum_second_call_type
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Test Assembly",
                "assembly_type_id": assembly_type.id,
                # quorum_second_call_type NOT in vals - should be inherited
            }
        )
        # Verify inheritance
        self.assertEqual(assembly.quorum_second_call_type, "percentage")

    def test_create_inherits_quorum_second_call_value(self):
        """create() inherits quorum_second_call_value from assembly_type_id."""
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Test Type",
                "code": "TEST",
                "default_quorum_second_call_value": 30.0,
                "partner_domain": "[]",
            }
        )
        # Create assembly WITHOUT passing quorum_second_call_value
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Test Assembly",
                "assembly_type_id": assembly_type.id,
                # quorum_second_call_value NOT in vals - should be inherited
            }
        )
        # Verify inheritance
        self.assertEqual(assembly.quorum_second_call_value, 30.0)

    def test_create_inherits_partner_domain(self):
        """create() inherits partner_domain from assembly_type_id."""
        partners = self._create_partners(
            self.env, 3
        )  # pylint: disable=protected-access
        domain = "[('id', 'in', %s)]" % partners.ids
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Test Type",
                "code": "TEST",
                "partner_domain": domain,
            }
        )
        # Create assembly WITHOUT passing partner_domain
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Test Assembly",
                "assembly_type_id": assembly_type.id,
                # partner_domain NOT in vals - should be inherited
            }
        )
        # Verify inheritance
        self.assertEqual(assembly.partner_domain, domain)

    def test_create_inherits_all_fields_together(self):
        """create() inherits ALL fields from assembly_type_id in one call."""
        vote_type = self._create_vote_type(self.env, name="VT", code="VT")
        # pylint: disable=protected-access
        partners = self._create_partners(
            self.env, 2
        )  # pylint: disable=protected-access
        domain = "[('id', 'in', %s)]" % partners.ids
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Complete Type",
                "code": "COMPLETE",
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "default_quorum_type": "fixed",
                "default_quorum_value": 10.0,
                "default_quorum_second_call_type": "percentage",
                "default_quorum_second_call_value": 20.0,
                "partner_domain": domain,
            }
        )
        # Create assembly WITHOUT passing any of these fields
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Complete Assembly",
                "assembly_type_id": assembly_type.id,
                # None of the fields in vals - all should be inherited
            }
        )
        # Verify ALL fields are inherited
        self.assertEqual(assembly.vote_type_ids, vote_type)
        self.assertEqual(assembly.quorum_type, "fixed")
        self.assertEqual(assembly.quorum_value, 10.0)
        self.assertEqual(assembly.quorum_second_call_type, "percentage")
        self.assertEqual(assembly.quorum_second_call_value, 20.0)
        self.assertEqual(assembly.partner_domain, domain)

    def test_create_respects_explicit_values(self):
        """create() respects explicit values even if assembly_type has defaults."""
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
                "vote_type_ids": [(6, 0, vote_type1.ids)],
                "default_quorum_type": "percentage",
                "default_quorum_value": 50.0,
                "default_quorum_second_call_type": "any",
                "default_quorum_second_call_value": 0.0,
                "partner_domain": "[]",
            }
        )
        # Create assembly WITH explicit values (should NOT be overridden)
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Test Assembly",
                "assembly_type_id": assembly_type.id,
                "vote_type_ids": [(6, 0, vote_type2.ids)],  # Explicit
                "quorum_type": "fixed",  # Explicit
                "quorum_value": 5.0,  # Explicit
                "quorum_second_call_type": "percentage",  # Explicit
                "quorum_second_call_value": 15.0,  # Explicit
                "partner_domain": "[('id', '=', 1)]",  # Explicit
            }
        )
        # Verify explicit values are respected (not inherited)
        self.assertEqual(assembly.vote_type_ids, vote_type2)
        self.assertEqual(assembly.quorum_type, "fixed")
        self.assertEqual(assembly.quorum_value, 5.0)
        self.assertEqual(assembly.quorum_second_call_type, "percentage")
        self.assertEqual(assembly.quorum_second_call_value, 15.0)
        self.assertEqual(assembly.partner_domain, "[('id', '=', 1)]")

    def test_create_without_assembly_type_id_no_inheritance(self):
        """create() without assembly_type_id does not inherit anything."""
        # Create assembly WITHOUT assembly_type_id
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Test Assembly",
                # assembly_type_id NOT provided
            }
        )
        # Verify defaults (not from type)
        self.assertFalse(assembly.assembly_type_id)
        self.assertFalse(assembly.vote_type_ids)
        self.assertEqual(assembly.quorum_type, "percentage")  # Model default
        self.assertEqual(assembly.quorum_value, 50.0)  # Model default
        self.assertEqual(assembly.quorum_second_call_type, "any")  # Model default
        self.assertEqual(assembly.quorum_second_call_value, 0.0)  # Model default
        self.assertEqual(assembly.partner_domain, "[]")  # Model default

    def test_create_inherits_partner_domain_empty_fallback(self):
        """create() uses '[]' as fallback when partner_domain is empty in type."""
        assembly_type = self.env["assembly.type"].create(  # noqa: F841
            {
                "name": "Test Type",
                "code": "TEST",
                "partner_domain": False,  # Empty/False
            }
        )
        # Create assembly
        assembly = self.env["assembly.assembly"].create(  # noqa: F841
            {
                "name": "Test Assembly",
                "assembly_type_id": assembly_type.id,
            }
        )
        # Verify fallback to "[]"
        self.assertEqual(assembly.partner_domain, "[]")
