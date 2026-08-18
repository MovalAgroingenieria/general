# 2026 Moval Agroingenieria
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_sii_identifier(self):
        self.ensure_one()
        gen_type = self._get_sii_gen_type()
        partner = self._aeat_get_partner()
        (
            country_code,
            identifier_type,
            identifier,
        ) = partner._parse_aeat_vat_info()
        vat_country_code = (
            partner._map_aeat_country_iso_code(partner.country_id) or country_code
        )
        if identifier == "/":
            identifier = False
        if identifier:
            identifier = "".join(e for e in identifier if e.isalnum()).upper()
        else:
            identifier = "NO_DISPONIBLE"
            identifier_type = "06"
        if gen_type == 1:
            if "1117" in (self.aeat_send_error or ""):
                return {
                    "IDOtro": {
                        "CodigoPais": country_code,
                        "IDType": "07",
                        "ID": identifier,
                    }
                }
            else:
                if identifier_type == "":
                    return {"NIF": identifier}
                return {
                    "IDOtro": {
                        "CodigoPais": country_code,
                        "IDType": identifier_type,
                        "ID": vat_country_code + identifier
                        if self._aeat_get_partner()._map_aeat_country_code(
                            vat_country_code
                        )
                        in self._aeat_get_partner()._get_aeat_europe_codes()
                        else identifier,
                    },
                }
        elif gen_type == 2:
            return {"IDOtro": {"IDType": "02", "ID": vat_country_code + identifier}}
        elif gen_type == 3 and identifier_type:

            if identifier_type == "02":
                identifier_type = "06"
            return {
                "IDOtro": {
                    "CodigoPais": country_code,
                    "IDType": identifier_type,
                    "ID": identifier,
                },
            }
        elif gen_type == 3:
            return {"NIF": identifier}
        return {"NIF": identifier}

    def _post(self, *args, **kwargs):
        if self.sii_enabled and self.aeat_state in ("sent", "sent_w_errors", "sent_modified"):
            # pylint: disable=W0642
            self = self.with_context(_sii_only_analytic_change=True)
        return super()._post(*args, **kwargs)

    def _sii_invoice_dict_not_modified(self):
        self.ensure_one()
        if self.env.context.get("_sii_only_analytic_change"):
            return True
        to_send = self._get_aeat_invoice_dict()
        content_sent = json.loads(self.aeat_content_sent)
        return to_send == content_sent
