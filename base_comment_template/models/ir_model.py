# Copyright 2020 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class IrModel(models.Model):
    _inherit = "ir.model"

    is_comment_template = fields.Boolean(
        string="Comment Template",
        default=False,
        help="Indicates whether this model supports comment templates in reports.",
    )

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @api.model
    def get_comment_template_models(self):
        """Return technical names of models that support comment templates.

        This helper can be reused from other code instead of relying on
        ORM internals or hard-coded model names.
        """
        return self.search([("is_comment_template", "=", True)]).mapped("model")
