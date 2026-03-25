# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


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
