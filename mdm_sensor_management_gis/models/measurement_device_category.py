# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from jinja2 import Markup
import json
import random


class MeasurementDeviceCategory(models.Model):
    _inherit = 'mdm.measurement.device.category'

    available_for_gis_devices = fields.Boolean(
        string='Available in Devices Mode',
        default=True,
        help='Make this category available in GIS devices visualization mode',
    )

    geojson_style = fields.Text(
        string='GeoJSON style for viewer data',
        help='GeoJSON style for viewer data.',
        default="""
        {
          "radius": 6,
          "fillColor": "#ff7800",
          "color": "#000",
          "weight": 1,
          "opacity": 1,
          "fillOpacity": 0.5
        }
        """,
    )

    geojson_style_preview = fields.Html(
        string="Style Preview",
        compute="_compute_geojson_style_preview",
        sanitize=False,
    )

    legend_symbology = fields.Text(
        string='Legend symbology viewer data',
        help='Legend symbology for viewer data.',
        default="""
        [
            {
                "fontAwesomeSymbol": "fas fa-circle",
                "color": "#ff7800",
                "name": "Normal"
            }
        ]
        """,
    )

    symbology_rule_ids = fields.One2many(
        comodel_name='mdm.measurement.device.symbology.rule',
        inverse_name='category_id',
        string='Symbology Rules',
    )

    def _generate_random_color(self):
        return "#{:06x}".format(random.randint(0, 0xFFFFFF))

    def _generate_random_style(self):
        self.ensure_one()
        try:
            style = json.loads(self.geojson_style or '{}')
        except Exception:
            style = {}
        new_fill_color = self._generate_random_color()
        new_border_color = self._generate_random_color()
        style['fillColor'] = new_fill_color
        style['color'] = new_border_color
        legend_symbology = [
            {
                "fontAwesomeSymbol": "far fa-check-circle",
                "color": new_fill_color,
                "name": "Normal",
            },
        ]
        return json.dumps(style, indent=2), json.dumps(
            legend_symbology, indent=2)

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

    @api.multi
    def action_randomize_style(self):
        self.ensure_one()
        geojson_style, legend_symbology = self._generate_random_style()
        self.geojson_style = geojson_style
        self.legend_symbology = legend_symbology
