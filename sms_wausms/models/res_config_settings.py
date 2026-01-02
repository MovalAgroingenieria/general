# Copyright 2025-2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sms_provider = fields.Selection(
        related="company_id.sms_provider",
        readonly=False,
    )

    sms_wausms_service_url = fields.Char(
        related="company_id.sms_wausms_service_url",
        readonly=False,
    )
    sms_wausms_api_user = fields.Char(
        related="company_id.sms_wausms_api_user",
        readonly=False,
    )
    sms_wausms_api_passwd = fields.Char(
        related="company_id.sms_wausms_api_passwd",
        readonly=False,
    )
    sms_wausms_sender = fields.Char(
        related="company_id.sms_wausms_sender",
        readonly=False,
        help="Up to 15 digits for numeric sender, or up to 11 alphanumeric characters.",
    )
