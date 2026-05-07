# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class MeteoAggregation(models.Model):
    _name = 'meteo.aggregation'
    _description = 'Meteorological Aggregation'
    _order = 'sequence, name, id'

    name = fields.Char(
        string='Name',
        required=True,
        translate=True,
    )

    code = fields.Char(
        string='Code',
        required=True,
        help='Stable technical key used by the compute pipeline '
             '(e.g. avg, sum, min, max, last).',
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order of appearance in product aggregation selectors.',
    )

    description = fields.Text(
        string='Description',
        translate=True,
    )

    python_method_name = fields.Char(
        string='Python Method',
        compute='_compute_python_method_name',
        store=True,
        readonly=True,
        help='Convention used by custom composite aggregations: '
             '_meteo_aggr_<code>.',
    )

    active = fields.Boolean(
        default=True,
    )

    _sql_constraints = [
        ('code_uniq', 'unique(code)',
         'The aggregation code must be unique.'),
    ]

    @api.depends('code')
    def _compute_python_method_name(self):
        for record in self:
            record.python_method_name = '_meteo_aggr_%s' % (
                (record.code or '').strip())
