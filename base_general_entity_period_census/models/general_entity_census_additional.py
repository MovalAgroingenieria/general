# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class GeneralEntityCensusAdditional(models.Model):
    _name = "general.entity.census.additional"
    _description = "Additional Census Movements"
    _order = "create_date desc"

    census_line_id = fields.Many2one(
        comodel_name="general.entity.census.line",
        required=True,
        ondelete="cascade",
        index=True,
    )
    census_id = fields.Many2one(
        comodel_name="general.entity.census",
        related="census_line_id.census_id",
        store=True,
        index=True,
    )
    census_state = fields.Selection(
        string="Census Status",
        related="census_id.state",
        store=True,
    )
    census_line_state = fields.Selection(
        string="Line Status",
        related="census_line_id.state",
        store=True,
    )
    member_partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="census_line_id.member_partner_id",
        store=True,
    )
    primary_partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="census_line_id.primary_partner_id",
        store=True,
        index=True,
    )
    period_date = fields.Date(
        related="census_line_id.period_date",
        store=True,
        index=True,
    )
    qty = fields.Float(
        digits="Product Unit of Measure",
        compute="_compute_qty",
        inverse="_inverse_qty",
        store=True,
        help="Quantity adjustment. When shares is set, calculated as "
        "shares × census distribution amount per period. "
        "Can be set directly (shares will be reset to 0).",
    )
    shares = fields.Float(
        digits="Product Unit of Measure",
        default=0.0,
        help="Positive or negative shares adjustment (distribution basis). "
        "When set, qty is computed automatically.",
    )
    note = fields.Text()
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="census_id.company_id",
        store=True,
    )

    @api.depends("shares", "census_line_id.census_id.distribution_amount_period")
    def _compute_qty(self):
        """Calculate qty from shares × census distribution amount per period.

        If shares is 0 the field keeps its current stored value, allowing
        direct entry via the inverse.
        """
        for record in self:
            aforo = record.census_line_id.census_id.distribution_amount_period
            if record.shares and aforo:
                record.qty = record.shares * aforo
            elif not record.shares:
                record.qty = record.qty or 0.0
            else:
                record.qty = 0.0

    def _inverse_qty(self):
        """When qty is set directly (different from shares-derived value),
        reset shares to 0 to indicate direct-entry mode."""
        for record in self:
            if float_is_zero(record.qty, precision_digits=4):
                continue
            if not record.shares:
                continue
            aforo = record.census_line_id.census_id.distribution_amount_period
            if not aforo:
                continue
            calculated = record.shares * aforo
            if float_compare(record.qty, calculated, precision_digits=4) != 0:
                record.shares = 0.0

    def _check_can_modify(self):
        """Check that additional movements can be modified."""
        for record in self:
            if record.census_id.state == "locked":
                raise UserError(
                    self.env._(
                        "Cannot modify additional movements when census is locked. "
                        "Unlock the census first."
                    )
                )
            if record.census_line_id.state == "validated":
                raise UserError(
                    self.env._(
                        "Cannot modify additional movements when census line is "
                        "validated. Unvalidate the line first."
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        """Prevent creation of additional movements in locked/validated states."""
        records = super().create(vals_list)
        records._check_can_modify()  # pylint: disable=protected-access
        return records

    def write(self, vals):
        """Prevent modification of additional movements in locked/validated states."""
        if self.env.context.get("skip_census_protection"):
            return super().write(vals)
        self._check_can_modify()  # pylint: disable=protected-access
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_check_can_modify(self):
        """Prevent deletion of additional movements in locked/validated states."""
        self._check_can_modify()  # pylint: disable=protected-access
