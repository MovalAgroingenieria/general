# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    census_ids = fields.One2many(
        comodel_name="general.entity.census",
        inverse_name="primary_partner_id",
    )
    census_count = fields.Integer(
        compute="_compute_census_count",
    )
    primary_census_line_ids = fields.One2many(
        comodel_name="general.entity.census.line",
        inverse_name="primary_partner_id",
    )
    primary_census_line_count = fields.Integer(
        compute="_compute_primary_census_line_count",
    )
    census_line_ids = fields.One2many(
        comodel_name="general.entity.census.line",
        inverse_name="member_partner_id",
    )
    census_line_count = fields.Integer(
        compute="_compute_census_line_count",
    )

    @api.depends("census_ids")
    def _compute_census_count(self):
        for partner in self:
            partner.census_count = len(partner.census_ids)

    @api.depends("primary_census_line_ids")
    def _compute_primary_census_line_count(self):
        for partner in self:
            partner.primary_census_line_count = len(partner.primary_census_line_ids)

    @api.depends("census_line_ids")
    def _compute_census_line_count(self):
        for partner in self:
            partner.census_line_count = len(partner.census_line_ids)

    def action_view_censuses(self):
        """Open censuses view of the primary entity."""
        self.ensure_one()
        action = self.env.ref(
            "base_general_entity_period_census.action_general_entity_census"
        ).read()[0]
        action["domain"] = [("primary_partner_id", "=", self.id)]
        action["context"] = {
            "default_primary_partner_id": self.id,
        }
        return action

    def action_view_primary_census_lines(self):
        """Open census lines view for the primary entity."""
        self.ensure_one()
        action = self.env.ref(
            "base_general_entity_period_census.action_general_entity_census_line"
        ).read()[0]
        action["domain"] = [("primary_partner_id", "=", self.id)]
        action["context"] = {
            "default_primary_partner_id": self.id,
            "hide_primary_partner": True,
            "search_default_group_by_quarter": 1,
            "search_default_group_by_month": 1,
        }
        return action

    def action_view_census_lines(self):
        """Open census lines view for the secondary member."""
        self.ensure_one()
        action = self.env.ref(
            "base_general_entity_period_census.action_general_entity_census_line"
        ).read()[0]
        action["domain"] = [("member_partner_id", "=", self.id)]
        action["context"] = {
            "default_member_partner_id": self.id,
            "create": False,
            "delete": False,
            "search_default_group_by_quarter": 1,
            "search_default_group_by_month": 1,
        }
        return action
