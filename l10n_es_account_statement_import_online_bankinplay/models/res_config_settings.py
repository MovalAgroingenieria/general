# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
# pylint: disable=translation-not-lazy
# pylint: disable=protected-access
# pylint: disable=broad-exception-caught

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Master toggle (purely informational—your code won’t auto-disable without it)
    bankinplay_integration = fields.Boolean(
        string="Integration with BankInPlay Services",
        help="Enable the integration with BankInPlay for statement callbacks.",
        config_parameter=(
            "l10n_es_account_statement_import_online_bankinplay.bankinplay_integration"
        ),
    )

    # Public URL where BankInPlay will POST the webhook (your Odoo base URL)
    bankinplay_integration_url_for_callback = fields.Char(
        string="BankInPlay Callback URL",
        help="Public base URL of this Odoo instance used as the webhook target, "
        "e.g., https://odoo.example.com",
        config_parameter=(
            "l10n_es_account_statement_import_online_bankinplay."
            "bankinplay_integration_url_for_callback"
        ),
    )

    # API credentials used to register callbacks / login to BankInPlay
    bankinplay_integration_api_key = fields.Char(
        string="BankInPlay API Key",
        help="Username/key provided by BankInPlay.",
        config_parameter=(
            "l10n_es_account_statement_import_online_bankinplay."
            "bankinplay_integration_api_key"
        ),
    )

    bankinplay_integration_api_secret = fields.Char(
        string="BankInPlay API Secret",
        help="Password/secret provided by BankInPlay.",
        config_parameter=(
            "l10n_es_account_statement_import_online_bankinplay."
            "bankinplay_integration_api_secret"
        ),
    )

    def register_bankinplay_callbacks(self):
        """Register the /webhook/bankinplay_callback endpoint at BankInPlay.

        Reads config parameters, logs in against BankInPlay, and attempts to
        register the 'lectura_cierre' callback. Shows a UI notification with the result.
        """
        self.ensure_one()
        bankinplay_interface = self.env["bankinplay.interface"]

        icp = self.env["ir.config_parameter"].sudo()
        bankinplay_url = icp.get_param(
            "l10n_es_account_statement_import_online_bankinplay."
            "bankinplay_integration_url_for_callback"
        )
        bankinplay_api_key = icp.get_param(
            "l10n_es_account_statement_import_online_bankinplay."
            "bankinplay_integration_api_key"
        )
        bankinplay_api_secret = icp.get_param(
            "l10n_es_account_statement_import_online_bankinplay."
            "bankinplay_integration_api_secret"
        )

        # Basic validation before attempting the call
        missing = []
        if not bankinplay_url:
            missing.append(self.env._("Callback URL"))
        if not bankinplay_api_key:
            missing.append(self.env._("API Key"))
        if not bankinplay_api_secret:
            missing.append(self.env._("API Secret"))
        if missing:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": self.env._("Missing configuration"),
                    "message": self.env._("Please set: %s") % ", ".join(missing),
                    "sticky": False,
                    "type": "warning",
                },
            }

        # Normalize URL (avoid double slashes when the model builds the hook path)
        bankinplay_url = bankinplay_url.rstrip("/")

        try:
            access_data = bankinplay_interface._login(
                bankinplay_api_key, bankinplay_api_secret
            )
            result = bankinplay_interface._register_bankinplay_callbacks(
                access_data, bankinplay_url
            )
        except Exception as e:
            # Any network/remote error ends here with a clear message
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": self.env._("Error"),
                    "message": self.env._("Could not register callbacks: %s") % e,
                    "sticky": False,
                    "type": "danger",
                },
            }

        # Expecting {'data': {'id': ...}, ...} on success
        if isinstance(result, dict) and result.get("data", {}).get("id"):
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": self.env._("Callbacks registered"),
                    "message": self.env._(
                        "BankInPlay callbacks registered successfully."
                    ),
                    "sticky": False,
                    "type": "success",
                },
            }

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("Error"),
                "message": self.env._("BankInPlay callbacks were not registered."),
                "sticky": False,
                "type": "danger",
            },
        }
