# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class ResFileReport(models.Model):
    _name = 'res.file.report'
    _description = 'Report of Files'

    name = fields.Char(
        string='Report Name',
        size=50,
        required=True,
        translate=True,
        index=True)

    iractreportxml_id = fields.Many2one(
        string='Template base',
        comodel_name='ir.actions.report',
        default=lambda self: self.env.ref(
            'crm_filemgmt.res_file_report_base'),
        domain=[('model', '=', 'res.file'),
                ('report_type', '=', 'qweb-pdf')])

    report_template_start = fields.Html(
        string='Template start',
        translate=True)

    report_template_end = fields.Html(
        string='Template end',
        translate=True)

    file_ids = fields.One2many(
        string='Files',
        comodel_name='res.file',
        inverse_name='file_report_id')

    notes = fields.Html(
        string='Notes')

    _sql_constraints = [
        ('unique_name', 'UNIQUE (name)', 'Existing report name.'),
    ]
