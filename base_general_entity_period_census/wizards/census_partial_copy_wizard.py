# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from dateutil.relativedelta import relativedelta
from odoo import Command, api, fields, models
from odoo.exceptions import UserError


class CensusPartialCopyWizard(models.TransientModel):
    _name = "census.partial.copy.wizard"
    _description = "Copy Selected Members to Next Period"

    census_id = fields.Many2one(
        comodel_name="general.entity.census",
        required=True,
        readonly=True,
    )
    next_period_date = fields.Date(
        compute="_compute_next_period_date",
    )
    line_ids = fields.Many2many(
        comodel_name="general.entity.census.line",
        string="Lines to Copy",
        help="Select which census lines to copy to the next period.",
    )
    copy_additional = fields.Boolean(
        string="Copy Additional Movements",
        default=True,
        help="Also copy additional movements for each selected line.",
    )

    @api.depends("census_id")
    def _compute_next_period_date(self):
        for wiz in self:
            if wiz.census_id:
                wiz.next_period_date = (
                    # pylint: disable=protected-access
                    wiz.census_id._get_next_period_date()
                )
            else:
                wiz.next_period_date = False

    def default_get(self, fields_list):
        """Pre-populate all lines from the census."""
        res = super().default_get(fields_list)
        census_id = self.env.context.get("active_id")
        if census_id:
            census = self.env["general.entity.census"].browse(census_id)
            res["census_id"] = census.id
            res["line_ids"] = [fields.Command.set(census.line_ids.ids)]
        return res

    def action_copy(self):
        """Copy selected lines to a new census in the next period."""
        self.ensure_one()
        census = self.census_id

        next_date = census._get_next_period_date()  # pylint: disable=protected-access
        if not next_date:
            raise UserError(self.env._("Cannot calculate next period date."))

        # Check if census already exists for next period
        existing = self.env["general.entity.census"].search(
            [
                (
                    "primary_partner_id",
                    "=",
                    census.primary_partner_id.id,
                ),
                ("period_date", "=", next_date),
            ],
            limit=1,
        )
        if existing:
            raise UserError(
                self.env._(
                    "A census already exists for period %(period)s. "
                    "Delete it first or edit it directly.",
                    period=existing.period_name,
                )
            )

        if not self.line_ids:
            raise UserError(self.env._("Please select at least one line to copy."))

        # Prepare lines to copy
        lines_to_create = []
        for line in self.line_ids:
            line_vals = {
                "member_partner_id": line.member_partner_id.id,
                "shares": line.shares,
                "note": line.note,
                "previous_line_id": line.id,
            }
            if self.copy_additional:
                additional_cmds = []
                for addtnl in line.additional_ids:
                    additional_cmds.append(
                        Command.create(
                            {
                                "qty": addtnl.qty,
                                "note": addtnl.note,
                            }
                        )
                    )
                line_vals["additional_ids"] = additional_cmds
            lines_to_create.append(Command.create(line_vals))

        # Build new census values
        new_vals = {
            "primary_partner_id": census.primary_partner_id.id,
            "period_date": next_date,
            "period_type": census.period_type,
            "distribution_product_id": (
                census.distribution_product_id.id
                if census.distribution_product_id
                else False
            ),
            "distribution_amount_day": census.distribution_amount_day,
            "line_ids": lines_to_create,
        }

        # Handle custom period dates
        if census.period_type == "custom" and census.period_start_date:
            delta = census.period_end_date - census.period_start_date
            new_vals["period_start_date"] = census.period_start_date + relativedelta(
                days=delta.days + 1
            )
            new_vals["period_end_date"] = census.period_end_date + relativedelta(
                days=delta.days + 1
            )

        new_census = self.env["general.entity.census"].create(new_vals)

        return {
            "type": "ir.actions.act_window",
            "res_model": "general.entity.census",
            "res_id": new_census.id,
            "view_mode": "form",
            "target": "current",
        }
