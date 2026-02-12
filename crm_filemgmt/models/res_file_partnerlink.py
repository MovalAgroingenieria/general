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
        comodel_name="res.file",
        required=True,
        index=True,
        ondelete="cascade",
    )
    partner_id = fields.Many2one(
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

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-set is_main=True if this is the first/only partnerlink for a file."""
        records = super().create(vals_list)
        self._auto_set_main(records)
        return records

    def write(self, vals):
        """Handle is_main changes and auto-set when needed."""
        res = super().write(vals)
        # If is_main was set to True, unset it on other links for the same file
        if vals.get("is_main"):
            for record in self:
                siblings = record.file_id.partnerlink_ids - record
                siblings.filtered(lambda link: link.is_main).write({"is_main": False})
        return res

    def _auto_set_main(self, records):
        """Set is_main=True if file has exactly one partnerlink and none is main."""
        for record in records:
            if not record.file_id:
                continue
            links = record.file_id.partnerlink_ids
            if len(links) == 1 and not links.is_main:
                links.write({"is_main": True})
