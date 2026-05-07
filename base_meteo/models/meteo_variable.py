# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json

from odoo import api, exceptions, fields, models, _


# QGIS-style ramps as ordered lists of "#rrggbb". The number of colours
# is the natural number of control points of each ramp; we resample to
# `palette_stops` using piecewise linear interpolation in RGB space.
_COLOR_RAMPS = {
    'viridis': [
        '#440154', '#3b528b', '#21918c', '#5ec962', '#fde725'],
    'plasma': [
        '#0d0887', '#7e03a8', '#cc4778', '#f89540', '#f0f921'],
    'inferno': [
        '#000004', '#420a68', '#932667', '#dd513a', '#fcffa4'],
    'magma': [
        '#000004', '#3b0f70', '#8c2981', '#de4968', '#fcfdbf'],
    'turbo': [
        '#30123b', '#4662d8', '#36ace3', '#7ff058', '#fbb318',
        '#d23105', '#7a0403'],
    'rdylbu_r': [
        '#313695', '#74add1', '#e0f3f8', '#fee090', '#f46d43',
        '#a50026'],
    'spectral_r': [
        '#5e4fa2', '#3288bd', '#abdda4', '#fee08b', '#f46d43',
        '#9e0142'],
    'rdylgn': [
        '#a50026', '#f46d43', '#fee08b', '#a6d96a', '#1a9850'],
}


def _hex_to_rgb(value):
    value = value.lstrip('#')
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def _rgb_to_hex(rgb):
    return '#%02x%02x%02x' % (
        max(0, min(255, int(round(rgb[0])))),
        max(0, min(255, int(round(rgb[1])))),
        max(0, min(255, int(round(rgb[2])))))


def _interp_palette(name, stops):
    """Resample a named ramp to `stops` colours."""
    base = [_hex_to_rgb(c) for c in _COLOR_RAMPS[name]]
    if stops <= 1:
        return [_rgb_to_hex(base[0])]
    out = []
    last = len(base) - 1
    for i in range(stops):
        pos = (float(i) / (stops - 1)) * last
        lo = int(pos)
        hi = min(lo + 1, last)
        frac = pos - lo
        rgb = (
            base[lo][0] + (base[hi][0] - base[lo][0]) * frac,
            base[lo][1] + (base[hi][1] - base[lo][1]) * frac,
            base[lo][2] + (base[hi][2] - base[lo][2]) * frac,
        )
        out.append(_rgb_to_hex(rgb))
    return out


class MeteoVariable(models.Model):
    _name = 'meteo.variable'
    _description = 'Meteorological Variable'
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True,
        translate=True,
    )

    code = fields.Char(
        string='Code',
        required=True,
        help='Short identifier (e.g. T, P, HR, ET0).',
    )

    uom_id = fields.Many2one(
        comodel_name='mdm.measurement.device.sensor.uom',
        string='Unit of Measure',
    )

    sensor_type_ids = fields.Many2many(
        comodel_name='mdm.measurement.device.sensor.type',
        string='Sensor Types',
        help='Sensor types that feed this variable. Readings whose '
             'sensor.type_id is in this set are aggregated for the product.',
    )

    compatible_aggregation_ids = fields.Many2many(
        comodel_name='meteo.aggregation',
        relation='meteo_variable_aggregation_rel',
        column1='variable_id',
        column2='aggregation_id',
        string='Compatible Aggregations',
        help='Aggregations allowed for products using this variable. '
             'If empty, all active aggregations are considered valid.',
    )

    default_method = fields.Selection(
        selection=[
            ('idw', 'IDW'),
            ('idw_knn', 'IDW KNN'),
            ('nearest', 'Nearest'),
        ],
        string='Default Interpolation Method',
        default='idw',
        help='Default interpolation method suggested when creating '
             'a product for this variable.',
    )

    default_p = fields.Float(
        string='Default IDW Power',
        default=2.0,
        help='Default IDW exponent suggested for products using this '
             'variable.',
    )

    min_value = fields.Float(
        string='Min Physical Value',
        default=-1e9,
        help='Output values are clamped to this minimum after '
             'interpolation.',
    )

    max_value = fields.Float(
        string='Max Physical Value',
        default=1e9,
        help='Output values are clamped to this maximum after '
             'interpolation.',
    )

    color_ramp = fields.Text(
        string='Color Ramp (JSON)',
        help='Optional JSON array of [stop_value, "#rrggbb"] tuples used '
             'by the front-end to render the legend. Example: '
             '[[0, "#0000ff"], [15, "#00ff00"], [30, "#ff0000"]].',
    )

    palette = fields.Selection(
        selection=[
            ('viridis', 'Viridis'),
            ('plasma', 'Plasma'),
            ('inferno', 'Inferno'),
            ('magma', 'Magma'),
            ('turbo', 'Turbo'),
            ('rdylbu_r', 'Red-Yellow-Blue (reversed)'),
            ('spectral_r', 'Spectral (reversed)'),
            ('rdylgn', 'Red-Yellow-Green'),
        ],
        string='Palette',
        default='viridis',
        help='QGIS-style palette used by the "Generate Color Ramp" '
             'button to build a fresh ramp from min/max.',
    )

    palette_stops = fields.Integer(
        string='Palette Stops',
        default=7,
        help='Number of colour stops to interpolate over [min, max] '
             'when generating the ramp. Typical: 5-11.',
    )

    color_ramp_preview = fields.Html(
        string='Color Ramp Preview',
        compute='_compute_color_ramp_preview',
        sanitize=False,
        help='Visual preview of the stored color ramp: gradient bar '
             'with the stop values underneath. Re-renders on save '
             'after pressing "Generate Color Ramp".',
    )

    active = fields.Boolean(
        default=True,
    )

    _sql_constraints = [
        ('code_uniq', 'unique(code)',
         'The variable code must be unique.'),
    ]

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            label = '%s (%s)' % (record.name, record.code) \
                if record.code else record.name
            result.append((record.id, label))
        return result

    @api.multi
    def action_generate_color_ramp(self):
        """Fill `color_ramp` with `palette_stops` evenly spaced
        colours from the selected palette, mapping linearly onto
        [min_value, max_value]. Mirrors the QGIS "Apply" button on a
        single-band pseudo-colour styling.
        """
        for record in self:
            stops = max(int(record.palette_stops or 0), 2)
            palette = record.palette or 'viridis'
            colours = _interp_palette(palette, stops)
            lo = record.min_value
            hi = record.max_value
            if hi <= lo:
                raise exceptions.UserError(_(
                    'Cannot generate ramp: max_value (%s) must be '
                    'greater than min_value (%s).') % (hi, lo))
            ramp = []
            for i, hex_colour in enumerate(colours):
                value = lo + (hi - lo) * (float(i) / (stops - 1))
                ramp.append([round(value, 4), hex_colour])
            record.color_ramp = json.dumps(ramp)
        return True

    @api.depends('color_ramp')
    def _compute_color_ramp_preview(self):
        """Render the stored ramp as an HTML gradient bar with value
        ticks. Non-stored, derived from `color_ramp` on every read.
        """
        empty_msg = _('No color ramp defined yet. '
                      'Pick a palette and click "Generate Color Ramp".')
        for record in self:
            try:
                ramp = json.loads(record.color_ramp or '[]')
            except (TypeError, ValueError):
                ramp = []
            if len(ramp) < 2:
                record.color_ramp_preview = (
                    u'<div style="color:#888;font-style:italic;">%s</div>'
                    % empty_msg)
                continue
            lo = float(ramp[0][0])
            hi = float(ramp[-1][0])
            span = hi - lo if hi > lo else 1.0
            gradient_stops = ', '.join(
                '%s %.2f%%' % (color, (float(value) - lo) * 100.0 / span)
                for value, color in ramp)
            tick_cells = ''.join(
                u'<td style="text-align:center;font-size:11px;'
                u'color:#444;padding:2px 0;">%g</td>' % float(value)
                for value, _color in ramp)
            swatch_cells = ''.join(
                u'<td style="background:%s;height:18px;'
                u'border:1px solid #888;"></td>' % color
                for _value, color in ramp)
            record.color_ramp_preview = (
                u'<div style="max-width:600px;">'
                u'<div style="height:28px;border:1px solid #444;'
                u'background:linear-gradient(to right, %s);"></div>'
                u'<table style="width:100%%;table-layout:fixed;'
                u'border-collapse:collapse;margin-top:6px;">'
                u'<tr>%s</tr><tr>%s</tr></table>'
                u'</div>'
            ) % (gradient_stops, swatch_cells, tick_cells)
