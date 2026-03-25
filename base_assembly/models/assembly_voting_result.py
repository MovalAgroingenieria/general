# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AssemblyVotingResult(models.Model):
    _name = "assembly.voting.result"
    _description = "Voting result by option"

    _sql_constraints = [
        (
            "voting_result_option_uniq",
            "UNIQUE(voting_id, vote_option)",
            "Each vote option may appear only once per voting.",
        ),
    ]

    voting_id = fields.Many2one(
        "assembly.voting",
        string="Voting",
        required=True,
        ondelete="cascade",
        index=True,
    )
    vote_option = fields.Selection(
        [
            ("yes", "Yes"),
            ("no", "No"),
            ("abstention", "Abstention"),
            ("blank", "Blank"),
            ("not_cast", "Not cast"),
        ],
        string="Option",
        required=True,
    )
    total_votes = fields.Float(string="Total votes")
    result_percentage = fields.Float(string="Percentage")

    @api.model_create_multi
    def create(self, vals_list):
        vids = {v.get("voting_id") for v in vals_list if v.get("voting_id")}
        if vids:
            self.env["assembly.voting"].browse(list(vids)).exists().mapped(
                "assembly_id"
            )._assembly_ensure_not_closed_for_related_changes()
        return super().create(vals_list)

    def write(self, vals):
        self.mapped(
            "voting_id.assembly_id"
        )._assembly_ensure_not_closed_for_related_changes()
        return super().write(vals)

    def unlink(self):
        self.mapped(
            "voting_id.assembly_id"
        )._assembly_ensure_not_closed_for_related_changes()
        return super().unlink()
