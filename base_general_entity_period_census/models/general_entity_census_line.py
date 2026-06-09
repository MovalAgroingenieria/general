# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models
from odoo.exceptions import UserError


class GeneralEntityCensusLine(models.Model):
    _name = "general.entity.census.line"
    _description = "Period Census Line"
    _order = "period_date, primary_partner_id, entity_global_code asc"

    _sql_constraints = [
        (
            "unique_member_per_census",
            "unique(census_id, member_partner_id)",
            "A member can only appear once per census period.",
        ),
    ]

    @classmethod
    def _valid_field_parameter(cls, field, name):  # pylint: disable=arguments-differ
        """Allow 'tracking' parameter in field definitions."""
        return name == "tracking" or super()._valid_field_parameter(field, name)

    census_id = fields.Many2one(
        comodel_name="general.entity.census",
        required=True,
        index=True,
        ondelete="cascade",
    )
    census_state = fields.Selection(
        string="Census Status",
        related="census_id.state",
        readonly=True,
        store=True,
    )
    period_date = fields.Date(
        related="census_id.period_date",
        readonly=True,
        store=True,
        index=True,
        help="Period date from the census header, used for filtering and ordering",
    )
    primary_partner_id = fields.Many2one(
        related="census_id.primary_partner_id",
        readonly=True,
        store=True,
    )
    member_partner_id = fields.Many2one(
        comodel_name="res.partner",
        required=True,
        index=True,
        domain=[("is_secondary_entity", "=", True)],
    )
    entity_global_code = fields.Integer(
        related="member_partner_id.entity_global_code",
        readonly=True,
        store=True,
        help="Global code of the secondary member",
    )
    previous_line_id = fields.Many2one(
        comodel_name="general.entity.census.line",
        index=True,
        help="Reference to the line from the previous period",
    )
    state = fields.Selection(
        selection=[("draft", "Draft"), ("validated", "Validated")],
        default="draft",
        required=True,
        index=True,
        tracking=True,
        help="Draft lines can be edited, validated lines are locked",
    )
    shares = fields.Float(
        digits="Product Unit of Measure",
        default=0.0,
    )
    additional_ids = fields.One2many(
        comodel_name="general.entity.census.additional",
        inverse_name="census_line_id",
        string="Additional Movements",
    )
    has_additional_movements = fields.Boolean(
        compute="_compute_has_additional_movements",
        store=True,
        help="Indicates whether this line has any additional movement records.",
    )
    qty_additional = fields.Float(
        string="Additional Qty",
        digits="Product Unit of Measure",
        compute="_compute_qty_additional",
        store=True,
        help="Total of additional movements (positive or negative)",
    )
    shares_changed = fields.Boolean(
        compute="_compute_shares_changed",
        store=True,
        help="Indicates if shares count has changed from previous period",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        related="census_id.distribution_product_id",
        store=True,
        string="Distribution Product",
    )
    note = fields.Text()

    # Distribution fields
    base_distributed_qty = fields.Float(
        string="Base Distribution",
        digits="Census Distribution",
        compute="_compute_base_distributed_qty",
        inverse="_inverse_base_distributed_qty",
        store=True,
        help="Distribution without additional movements. "
        "If calculated from shares: shares × amount_day × days. "
        "Can be set directly (shares will be set to 0).",
    )
    distributed_qty = fields.Float(
        string="Total Distribution",
        compute="_compute_distributed_qty",
        store=True,
        digits="Census Distribution",
        help="Total distribution: base_distributed_qty + qty_additional.",
    )

    @api.depends("shares", "previous_line_id.shares")
    def _compute_shares_changed(self):
        """Check if shares count has changed from previous period."""
        for line in self:
            if line.previous_line_id:
                line.shares_changed = line.shares != line.previous_line_id.shares
            else:
                line.shares_changed = False

    @api.depends("additional_ids.qty")
    def _compute_qty_additional(self):
        """Calculate total additional quantity from movements."""
        for line in self:
            line.qty_additional = sum(line.additional_ids.mapped("qty"))

    @api.depends("additional_ids")
    def _compute_has_additional_movements(self):
        """Flag lines that have one or more additional movements."""
        for line in self:
            line.has_additional_movements = bool(line.additional_ids)

    @api.depends("shares", "census_id.distribution_amount_period")
    def _compute_base_distributed_qty(self):
        """Calculate base distribution: shares × amount_per_period."""
        for line in self:
            if line.shares and line.census_id.distribution_amount_period:
                line.base_distributed_qty = (
                    line.shares * line.census_id.distribution_amount_period
                )
            else:
                # Keep existing value if shares is 0 (might be direct entry)
                if not line.shares:
                    # Don't overwrite if base_distributed_qty was set directly
                    pass
                else:
                    line.base_distributed_qty = 0.0

    def _inverse_base_distributed_qty(self):
        """When base_distributed_qty is set directly, set shares to 0."""
        for line in self:
            # If user enters base_distributed_qty directly, set shares to 0
            # This indicates "direct entry" mode
            if line.base_distributed_qty and not line.shares:
                # Already shares=0, nothing to do
                pass
            elif line.base_distributed_qty:
                # Check if the value matches the calculated value
                calculated = 0.0
                if line.shares and line.census_id.distribution_amount_period:
                    calculated = line.shares * line.census_id.distribution_amount_period
                # If it doesn't match, user is setting directly, so set shares to 0
                if abs(line.base_distributed_qty - calculated) > 0.001:
                    line.shares = 0.0

    @api.depends("base_distributed_qty", "qty_additional")
    def _compute_distributed_qty(self):
        """Calculate total distribution: base + additional."""
        for line in self:
            line.distributed_qty = (line.base_distributed_qty or 0.0) + (
                line.qty_additional or 0.0
            )

    def action_view_additional_movements(self):
        """Open the additional movements for this census line in a modal dialog."""
        self.ensure_one()
        # Determine if modifications are allowed
        is_readonly = self.census_id.state == "locked" or self.state == "validated"
        return {
            "name": self.env._(
                "Additional Movements - %(partner)s",
                partner=self.member_partner_id.name,
            ),
            "type": "ir.actions.act_window",
            "res_model": "general.entity.census.additional",
            "view_mode": "list",
            "views": [
                (
                    self.env.ref(
                        "base_general_entity_period_census."
                        "view_general_entity_census_additional_list"
                    ).id,
                    "list",
                )
            ],
            "domain": [("census_line_id", "=", self.id)],
            "context": {
                "default_census_line_id": self.id,
                "readonly_form": is_readonly,
            },
            "target": "new",
        }

    @api.model
    def search_panel_select_range(self, field_name, **kwargs):
        """Format entity labels and ordering in searchpanel sidebar."""
        result = super().search_panel_select_range(field_name, **kwargs)
        return self.env["res.partner"].format_entity_searchpanel_result(
            field_name,
            result,
        )

    @api.onchange("member_partner_id")
    def _onchange_member_partner_default_shares(self):
        """Fill shares from the member's default_shares when selecting."""
        for line in self:
            if line.member_partner_id and line.census_id.primary_partner_id:
                member = self.env["general.entity.member"].search(
                    [
                        (
                            "primary_partner_id",
                            "=",
                            line.census_id.primary_partner_id.id,
                        ),
                        ("member_partner_id", "=", line.member_partner_id.id),
                    ],
                    limit=1,
                )
                if member and member.default_shares:
                    line.shares = member.default_shares

    @api.ondelete(at_uninstall=False)
    def _check_can_delete(self):
        """Prevent deletion if the census is locked or line is validated."""
        for line in self:
            if line.census_id.state == "locked":
                raise UserError(
                    self.env._(
                        "Cannot delete lines from a locked census. "
                        "Unlock the census first."
                    )
                )
            if line.state == "validated":
                raise UserError(
                    self.env._(
                        "Cannot delete validated census lines. "
                        "Unvalidate the line first."
                    )
                )

    def write(self, vals):
        """Control editing based on line state."""
        if self.env.context.get("skip_census_protection"):
            return super().write(vals)
        # Fields allowed when validated or census locked
        allowed_fields_always = {"note", "state"}

        for line in self:
            # If line is validated, only allow notes and state change
            if line.state == "validated":
                forbidden_fields = set(vals.keys()) - allowed_fields_always
                if forbidden_fields:
                    raise UserError(
                        self.env._(
                            "Cannot modify validated lines. "
                            "Only 'Observations' can be edited. "
                            "Unvalidate the line first."
                        )
                    )
            # If census is locked, only allow notes
            elif line.census_id.state == "locked":
                forbidden_fields = set(vals.keys()) - {"note"}
                if forbidden_fields:
                    raise UserError(
                        self.env._(
                            "Cannot modify lines from a locked census. "
                            "Only the 'Observations' field can be edited. "
                            "Unlock the census first."
                        )
                    )

        return super().write(vals)

    def action_validate(self):
        """Validate draft lines."""
        for line in self:
            if line.census_id.state == "locked":
                raise UserError(
                    self.env._(
                        "Cannot validate lines from a locked census. "
                        "Unlock the census first."
                    )
                )
        self.filtered(lambda ln: ln.state == "draft").write({"state": "validated"})

    def action_unvalidate(self):
        """Unvalidate validated lines."""
        for line in self:
            if line.census_id.state == "locked":
                raise UserError(
                    self.env._(
                        "Cannot unvalidate lines from a locked census. "
                        "Unlock the census first."
                    )
                )
        self.filtered(lambda ln: ln.state == "validated").write({"state": "draft"})

    @api.depends("census_id.name", "member_partner_id.name")
    def _compute_display_name(self):
        for record in self:
            record.display_name = "{} - {}".format(
                record.census_id.name or "",
                record.member_partner_id.name or "",
            )
