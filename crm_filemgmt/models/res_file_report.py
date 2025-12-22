# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResFileReport(models.Model):
    _name = "res.file.report"
    _description = "Report of Files"
    _order = "name"

    # Add active flag
    active = fields.Boolean(
        default=True, help="Uncheck to archive this report template"
    )

    # Add report type/category
    report_type = fields.Selection(
        [
            ("summary", "Summary Report"),
            ("detailed", "Detailed Report"),
            ("label", "Label/Sticker"),
            ("inventory", "Inventory Report"),
            ("custom", "Custom Report"),
        ],
        string="Report Type",
        default="custom",
        required=True,
    )

    # Add paper format
    paperformat_id = fields.Many2one(
        comodel_name="report.paperformat",
        string="Paper Format",
        help="Paper format for this report (A4, Letter, etc.)",
    )

    # Add orientation
    orientation = fields.Selection(
        [
            ("portrait", "Portrait"),
            ("landscape", "Landscape"),
        ],
        string="Orientation",
        default="portrait",
    )

    # Add header/footer templates
    report_template_header = fields.Html(
        string="Header Template",
        translate=True,
        help="Optional header template for the report",
    )

    report_template_footer = fields.Html(
        string="Footer Template",
        translate=True,
        help="Optional footer template for the report",
    )

    # Add CSS styles
    custom_css = fields.Text(
        string="Custom CSS", help="Custom CSS styles for this report"
    )

    # Add preview image
    preview_image = fields.Image(
        string="Preview Image",
        max_width=800,
        max_height=600,
        help="Preview image of the report output",
    )

    # Add usage counter
    usage_count = fields.Integer(
        string="Usage Count",
        compute="_compute_usage_count",
        store=True,
        help="Number of times this report has been used",
    )

    name = fields.Char(
        string="Report Name",
        required=True,
        translate=False,
        index=True,
        help="Human-readable name of the report.",
    )

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

    @api.depends("file_ids")
    def _compute_usage_count(self):
        for report in self:
            report.usage_count = len(report.file_ids)

    # Add method to test report
    def action_test_report(self):
        """Generate a test report preview."""
        self.ensure_one()
        # Create a test file or use existing one
        test_file = self.env["res.file"].search([], limit=1)
        if test_file:
            return self.iractreportxml_id.report_action(test_file)
        return False

    # Add method to duplicate report
    def action_duplicate_report(self):
        """Duplicate this report template."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Duplicate Report",
            "res_model": self._name,
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_name": f"{self.name} (Copy)",
                "default_iractreportxml_id": self.iractreportxml_id.id,
                "default_report_template_start": self.report_template_start,
                "default_report_template_end": self.report_template_end,
            },
        }
