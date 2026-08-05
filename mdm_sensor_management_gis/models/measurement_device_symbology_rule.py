# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from jinja2 import Markup
import json


class MeasurementDeviceSymbologyRule(models.Model):
    _name = 'mdm.measurement.device.symbology.rule'
    _description = 'Measurement Device Symbology Rule'
    _order = 'sequence, id'

    name = fields.Char(
        string='Name',
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Evaluation order. The first matching rule (lowest sequence) '
             'wins.',
    )

    active = fields.Boolean(
        string='Active',
        default=True,
    )

    category_id = fields.Many2one(
        string='Category',
        comodel_name='mdm.measurement.device.category',
        required=True,
        ondelete='cascade',
        index=True,
    )

    sensor_type_id = fields.Many2one(
        string='Sensor Type',
        comodel_name='mdm.measurement.device.sensor.type',
        required=True,
        ondelete='cascade',
        help='The rule is evaluated against the last reading of a sensor of '
             'this type in the device.',
    )

    operator = fields.Selection(
        string='Operator',
        selection=[
            ('gt', '>'),
            ('ge', '>='),
            ('lt', '<'),
            ('le', '<='),
            ('eq', '='),
            ('ne', '!='),
            ('between', 'between'),
        ],
        required=True,
        default='gt',
    )

    value = fields.Float(
        string='Value',
        digits=(32, 4),
    )

    value_max = fields.Float(
        string='Max Value',
        digits=(32, 4),
        help='Upper bound, only used with the "between" operator.',
    )

    animation = fields.Selection(
        string='Animation',
        selection=[
            ('none', 'None'),
            ('pulse', 'Pulse'),
        ],
        required=True,
        default='none',
        help='Optional animation applied to the marker in the viewer when '
             'this rule matches (e.g. a pulsing effect to represent an '
             'active/irrigating device).',
    )

    geojson_style = fields.Text(
        string='GeoJSON style override',
        help='GeoJSON style applied to the device when this rule matches.',
        default="""
        {
          "radius": 7,
          "fillColor": "#39FF14",
          "color": "#000",
          "weight": 1,
          "opacity": 1,
          "fillOpacity": 0.9
        }
        """,
    )

    geojson_style_preview = fields.Html(
        string='Style Preview',
        compute='_compute_geojson_style_preview',
        sanitize=False,
    )

    legend_symbology = fields.Text(
        string='Legend symbology',
        help='Optional legend entry shown in the viewer when this rule is '
             'active. Leave "name" empty to use the rule name as label.',
        default="""
        [
            {
                "fontAwesomeSymbol": "fas fa-circle",
                "color": "#39FF14",
                "name": ""
            }
        ]
        """,
    )

    @api.depends('geojson_style')
    def _compute_geojson_style_preview(self):
        for record in self:
            try:
                style = json.loads(record.geojson_style or '{}')
                fill = style.get('fillColor', '#ccc')
                stroke = style.get('color', '#000')
            except Exception:
                fill = '#ccc'
                stroke = '#000'
            svg = '''
            <svg width="60" height="60" xmlns="http://www.w3.org/2000/svg">
            <circle cx="30" cy="30" r="20"
                    fill="{fill}" stroke="{stroke}" stroke-width="3"/>
            </svg>
            '''.format(fill=fill, stroke=stroke)
            record.geojson_style_preview = Markup(svg)
