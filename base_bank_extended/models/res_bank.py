# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    # Override the core SQL constraint using the SAME name
    # to effectively disable uniqueness on acc_number.
    # Odoo will drop the original UNIQUE constraint during module update
    # and create this harmless CHECK instead.
    _sql_constraints = [
        (
            "unique_number",
            "CHECK (1=1)",
            "Account Number must be unique (disabled by customization).",
        ),
    ]
