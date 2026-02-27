# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import calendar

from dateutil.relativedelta import relativedelta

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError


class GeneralEntityCensus(models.Model):
    _name = "general.entity.census"
    _description = "General Entity Period Census"
    _order = "period_date desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(compute="_compute_name", store=True)
    primary_partner_id = fields.Many2one(
        comodel_name="res.partner",
        required=True,
        index=True,
        ondelete="cascade",
        domain=[("is_primary_entity", "=", True)],
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        index=True,
    )
    period_date = fields.Date(
        required=True,
        index=True,
        help="Use the first day of the month (e.g., 2026-02-01 for February 2026)",
        tracking=True,
    )
    period_type = fields.Selection(
        selection=[
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("monthly", "Monthly"),
            ("quarterly", "Quarterly"),
            ("annual", "Annual"),
            ("custom", "Custom"),
        ],
        required=True,
        default="monthly",
        tracking=True,
    )
    period_start_date = fields.Date(
        help="Start date for custom periods",
        tracking=True,
    )
    period_end_date = fields.Date(
        help="End date for custom periods",
        tracking=True,
    )
    period_days = fields.Integer(
        compute="_compute_period_days",
        store=True,
        help="Number of days in the period",
    )
    period_name = fields.Char(compute="_compute_period_name", store=True)
    state = fields.Selection(
        selection=[("draft", "Draft"), ("locked", "Locked")],
        default="draft",
        required=True,
        tracking=True,
    )
    line_ids = fields.One2many(
        comodel_name="general.entity.census.line",
        inverse_name="census_id",
    )
    line_count = fields.Integer(
        string="Lines",
        compute="_compute_line_count",
        default=0,
    )
    total_shares = fields.Float(
        compute="_compute_totals",
        store=True,
        digits="Product Unit of Measure",
        default=0.0,
    )
    note = fields.Text()

    # Distribution fields
    distribution_product_id = fields.Many2one(
        comodel_name="product.product",
        help="Product to distribute based on shares",
    )
    distribution_amount_day = fields.Float(
        string="Amount per Action/Day",
        digits="Census Distribution",
        default=0.0,
        help="Amount to distribute per action per day",
    )
    distribution_amount_period = fields.Float(
        string="Amount per Action/Period",
        digits="Census Distribution",
        compute="_compute_distribution_amount_period",
        inverse="_inverse_distribution_amount_period",
        store=True,
        help="Amount to distribute per action per period",
    )
    distribution_total = fields.Float(
        compute="_compute_distribution_total",
        store=True,
        digits="Census Distribution",
        help="Total distributed amount across all lines",
    )

    _sql_constraints = [
        (
            "unique_entity_period",
            "unique(primary_partner_id, period_date)",
            "A census for this entity already exists in this period.",
        ),
    ]

    @api.depends("primary_partner_id", "period_date")
    def _compute_name(self):
        for census in self:
            if census.primary_partner_id and census.period_date:
                census.name = "{} - {}".format(
                    census.primary_partner_id.name,
                    census.period_date.strftime("%Y-%m"),
                )
            else:
                census.name = "New Census"

    def _get_custom_period_days(self):
        """Calculate days for custom period type."""
        self.ensure_one()
        if self.period_start_date and self.period_end_date:
            delta = self.period_end_date - self.period_start_date
            return delta.days + 1  # Include both start and end
        return 0

    def _get_monthly_period_days(self, period_date):
        """Calculate days in month for given date."""
        return calendar.monthrange(period_date.year, period_date.month)[1]

    def _get_annual_period_days(self, period_date):
        """Calculate days in year (365 or 366 for leap year)."""
        return 366 if calendar.isleap(period_date.year) else 365

    @api.depends("period_date", "period_type", "period_start_date", "period_end_date")
    def _compute_period_days(self):
        """Calculate number of days in the period based on type."""
        for census in self:
            if census.period_type == "custom":
                census.period_days = (
                    # pylint: disable=protected-access
                    census._get_custom_period_days()
                )
                continue

            if not census.period_date:
                census.period_days = 0
                continue

            period_date = census.period_date
            if census.period_type == "daily":
                census.period_days = 1
            elif census.period_type == "weekly":
                census.period_days = 7
            elif census.period_type == "monthly":
                # pylint: disable=protected-access
                census.period_days = census._get_monthly_period_days(period_date)
            elif census.period_type == "quarterly":
                census.period_days = 90
            elif census.period_type == "annual":
                # pylint: disable=protected-access
                census.period_days = census._get_annual_period_days(period_date)
            else:
                census.period_days = 0

    @api.depends("period_date")
    def _compute_period_name(self):
        for census in self:
            if census.period_date:
                census.period_name = census.period_date.strftime("%Y-%m")
            else:
                census.period_name = ""

    @api.depends("line_ids")
    def _compute_line_count(self):
        for census in self:
            census.line_count = len(census.line_ids)

    @api.depends("line_ids.shares")
    def _compute_totals(self):
        for census in self:
            census.total_shares = sum(census.line_ids.mapped("shares"))

    @api.depends("distribution_amount_day", "period_days")
    def _compute_distribution_amount_period(self):
        """Calculate amount per period based on amount per day and period days."""
        for census in self:
            if census.period_days:
                census.distribution_amount_period = (
                    census.distribution_amount_day * census.period_days
                )
            else:
                census.distribution_amount_period = 0.0

    def _inverse_distribution_amount_period(self):
        """Calculate amount per day based on amount per period."""
        for census in self:
            if census.period_days:
                census.distribution_amount_day = (
                    census.distribution_amount_period / census.period_days
                )
            else:
                census.distribution_amount_day = 0.0

    @api.depends("line_ids.distributed_qty")
    def _compute_distribution_total(self):
        """Calculate total distributed amount."""
        for census in self:
            census.distribution_total = sum(census.line_ids.mapped("distributed_qty"))

    def action_open_form(self):
        """Open the form view of this census."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "general.entity.census",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_lock(self):
        """Lock census to prevent modifications."""
        for census in self:
            if census.state != "draft":
                raise UserError(self.env._("Only draft censuses can be locked."))
            census.state = "locked"

    def action_unlock(self):
        """Unlock census to allow modifications."""
        for census in self:
            if census.state != "locked":
                raise UserError(self.env._("Only locked censuses can be unlocked."))
            census.state = "draft"

    def _get_period_relativedelta(self):
        """Return the relativedelta for advancing one period based on type."""
        self.ensure_one()
        period_deltas = {
            "daily": relativedelta(days=1),
            "weekly": relativedelta(weeks=1),
            "monthly": relativedelta(months=1),
            "quarterly": relativedelta(months=3),
            "annual": relativedelta(years=1),
        }
        if self.period_type in period_deltas:
            return period_deltas[self.period_type]
        if (
            self.period_type == "custom"
            and self.period_start_date
            and self.period_end_date
        ):
            delta = self.period_end_date - self.period_start_date
            return relativedelta(days=delta.days + 1)
        return None

    def _get_next_period_date(self):
        """Calculate the next period date based on period type."""
        self.ensure_one()
        if not self.period_date:
            return False
        # pylint: disable=protected-access
        period_delta = self._get_period_relativedelta()
        if not period_delta:
            return False
        return self.period_date + period_delta

    def action_copy_to_next_period(self):
        """Copy this census to the next period, creating a new census."""
        self.ensure_one()

        next_date = self._get_next_period_date()  # pylint: disable=protected-access
        if not next_date:
            raise UserError(self.env._("Cannot calculate next period date."))

        # Check if census already exists for next period
        existing = self.search(
            [
                ("primary_partner_id", "=", self.primary_partner_id.id),
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

        # Prepare lines to copy
        lines_to_create = []
        for line in self.line_ids:
            # Copy additional movements
            additional_movements = []
            for additional in line.additional_ids:
                additional_movements.append(
                    Command.create(
                        {
                            "qty": additional.qty,
                            "note": additional.note,
                        }
                    )
                )

            lines_to_create.append(
                Command.create(
                    {
                        "member_partner_id": line.member_partner_id.id,
                        "shares": line.shares,
                        "note": line.note,
                        "previous_line_id": line.id,
                        "additional_ids": additional_movements,
                    }
                )
            )

        # Create new census with custom period dates if applicable
        new_census_vals = {
            "primary_partner_id": self.primary_partner_id.id,
            "period_date": next_date,
            "period_type": self.period_type,
            "distribution_product_id": (
                self.distribution_product_id.id
                if self.distribution_product_id
                else False
            ),
            "distribution_amount_day": self.distribution_amount_day,
            "line_ids": lines_to_create,
        }

        # Handle custom period dates
        if self.period_type == "custom" and self.period_start_date:
            delta = self.period_end_date - self.period_start_date
            new_census_vals["period_start_date"] = (
                self.period_start_date + relativedelta(days=delta.days + 1)
            )
            new_census_vals["period_end_date"] = self.period_end_date + relativedelta(
                days=delta.days + 1
            )

        new_census = self.create(new_census_vals)

        return {
            "type": "ir.actions.act_window",
            "res_model": "general.entity.census",
            "res_id": new_census.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.constrains("period_date")
    def _check_period_date(self):
        """Validate that the date is the first day of the month."""
        for census in self:
            if census.period_date and census.period_date.day != 1:
                raise ValidationError(
                    self.env._(
                        "The period date must be the first day of the month "
                        "(e.g., 2026-02-01 for February 2026)."
                    )
                )
