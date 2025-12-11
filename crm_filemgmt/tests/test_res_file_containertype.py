# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import unittest

from odoo.tests.common import TransactionCase
from odoo import fields, models

try:
    from odoo.tests.common import SavepointCase as BaseCase
except ImportError:
    BaseCase = TransactionCase

# psycopg2 exceptions for SQL constraint checks
try:
    # psycopg2 >= 2.8 exposes granular errors
    from psycopg2.errors import UniqueViolation as PgUniqueViolation

    _PG_ERR = PgUniqueViolation
except ImportError:  # pragma: no cover
    # Fallback to base IntegrityError if needed
    from psycopg2 import IntegrityError as PgIntegrityError

    _PG_ERR = PgIntegrityError


class TestResFileContainerType(BaseCase):
    """Tests for res.file.containertype (Odoo/OCB 18)."""

    def setUp(self):
        super().setUp()
        # Create test location
        self.location = self.env['res.file.location'].create({
            'name': 'Test Location',
            'description': 'Test Location Description',
        })
        # Create test container type
        self.container_type = self.env['res.file.containertype'].create({
            'name': 'Test Type',
            'description': 'Test Type Description',
        })
        # Create test container
        self.container = self.env['res.file.container'].create({
            'name': 'CTN-001',
            'description': 'Test Container',
            'location_id': self.location.id,
            'containertype_id': self.container_type.id,
        })

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.Model = cls.env["res.file.containertype"]

    def test_create_minimal(self):
        """Creating a minimal container type with just 'name' should work."""
        rec = self.Model.create({"name": "Box"})
        self.assertTrue(rec.id)
        self.assertEqual(rec.name, "Box")
        self.assertFalse(rec.description)
        self.assertFalse(rec.notes)


    def test_default_order_by_name(self):
        """Default ordering should be by 'name' ascending."""
        self.Model.create({"name": "Crate"})
        self.Model.create({"name": "Archive"})
        self.Model.create({"name": "Zipper"})

        # search() without explicit order must respect _order = 'name'
        recs = self.Model.search([])
        names = [r.name for r in recs]
        # ensure relative order among our three records is alphabetical
        # (other pre-existing records in DB won't break this assertion)
        idx = {n: names.index(n) for n in ["Archive", "Crate", "Zipper"]}
        self.assertLess(idx["Archive"], idx["Crate"])
        self.assertLess(idx["Crate"], idx["Zipper"])

    def test_container_creation(self):
        """Test basic container creation."""
        self.assertEqual(self.container.name, 'CTN-001')
        self.assertEqual(self.container.description, 'Test Container')
        self.assertEqual(self.container.location_id, self.location)
        self.assertEqual(self.container.containertype_id, self.container_type)
        self.assertEqual(self.container.number_of_files, 0)

    def test_file_count_computation(self):
        """Test file count computation."""
        # Create test files
        file1 = self.env['res.file'].create({
            'alphanum_code': 'TEST-2024/0001',
            'subject': 'Test File 1',
            'date_file': fields.Date.today(),
            'category_id': self.env.ref('crm_filemgmt.resfilecategory_internal_file').id,
            'stage_id': self.env['res.file.stage'].search([], limit=1).id,
            'container_id': self.container.id,
        })
        file2 = self.env['res.file'].create({
            'alphanum_code': 'TEST-2024/0002',
            'subject': 'Test File 2',
            'date_file': fields.Date.today(),
            'category_id': self.env.ref('crm_filemgmt.resfilecategory_internal_file').id,
            'stage_id': self.env['res.file.stage'].search([], limit=1).id,
            'container_id': self.container.id,
        })

        self.assertEqual(self.container.number_of_files, 2)
        self.assertIn(file1, self.container.file_ids)
        self.assertIn(file2, self.container.file_ids)

    def test_display_name_computation(self):
        """Test display name computation with and without context."""
        # Test without extra context
        self.assertEqual(self.container.display_name, 'Test Container [CTN-001]')

        # Test with extra context
        container_with_ctx = self.container.with_context(show_container_data=True)
        display_name = container_with_ctx.display_name
        self.assertIn('Test Container [CTN-001]', display_name)

    def test_action_get_files(self):
        """Test the action to get files."""
        # Create a file first
        self.env['res.file'].create({
            'alphanum_code': 'TEST-2024/0001',
            'subject': 'Test File',
            'date_file': fields.Date.today(),
            'category_id': self.env.ref('crm_filemgmt.resfilecategory_internal_file').id,
            'stage_id': self.env['res.file.stage'].search([], limit=1).id,
            'container_id': self.container.id,
        })

        action = self.container.action_get_files()
        self.assertIsNotNone(action)
        self.assertEqual(action['res_model'], 'res.file')
        self.assertEqual(action['domain'], [('container_id', '=', self.container.id)])
        self.assertEqual(action['context']['default_container_id'], self.container.id)
if __name__ == "__main__":
    unittest.main()
