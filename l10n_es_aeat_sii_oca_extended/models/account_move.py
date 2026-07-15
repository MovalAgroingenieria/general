# 2026 Moval Agroingenieria
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_sii_identifier(self):
        """Get the SII structure for a partner identifier depending on the
        conditions of the invoice.
        """
        self.ensure_one()
        gen_type = self._get_sii_gen_type()
        partner = self._aeat_get_partner()
        (
            country_code,
            identifier_type,
            identifier,
        ) = partner._parse_aeat_vat_info()
        # Take into account some vats construction like Greece
        vat_country_code = (
            partner._map_aeat_country_iso_code(partner.country_id) or country_code
        )
        if identifier == "/":
            identifier = False
        # Limpiar alfanum
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
            # Si usamos identificador tipo 02 en exportaciones, el envío falla con:
            #   {'CodigoErrorRegistro': 1104,
            #    'DescripcionErrorRegistro': 'Valor del campo ID incorrecto'}
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
