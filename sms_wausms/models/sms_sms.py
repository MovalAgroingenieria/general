# Copyright 2025-2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0.html).
# pylint: disable=protected-access
# pylint: disable=missing-return

from odoo import fields, models


class SmsSms(models.Model):
    _inherit = "sms.sms"

    wausms_response = fields.Text(
        string="WauSMS Response",
        readonly=True,
        copy=False,
        help="Raw response returned by WauSMS for debugging purposes.",
    )

    def _handle_call_result_hook(self, results):
        """Store WauSMS raw response on sms.sms when still available."""
        wausms_sms = self.filtered(
            lambda sms: sms._get_sms_company().sms_provider == "wausms"
        )
        if wausms_sms and results:
            sms_by_uuid = {sms.uuid: sms for sms in wausms_sms if sms.uuid}
            for result in results:
                sms = sms_by_uuid.get(result.get("uuid"))
                raw = result.get("wausms_response")
                if sms and raw:
                    sms.wausms_response = raw

        other_sms = self - wausms_sms
        if other_sms:
            super(SmsSms, other_sms)._handle_call_result_hook(results)

    def _split_by_api(self):
        """Split SMS by company and bind the correct company to the API instance.

        Odoo v18 instantiates the API with env.company by default. In multi-company
        scenarios, this may not match the SMS company (record_company_id).
        """
        by_company = {}
        for sms in self:
            company = sms._get_sms_company()
            by_company.setdefault(company, self.env["sms.sms"])
            by_company[company] |= sms

        for company, sms_recs in by_company.items():
            api_cls = company._get_sms_api_class()
            sms_api = api_cls(self.env)
            sms_api._set_company(company)
            yield sms_api, sms_recs
