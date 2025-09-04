# -*- coding: utf-8 -*-
# 2021 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import datetime
from odoo import models, fields, api, exceptions, _


class StatisticalSeries(models.AbstractModel):
    _name = 'statistical.series'
    _description = 'Statistical-Series Model'

    # Size of "masterrecord_name".
    MAX_SIZE_MASTERRECORD_NAME_FIELD = 50

    # If True, the name field will be calculated as
    # "masterrecord_name + data_date"; if False, it will be calculated as
    # "data_date + masterrecord_name".
    _date_first = True

    # Minimum value allowed for indices.
    _min_allowed_value = 0

    # Maximum value allowed for indices.
    _max_allowed_value = 100

    masterrecord_name = fields.Char(
        string='Related Entity',
        size=MAX_SIZE_MASTERRECORD_NAME_FIELD,
        index=True)

    data_date = fields.Date(
        string='Date',
        default=lambda self: fields.datetime.now(),
        required=True,
        index=True)

    name = fields.Char(
        string='Identifier',
        store=True,
        index=True,
        compute='_compute_name')

    min_value = fields.Float(
        string='Minimum',
        digits=(32, 4),
        default=0,
        required=True,
        index=True)

    mean_value = fields.Float(
        string='Mean',
        digits=(32, 4),
        default=0,
        required=True,
        index=True)

    max_value = fields.Float(
        string='Maximum',
        digits=(32, 4),
        default=0,
        required=True,
        index=True)

    stdev_value = fields.Float(
        string='SD',
        digits=(32, 4),
        default=0,
        required=True,
        index=True)

    geom_ewkt = fields.Char(
        string='EWKT Geometry',
        compute='_compute_geom_ewkt')

    _sql_constraints = [
        ('unique_name', 'UNIQUE (name)',
         'Existing record.'),
        ]

    @api.depends('masterrecord_name', 'data_date')
    def _compute_name(self):
        for record in self:
            name = ''
            if record.masterrecord_name and record.data_date:
                if self._date_first:
                    name = record.data_date + '|' + record.masterrecord_name
                else:
                    name = record.masterrecord_name + '|' + record.data_date
            record.name = name

    @api.constrains('masterrecord_name')
    def _check_partner_id(self):
        for record in self:
            if (not record.masterrecord_name):
                raise exceptions.UserError(
                    _('The related entity is required.'))

    @api.constrains('min_value', 'mean_value', 'max_value')
    def _check_indices(self):
        for record in self:
            if (self._min_allowed_value != 0 or
               self._max_allowed_value != 0):
                if record.min_value < self._min_allowed_value:
                    raise exceptions.UserError(
                        _('Incorrect index value: minimum value too low.'))
                if record.max_value > self._max_allowed_value:
                    raise exceptions.UserError(
                        _('Incorrect index value: maximum value too large.'))
                if (record.min_value > record.mean_value or
                   record.max_value < record.mean_value):
                    raise exceptions.UserError(
                        _('Incorrect index value: mean value out of limits.'))

    @api.constrains('stdev_value')
    def _check_stdev_value(self):
        for record in self:
            if record.stdev_value < 0:
                raise exceptions.UserError(
                    _('The standard deviation can not be a negative value.'))

    @api.multi
    def name_get(self):
        result = []
        lang = 'es_ES'
        if ('lang' in self.env.context and self.env.context['lang']):
            lang = self.env.context['lang']
        lang_model = self.env['res.lang'].search([('code', '=', lang)])
        for record in self:
            data_date = ''
            date_parsed = datetime.datetime.strptime(
                record.data_date, '%Y-%m-%d')
            data_date = str(date_parsed)
            if (lang_model):
                data_date = date_parsed.strftime(
                    lang_model.date_format)
            masterrecord_name = record.masterrecord_name
            name = masterrecord_name + ', ' + data_date
            if self._date_first:
                name = data_date + ', ' + masterrecord_name
            result.append((record.id, name))
        return result
