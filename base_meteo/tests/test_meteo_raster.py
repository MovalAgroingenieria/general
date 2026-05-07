# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import numpy as np

from odoo.tests import common


@common.at_install(False)
@common.post_install(True)
class TestMeteoRasterKernels(common.TransactionCase):
    """Pure numerical tests of the interpolation kernels.

    These do not write any COG; they only exercise the math, so they
    run fast and do not require gdal_translate.
    """

    def setUp(self):
        super(TestMeteoRasterKernels, self).setUp()
        self.Raster = self.env['meteo.raster']

    def test_idw_at_station_returns_station_value(self):
        # Three stations forming a triangle with distinct values.
        xs = np.array([0.0, 100.0, 50.0])
        ys = np.array([0.0, 0.0, 80.0])
        vs = np.array([10.0, 20.0, 30.0])
        # Grid sampling exactly the station coordinates.
        gx = xs.copy()
        gy = np.array([0.0, 80.0])
        out = self.Raster._idw(xs, ys, vs, gx, gy, power=2.0)
        # First row: y=0, columns 0/1 are stations 0/1.
        self.assertAlmostEqual(out[0, 0], 10.0, places=2)
        self.assertAlmostEqual(out[0, 1], 20.0, places=2)
        # Second row: y=80, column 2 is station 2.
        self.assertAlmostEqual(out[1, 2], 30.0, places=2)

    def test_idw_clamped_to_value_range(self):
        xs = np.array([0.0, 100.0])
        ys = np.array([0.0, 0.0])
        vs = np.array([5.0, 25.0])
        gx = np.linspace(0.0, 100.0, 5)
        gy = np.array([0.0])
        out = self.Raster._idw(xs, ys, vs, gx, gy, power=2.0)
        # Output should never go below min value or above max value.
        self.assertGreaterEqual(out.min(), 5.0 - 1e-6)
        self.assertLessEqual(out.max(), 25.0 + 1e-6)

    def test_constant_method_via_dispatch(self):
        out = self.Raster._interpolate(
            'constant', {},
            np.array([0.0]), np.array([0.0]), np.array([42.0]),
            np.linspace(0, 100, 4), np.linspace(0, 100, 3))
        self.assertEqual(out.shape, (3, 4))
        self.assertTrue(np.allclose(out, 42.0))

    def test_idw_knn_falls_back_when_k_exceeds_n(self):
        # Should not crash; k clamps to n.
        xs = np.array([0.0, 50.0])
        ys = np.array([0.0, 50.0])
        vs = np.array([1.0, 9.0])
        gx = np.linspace(0, 100, 4)
        gy = np.linspace(0, 100, 4)
        out = self.Raster._idw_knn(xs, ys, vs, gx, gy, power=2.0, k=20)
        self.assertEqual(out.shape, (4, 4))
        self.assertTrue(np.isfinite(out).all())
