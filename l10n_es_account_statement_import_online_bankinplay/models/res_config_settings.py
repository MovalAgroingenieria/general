# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    bankinplay_integration = fields.Boolean(
        string="Integration with BankInPlat Services",
        config_parameter="l10n_es_account_statement_import_online_bankinplay"
        ".bankinplay_integration",
    )

    bankinplay_integration_url_for_callback = fields.Char(
        string="Bankinplay Callback URL",
        config_parameter="l10n_es_account_statement_import_online_bankinplay"
        ".bankinplay_integration_url_for_callback",
    )

    bankinplay_integration_api_key = fields.Char(
        string="Bankinplay API Key",
        config_parameter="l10n_es_account_statement_import_online_bankinplay"
        ".bankinplay_integration_api_key",
    )

    bankinplay_integration_api_secret = fields.Char(
        string="Bankinplay API Secret",
        config_parameter="l10n_es_account_statement_import_online_bankinplay"
        ".bankinplay_integration_api_secret",
    )

    def register_bankinplay_callbacks(self):
        self.ensure_one()
        bankinplay_interface = self.env["bankinplay.interface"]
        bankinplay_url = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "l10n_es_account_statement_import_online_bankinplay"
                ".bankinplay_integration_url_for_callback"
            )
        )
        bankinplay_api_key = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "l10n_es_account_statement_import_online_bankinplay"
                ".bankinplay_integration_api_key"
            )
        )
        bankinplay_api_secret = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "l10n_es_account_statement_import_online_bankinplay"
                ".bankinplay_integration_api_secret"
            )
        )
        access_data = bankinplay_interface._login(
            bankinplay_api_key, bankinplay_api_secret
        )
        result = bankinplay_interface._register_bankinplay_callbacks(
            access_data, bankinplay_url
        )
        if result and "data" in result and "id" in result["data"]:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Callbacks Registered",
                    "message": "BankInPlay calbacks registered correctly.",
                    "sticky": False,
                    "type": "success",
                },
            }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error",
                    "message": "BankInPlay calbacks not registered",
                    "sticky": False,
                    "type": "danger",
                },
            }
