# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Allow ``mail.compose.message`` to open with a pre-filled body from assembly AF render.

Standard :meth:`~odoo.addons.mail.wizard.mail_compose_message.MailComposer._compute_body`
clears ``body`` when no template is selected; assembly actions pass rendered HTML via
``default_body`` and context flag ``assembly_use_rendered_mail_body``.
"""

from odoo import api, models


class MailComposeMessage(models.TransientModel):  # pylint: disable=no-wizard-in-models
    _inherit = "mail.compose.message"

    @api.depends(
        "composition_mode",
        "model",
        "res_domain",
        "res_ids",
        "template_id",
    )
    def _compute_body(self):
        if self.env.context.get("assembly_use_rendered_mail_body"):
            with_template = self.filtered("template_id")
            if with_template:
                super(MailComposeMessage, with_template)._compute_body()
            return
        super()._compute_body()
