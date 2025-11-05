# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime

from odoo import models
from odoo.exceptions import UserError
from odoo.tools.misc import format_lazy


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    # ---------- Helpers ------------------------------------------------------

    def _calculate_num_of_payment(self, line, num_of_payment):
        """
        Build the 'num_of_payment' (7 digits + control digit mod 7),
        using partner VAT numeric part + padded sequence.
        """
        self.ensure_one()
        converter = self.env["payment.converter.spain"]
        vat = (line.partner_id.vat or "").strip()
        if not vat:
            # Use lazy formatting to satisfy W8301
            raise UserError(
                format_lazy(
                    self.env._("Missing VAT on partner %(partner)s"),
                    partner=line.partner_id.display_name,
                )
            )
        id_code = converter.digits_only(vat)
        num_str = str(num_of_payment).zfill(7)
        base_number = int((id_code or "0") + num_str)
        control_digit = base_number % 7
        return "%s%s" % (num_str, control_digit)

    def _start_68(self):
        """
        Fetch and convert the initiating party identifier/issuer to 12 chars.
        """
        self.ensure_one()
        converter = self.env["payment.converter.spain"]
        start_68 = (
            self.payment_mode_id.initiating_party_identifier
            or self.payment_mode_id.initiating_party_issuer
        )
        if not start_68:
            msg = self.env._(
                "The Transaction Initiator Identifier or Transaction Issuer "
                "have not been configured."
            )
            raise UserError(msg)
        return converter.convert(start_68, 12)

    # ---------- CSB Lines ----------------------------------------------------

    def _cabecera_ordenante_68(self):
        self.ensure_one()
        converter = self.env["payment.converter.spain"]
        today = datetime.today().strftime("%d%m%y")
        txt = "0359"
        txt += self._start_68()
        txt += " " * 12
        txt += "001"
        txt += today
        txt += " " * 9

        acc_number = (self.company_partner_bank_id.acc_number or "").replace(" ", "")
        if not acc_number:
            msg = self.env._(
                "Configuration error:\n\nNo account bank number found for "
                "ordering party: Cabecera ordenante 68"
            )
            raise UserError(msg)
        txt += converter.convert(acc_number, 24)
        txt += " " * 30
        txt += "\r\n"

        if len(txt) % 102 != 0:
            raise UserError(
                format_lazy(
                    self.env._(
                        'Configuration error:\n\nA line in "%(section)s" is not 100 '
                        "characters long:\n%(content)s"
                    ),
                    section="Cabecera ordenante 68",
                    content=txt,
                )
            )
        return txt

    def _cabecera_beneficiario_68(self, line):
        converter = self.env["payment.converter.spain"]
        txt = "0659"
        txt += self._start_68()
        vat = line.partner_id.vat or ""
        txt += converter.convert_text(vat, 12)
        return txt

    def _registro_beneficiario_68(self, line, num_of_payment):
        """
        Build the 6-detail records for one beneficiary (types 010..015).
        """
        # pylint: disable=too-many-locals, too-many-statements
        converter = self.env["payment.converter.spain"]
        num_of_payment_txt = self._calculate_num_of_payment(line, num_of_payment)
        txt = ""

        # Invoicing/default address
        partner = line.partner_id
        address = partner
        # Prefer invoice address if available
        addr_map = partner.address_get(["invoice", "default"])
        if addr_map.get("invoice"):
            address = self.env["res.partner"].browse(addr_map["invoice"])
        elif addr_map.get("default"):
            address = self.env["res.partner"].browse(addr_map["default"])
        if not address:
            raise UserError(
                format_lazy(
                    self.env._(
                        "User error:\n\nPartner %(partner)s has no invoicing or "
                        "default address."
                    ),
                    partner=partner.display_name,
                )
            )

        # --- Type 010
        text1 = self._cabecera_beneficiario_68(line)
        text1 += "010"
        text1 += converter.convert_text((partner.name or "")[:40], 40)
        text1 += " " * 29
        text1 += "\r\n"
        if len(text1) % 102 != 0:
            raise UserError(
                format_lazy(
                    self.env._(
                        'Configuration error:\n\nA line in "%(section)s" is not 100 '
                        "characters long:\n%(content)s"
                    ),
                    section="Beneficiary record, type 1",
                    content=text1,
                )
            )
        txt += text1

        # --- Type 011 (street)
        text2 = self._cabecera_beneficiario_68(line)
        text2 += "011"
        street = " ".join(
            s for s in [(address.street or ""), (address.street2 or "")] if s
        )
        text2 += converter.convert(street[:45], 45)
        text2 += " " * 24
        text2 += "\r\n"
        if len(text2) % 102 != 0:
            raise UserError(
                format_lazy(
                    self.env._(
                        'Configuration error:\n\nA line in "%(section)s" is not 100 '
                        "characters long:\n%(content)s"
                    ),
                    section="Beneficiary record, type 2",
                    content=text2,
                )
            )
        txt += text2

        # --- Type 012 (city + zip short)
        text3 = self._cabecera_beneficiario_68(line)
        text3 += "012"
        text3 += converter.convert(address.zip or "", 5)
        text3 += converter.convert((address.city or "")[:40], 40)
        text3 += " " * 24
        text3 += "\r\n"
        if len(text3) % 102 != 0:
            raise UserError(
                format_lazy(
                    self.env._(
                        'Configuration error:\n\nA line in "%(section)s" is not 100 '
                        "characters long:\n%(content)s"
                    ),
                    section="Beneficiary record, type 3",
                    content=text3,
                )
            )
        txt += text3

        # --- Type 013 (zip long + state + country)
        text4 = self._cabecera_beneficiario_68(line)
        text4 += "013"
        text4 += converter.convert(address.zip or "", 9)
        text4 += converter.convert((address.state_id.name or "")[:30], 30)
        text4 += converter.convert((address.country_id.name or "")[:20], 20)
        text4 += " " * 10
        text4 += "\r\n"
        if len(text4) % 102 != 0:
            raise UserError(
                format_lazy(
                    self.env._(
                        'Configuration error:\n\nA line in "%(section)s" is not 100 '
                        "characters long:\n%(content)s"
                    ),
                    section="Beneficiary record, type 4",
                    content=text4,
                )
            )
        txt += text4

        # --- Type 014 (num_of_payment + date + amount + country code)
        text5 = self._cabecera_beneficiario_68(line)
        text5 += "014"
        text5 += num_of_payment_txt

        pay_date = line.date or datetime.today().date()
        text5 += converter.convert(pay_date.strftime("%d%m%Y"), 8)

        # Use absolute amount; prefer line.amount if available
        amount = getattr(line, "amount", None)
        if amount is None:
            amount = getattr(line, "amount_currency", 0.0)  # fallback
        text5 += converter.convert(abs(amount), 12)
        text5 += "0"

        country_code = address.country_id.code or ""
        text5 += country_code if country_code != "ES" else " " * 2
        text5 += " " * 6
        text5 += " " * 32
        text5 += "\r\n"
        if len(text5) % 102 != 0:
            raise UserError(
                format_lazy(
                    self.env._(
                        'Configuration error:\n\nA line in "%(section)s" is not 100 '
                        "characters long:\n%(content)s"
                    ),
                    section="Beneficiary record, type 5",
                    content=text5,
                )
            )
        txt += text5

        # --- Type 015 (refs + generation date + amount + communication)
        text6 = self._cabecera_beneficiario_68(line)
        text6 += "015"
        text6 += num_of_payment_txt

        # Communication/reference
        ref = (line.communication or "").strip()
        ref_payment = converter.convert(ref, 12)
        communication = converter.convert(ref, 26)

        # Generated date (local variable, avoid runtime attribute)
        date_generated = datetime.today()
        date_create = converter.convert(date_generated.strftime("%d%m%Y"), 8)

        text6 += ref_payment
        text6 += date_create
        text6 += converter.convert(abs(amount), 12)
        text6 += "H"
        text6 += communication
        text6 += " " * 2
        text6 += "\r\n"
        if len(text6) % 102 != 0:
            raise UserError(
                format_lazy(
                    self.env._(
                        'Configuration error:\n\nA line in "%(section)s" is not 100 '
                        "characters long:\n%(content)s"
                    ),
                    section="Beneficiary record, type 6",
                    content=text6,
                )
            )
        txt += text6

        return txt

    def _total_general_68(self, total_payments, total_amount):
        self.ensure_one()
        converter = self.env["payment.converter.spain"]
        txt = "0859"
        txt += self._start_68()
        txt += " " * 12
        txt += " " * 3
        txt += converter.convert(abs(total_amount), 12)
        # Each beneficiary contributes 6 lines; +2 header/footer lines
        txt += converter.convert(abs(total_payments * 6 + 2), 10)
        txt += " " * 42
        txt += " " * 5
        txt += "\r\n"
        if len(txt) % 102 != 0:
            raise UserError(
                format_lazy(
                    self.env._(
                        'Configuration error:\n\nA line in "%(section)s" is not 100 '
                        "characters long:\n%(content)s"
                    ),
                    section="Registration of totals",
                    content=txt,
                )
            )
        return txt

    # ---------- Public API ---------------------------------------------------

    def generate_payment_file(self):
        """
        Create the CSB Direct Debit file for code 'csb_direct_debit_payments'.
        Falls back to super() for other methods.
        """
        self.ensure_one()
        if self.payment_method_id.code != "csb_direct_debit_payments":
            return super().generate_payment_file()

        txt_file = ""
        seq = 0
        total_payments = 0
        total_amount = 0.0

        # Header
        txt_file += self._cabecera_ordenante_68()

        # Beneficiaries (self.payment_ids are the payment lines on this order)
        for line in self.payment_ids:
            seq += 1
            txt_file += self._registro_beneficiario_68(line, seq)
            total_payments += 1
            amt = getattr(line, "amount", None)
            if amt is None:
                amt = getattr(line, "amount_currency", 0.0)
            total_amount += abs(amt)

        # Totals
        txt_file += self._total_general_68(total_payments, total_amount)

        # Filename
        filename = (
            self.name.replace("/", "_") + datetime.today().strftime("%d-%m-%Y") + ".txt"
        )
        return txt_file.encode(), filename
