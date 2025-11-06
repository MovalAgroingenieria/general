# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = "crm.lead"

    # Related boolean field to indicate if the current stage is marked as "new"
    stage_new = fields.Boolean(
        string="Stage: New",
        related="stage_id.is_new",
        readonly=True,
        store=False,
    )

    @api.depends("user_id", "type")
    def _compute_team_id(self):
        """Override default behavior:
        When changing the user, assign a team_id if necessary,
        but remove the type-based restriction (lead/opportunity).
        """
        for lead in self:
            user = lead.user_id
            if not user:
                continue

            # If the lead already has a team and the user is either
            # the team leader or a member, skip reassignment
            if lead.team_id and (
                user == lead.team_id.user_id or user in lead.team_id.member_ids
            ):
                continue

            # No type restriction for team assignment
            # pylint: disable=protected-access
            team = self.env["crm.team"]._get_default_team_id(user_id=user.id, domain=[])
            lead.team_id = team.id if team else False

    def write(self, vals):
        vals = vals or {}
        # If the stage is being changed, ensure the lead has
        # both Category (tag) and Origin (utm.source)
        if "stage_id" in vals:
            for lead in self:
                if not lead.tag_ids and not lead.source_id:
                    raise UserError(
                        self.env._(
                            "You must indicate Category and Origin for the lead "
                            "before changing the stage."
                        )
                    )
        return super().write(vals)
