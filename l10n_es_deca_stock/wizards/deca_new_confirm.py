# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class DecaNewConfirm(models.TransientModel):
    _name = "deca.new.confirm"
    _description = "Confirm New DECA for Transfer"

    picking_id = fields.Many2one(
        "stock.picking",
        string="Transfer",
        required=True,
    )
    existing_deca_ids = fields.Many2many(
        "deca.document",
        compute="_compute_existing_deca_ids",
        string="Existing DECA Documents",
    )

    @api.depends("picking_id")
    def _compute_existing_deca_ids(self):
        for wizard in self:
            wizard.existing_deca_ids = wizard.picking_id.deca_ids.filtered(
                lambda deca: deca.state == "issued"
            )

    def action_confirm(self):
        self.ensure_one()
        # pylint: disable=protected-access
        return self.picking_id._create_and_open_deca()
