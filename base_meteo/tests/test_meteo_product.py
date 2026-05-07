# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import ValidationError
from odoo.tests import common


@common.at_install(False)
@common.post_install(True)
class TestMeteoProduct(common.TransactionCase):
    """Unit tests for meteo.product (no DB rasters generated)."""

    def setUp(self):
        super(TestMeteoProduct, self).setUp()
        self.variable = self.env['meteo.variable'].create({
            'name': 'Test Var',
            'code': 'TV',
            'min_value': 0.0,
            'max_value': 100.0,
        })
        self.product_vals = {
            'name': 'Test Product',
            'variable_id': self.variable.id,
            'srs': 'EPSG:3857',
            'extent_xmin': 0.0,
            'extent_ymin': 0.0,
            'extent_xmax': 50000.0,
            'extent_ymax': 50000.0,
            'aggregation': 'avg',
        }

    def test_extent_validation(self):
        bad = dict(self.product_vals, extent_xmax=0.0)
        with self.assertRaises(ValidationError):
            self.env['meteo.product'].create(bad)

    def test_grid_bounds_validation(self):
        bad = dict(self.product_vals, grid_min=8)
        with self.assertRaises(ValidationError):
            self.env['meteo.product'].create(bad)

    def test_recommend_method(self):
        product = self.env['meteo.product'].create(self.product_vals)
        self.assertEqual(product.recommend_method(0)[0], 'none')
        self.assertEqual(product.recommend_method(1)[0], 'constant')
        self.assertEqual(product.recommend_method(2)[0], 'idw')
        self.assertEqual(product.recommend_method(2)[1]['power'], 1.0)
        self.assertEqual(product.recommend_method(20)[0], 'idw')
        self.assertEqual(product.recommend_method(50)[0], 'idw_knn')

    def test_recommend_grid_size_bounds(self):
        product = self.env['meteo.product'].create(self.product_vals)
        # 1 station -> grid_min.
        self.assertEqual(
            product.recommend_grid_size(1), product.grid_min)
        # Many stations -> bounded by grid_max.
        self.assertLessEqual(
            product.recommend_grid_size(10000), product.grid_max)
        # Reasonable density -> within bounds.
        size = product.recommend_grid_size(20)
        self.assertGreaterEqual(size, product.grid_min)
        self.assertLessEqual(size, product.grid_max)

    def test_recommend_grid_size_manual(self):
        product = self.env['meteo.product'].create(dict(
            self.product_vals,
            auto_resolution=False,
            grid_size=384,
        ))
        self.assertEqual(product.recommend_grid_size(50), 384)

    def test_version_hash_changes(self):
        product = self.env['meteo.product'].create(self.product_vals)
        h1 = product.version_hash
        product.idw_power = 3.0
        product.flush() if hasattr(product, 'flush') else None
        h2 = product.version_hash
        self.assertNotEqual(h1, h2)
        product.idw_power = 2.0
        h3 = product.version_hash
        # Reverting recovers the original hash.
        self.assertEqual(h1, h3)
