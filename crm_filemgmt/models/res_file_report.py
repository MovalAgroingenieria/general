# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResFileReport(models.Model):
    _name = "res.file.report"
    _description = "Report of Files"
    _order = "name"

    # Display name (translatable)
    name = fields.Char(
        string="Report Name",
        required=True,
        translate=False,
        index=True,
        help="Human-readable name of the report.",
    )

    # Base ir.actions.report to use when printing from res.file
    iractreportxml_id = fields.Many2one(
        string="Template base",
        comodel_name="ir.actions.report",
        default=lambda self: self.env.ref(
            "crm_filemgmt.res_file_report_base", raise_if_not_found=False
        ),
        domain=[("model", "=", "res.file"), ("report_type", "=", "qweb-pdf")],
        help="Default report action used for printing file records.",
    )

    report_template_start = fields.Html(
        string="Template start",
        translate=True,
        help="Optional HTML/Jinja template rendered at the beginning of the report.",
    )

    report_template_end = fields.Html(
        string="Template end",
        translate=True,
        help="Optional HTML/Jinja template rendered at the end of the report.",
    )

    file_ids = fields.One2many(
        string="Files",
        comodel_name="res.file",
        inverse_name="file_report_id",
    )

    notes = fields.Html()

    _sql_constraints = [
        ("unique_name", "UNIQUE (name)", "Existing report name."),
    ]
