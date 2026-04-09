# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models
from odoo.exceptions import UserError


class CensusGenerateLinesWizard(models.TransientModel):
    _name = "census.generate.lines.wizard"
    _description = "Generate Census Lines from Active Members"

    census_id = fields.Many2one(
        comodel_name="general.entity.census",
        required=True,
        readonly=True,
    )
    primary_partner_id = fields.Many2one(
        related="census_id.primary_partner_id",
        readonly=True,
    )
    member_ids = fields.Many2many(
        comodel_name="general.entity.member",
        string="Members to Include",
        help="Select which active members to add as census lines. "
        "Members already in the census will be skipped.",
    )
    skip_existing = fields.Boolean(
        default=True,
        help="If checked, members already present in the census "
        "will be silently skipped. Otherwise, an error is raised.",
    )

    def default_get(self, fields_list):
        """Pre-populate members from active entity members."""
        res = super().default_get(fields_list)
        census_id = self.env.context.get("active_id")
        if census_id:
            census = self.env["general.entity.census"].browse(census_id)
            res["census_id"] = census.id
            # Get all active members of the primary entity
            members = self.env["general.entity.member"].search(
                [
                    ("primary_partner_id", "=", census.primary_partner_id.id),
                    ("active", "=", True),
                ]
            )
            res["member_ids"] = [fields.Command.set(members.ids)]
        return res

    def action_generate(self):
        """Create census lines from selected members."""
        self.ensure_one()
        census = self.census_id

        if census.state == "locked":
            raise UserError(
                self.env._("Cannot add lines to a locked census. Unlock it first.")
            )

        existing_partners = census.line_ids.mapped("member_partner_id")
        lines_created = 0

        for member in self.member_ids:
            if member.member_partner_id in existing_partners:
                if not self.skip_existing:
                    raise UserError(
                        self.env._(
                            "Member %(member)s is already in the census.",
                            member=member.member_partner_id.name,
                        )
                    )
                continue

            self.env["general.entity.census.line"].create(
                {
                    "census_id": census.id,
                    "member_partner_id": member.member_partner_id.id,
                }
            )
            lines_created += 1

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("Lines Generated"),
                "message": self.env._(
                    "%(count)d census lines created.",
                    count=lines_created,
                ),
                "sticky": False,
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
