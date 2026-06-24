# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import calendar

from dateutil.relativedelta import relativedelta
from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError


class GeneralEntityCensus(models.Model):
    _name = "general.entity.census"
    _description = "General Entity Period Census"
    _order = "period_date asc, id desc"
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
    active = fields.Boolean(default=True)
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

    @api.model
    def search_panel_select_range(self, field_name, **kwargs):
        """Format entity labels and ordering in searchpanel sidebar."""
        result = super().search_panel_select_range(field_name, **kwargs)
        return self.env["res.partner"].format_entity_searchpanel_result(
            field_name,
            result,
        )

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

    def _prepare_copy_line_vals(self, line, copy_additional=True):
        """Build line values for any census copy flow in base module."""
        self.ensure_one()
        vals = {
            "member_partner_id": line.member_partner_id.id,
            "shares": line.shares,
            "note": line.note,
            "previous_line_id": line.id,
        }
        if copy_additional and line.additional_ids:
            vals["additional_ids"] = [
                Command.create(
                    {
                        "qty": additional.qty,
                        "note": additional.note,
                    }
                )
                for additional in line.additional_ids
            ]
        return vals

    def _prepare_copy_census_vals(
        self,
        target_period_date,
        lines=None,
        copy_additional=True,
    ):
        """Build census create values for any copy flow in base module."""
        self.ensure_one()
        lines_to_copy = lines if lines is not None else self.line_ids
        line_cmds = [
            Command.create(
                self._prepare_copy_line_vals(
                    line,
                    copy_additional=copy_additional,
                )
            )
            for line in lines_to_copy
        ]
        vals = {
            "primary_partner_id": self.primary_partner_id.id,
            "period_date": target_period_date,
            "period_type": self.period_type,
            "distribution_product_id": (
                self.distribution_product_id.id
                if self.distribution_product_id
                else False
            ),
            "distribution_amount_day": self.distribution_amount_day,
            "line_ids": line_cmds,
        }
        return vals

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

        new_census_vals = self._prepare_copy_census_vals(next_date)

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

    @api.constrains("period_type", "period_start_date", "period_end_date")
    def _check_custom_period_dates(self):
        """Validate custom period dates."""
        for census in self:
            if census.period_type != "custom":
                continue
            if not census.period_start_date or not census.period_end_date:
                raise ValidationError(
                    self.env._("Custom periods require both start and end dates.")
                )
            if census.period_end_date < census.period_start_date:
                raise ValidationError(
                    self.env._(
                        "The end date (%(end)s) must be equal to or "
                        "later than the start date (%(start)s).",
                        end=census.period_end_date,
                        start=census.period_start_date,
                    )
                )

    def action_validate_all_lines(self):
        """Validate all draft lines in this census."""
        for census in self:
            if census.state == "locked":
                raise UserError(
                    self.env._(
                        "Cannot validate lines in a locked census. Unlock it first."
                    )
                )
            draft_lines = census.line_ids.filtered(lambda ln: ln.state == "draft")
            if draft_lines:
                draft_lines.write({"state": "validated"})

    def action_unvalidate_all_lines(self):
        """Unvalidate all validated lines in this census."""
        for census in self:
            if census.state == "locked":
                raise UserError(
                    self.env._(
                        "Cannot unvalidate lines in a locked census. "
                        "Unlock it first."
                    )
                )
            validated_lines = census.line_ids.filtered(
                lambda ln: ln.state == "validated"
            )
            if validated_lines:
                validated_lines.write({"state": "draft"})
