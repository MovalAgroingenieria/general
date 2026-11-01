# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    deca_ids = fields.One2many(
        "deca.document",
        "picking_id",
        string="DECA Documents",
    )
    deca_count = fields.Integer(
        compute="_compute_deca_count",
        string="DECA Count",
    )

    @api.depends("deca_ids")
    def _compute_deca_count(self):
        # pylint: disable=protected-access
        deca_data = self.env["deca.document"]._read_group(
            [("picking_id", "in", self.ids)],
            ["picking_id"],
            ["__count"],
        )
        mapped_count = {
            picking.id: count for picking, count in deca_data
        }
        for picking in self:
            picking.deca_count = mapped_count.get(picking.id, 0)

    def _deca_move_quantity(self, move):
        return move.quantity or move.product_uom_qty

    def _prepare_deca_line_vals(self, move):
        quantity = self._deca_move_quantity(move)
        return {
            "product_id": move.product_id.id,
            "name": move.product_id.display_name,
            "quantity": quantity,
            "uom_name": move.product_uom.name,
            "weight_kg": move.product_id.weight * quantity,
        }

    def _prepare_deca_vals(self):
        self.ensure_one()
        partner = self.partner_id
        line_vals = [
            (0, 0, self._prepare_deca_line_vals(move))
            for move in self.move_ids
        ]
        return {
            "company_id": self.company_id.id,
            "picking_id": self.id,
            "loading_partner_id": partner.id,
            "loading_name": partner.name,
            "loading_vat": partner.vat,
            "loading_address": ", ".join(
                filter(
                    None,
                    [partner.street, partner.street2, partner.zip_id.display_name],
                )
            ),
            "origin": self.location_id.company_id.zip_id.display_name,
            "destination": ", ".join(
                filter(
                    None,
                    [partner.street, partner.street2, partner.zip_id.display_name],
                )
            ),
            "transport_date": self.scheduled_date
            and self.scheduled_date.date(),
            "goods_description": self.origin or self.name,
            "weight_kg": sum(
                move.product_id.weight * self._deca_move_quantity(move)
                for move in self.move_ids
            ),
            "line_ids": line_vals,
        }

    def _create_and_open_deca(self):
        self.ensure_one()
        deca = self.env["deca.document"].create(self._prepare_deca_vals())
        return self._open_deca_form(deca)

    def _open_deca_form(self, deca):
        return {
            "type": "ir.actions.act_window",
            "res_model": "deca.document",
            "res_id": deca.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_prepare_deca(self):
        self.ensure_one()
        draft_deca = self.deca_ids.filtered(lambda deca: deca.state == "draft")
        if draft_deca:
            return self._open_deca_form(draft_deca[0])
        issued_deca = self.deca_ids.filtered(
            lambda deca: deca.state == "issued"
        )
        if issued_deca:
            return {
                "type": "ir.actions.act_window",
                "name": self.env._("New DECA for this transfer"),
                "res_model": "deca.new.confirm",
                "view_mode": "form",
                "target": "new",
                "context": {"default_picking_id": self.id},
            }
        return self._create_and_open_deca()

    def action_view_deca(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": self.env._("DECA Documents"),
            "res_model": "deca.document",
            "domain": [("picking_id", "=", self.id)],
            "context": {"default_picking_id": self.id},
        }
        if self.deca_count == 1:
            action.update(
                res_id=self.deca_ids.id,
                view_mode="form",
            )
        else:
            action.update(view_mode="list,form")
        return action
