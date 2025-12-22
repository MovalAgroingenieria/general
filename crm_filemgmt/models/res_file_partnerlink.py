# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResFilePartnerlink(models.Model):
    _name = "res.file.partnerlink"
    _description = "File Partnerlink"

    # Add ordering for better UI experience
    _order = "is_main desc, partner_id"

    # Add default ordering for search
    _rec_name = "partner_id"

    file_id = fields.Many2one(
        string="File",
        comodel_name="res.file",
        required=True,
        index=True,
        ondelete="cascade",
    )
    partner_id = fields.Many2one(
        string="Partner",
        comodel_name="res.partner",
        required=True,
        index=True,
        ondelete="restrict",
        domain=[("is_company", "=", True)],  # Optional: Restrict to company partners
    )
    is_main = fields.Boolean(
        string="Primary",
        default=False,
        help="If checked, this partner will be the primary partner for the file",
    )

    # Related fields with store=True for better performance if frequently accessed
    subject = fields.Char(
        string="Subject",
        related="file_id.subject",
        store=True,
        readonly=True,
    )
    date_file = fields.Date(
        string="Discharge date",
        related="file_id.date_file",
        store=True,
        readonly=True,
    )
    stage_id = fields.Many2one(
        string="Stage",
        related="file_id.stage_id",
        store=True,
        readonly=True,
    )
    category_id = fields.Many2one(
        string="Category",
        related="file_id.category_id",
        store=True,
        readonly=True,
    )

    # Add computed field for display
    display_name = fields.Char(
        string="Display Name",
        compute="_compute_display_name",
        store=True,
    )

    @api.depends("partner_id", "is_main")
    def _compute_display_name(self):
        for record in self:
            name = record.partner_id.name or ""
            if record.is_main:
                name = f"{name} (Primary)"
            record.display_name = name
