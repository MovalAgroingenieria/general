# Copyright 2025-2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0.html).
# pylint: disable=translation-not-lazy

from odoo import fields, models
from odoo.exceptions import UserError

from ..tools.sms_api import SmsApiWauSms


class ResCompany(models.Model):
    _inherit = "res.company"

    sms_provider = fields.Selection(
        selection=[
            ("iap", "Send via Odoo"),
            ("wausms", "Send via WauSMS"),
        ],
        default="iap",
        required=True,
    )

    sms_wausms_service_url = fields.Char(
        groups="base.group_system",
        help="WauSMS REST endpoint. The official endpoint is used by default "
        "(POST /Api/rest/message).",
    )
    sms_wausms_api_user = fields.Char(
        groups="base.group_system",
    )
    sms_wausms_api_passwd = fields.Char(
        groups="base.group_system",
    )
    sms_wausms_sender = fields.Char(
        groups="base.group_system",
        help="Up to 15 digits for numeric sender, or up to 11 alphanumeric "
        "characters.",
    )

    # -------------------------------------------------------------------------
    # SMS framework hooks
    # -------------------------------------------------------------------------

    def _get_sms_api_class(self):
        """Return the SMS API backend class for this company."""
        self.ensure_one()
        if self.sms_provider == "wausms":
            # Use relative import

            return SmsApiWauSms
        return super()._get_sms_api_class()

    # -------------------------------------------------------------------------
    # WauSMS helpers
    # -------------------------------------------------------------------------

    def _assert_wausms_config(self):
        """Validate WauSMS configuration before sending."""
        self.ensure_one()

        missing = self._get_wausms_missing_config_fields()
        if missing:
            raise UserError(
                self.env._(
                    "WauSMS is selected as SMS provider, but the configuration is "
                    "incomplete: %(missing)s"
                )
                % {"missing": ", ".join(missing)}
            )

        self._check_wausms_sender()

    def _get_wausms_missing_config_fields(self):
        """Return a list of missing configuration field labels."""
        self.ensure_one()
        missing = []
        if not self.sms_wausms_service_url:
            missing.append(self.env._("Service URL"))
        if not self.sms_wausms_api_user:
            missing.append(self.env._("API User"))
        if not self.sms_wausms_api_passwd:
            missing.append(self.env._("API Password"))
        if not self.sms_wausms_sender:
            missing.append(self.env._("Sender"))
        return missing

    def _check_wausms_sender(self):
        """Validate WauSMS sender constraints.

        WauSMS constraints (spec):
          - numeric sender: max 15 digits
          - alphanumeric sender: max 11 characters
        """
        self.ensure_one()
        sender = (self.sms_wausms_sender or "").strip()
        if not sender:
            return

        if sender.isdigit():
            if len(sender) > 15:
                raise UserError(
                    self.env._("Sender is limited to 15 digits when numeric.")
                )
        else:
            if len(sender) > 11:
                raise UserError(
                    self.env._("Sender is limited to 11 characters when alphanumeric.")
                )
