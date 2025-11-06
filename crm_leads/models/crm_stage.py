# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class Stage(models.Model):
    _inherit = "crm.stage"

    # Flag to mark a stage as “new” for downstream logic
    # (e.g., computed fields on crm.lead)
    is_new = fields.Boolean(
        default=False,
        help="Indicates if this stage represents a 'new' "
        "state for leads/opportunities.",
        index=True,  # faster searches/filters on large DBs
    )
