# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime

from odoo import models
from odoo.exceptions import UserError


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
            raise UserError(
                self.env._(
                    "Missing VAT on partner %(partner)s",
                    partner=line.partner_id.display_name,
                )
            )
        id_code = converter.digits_only(vat)
        num_str = str(num_of_payment).zfill(7)
        base_number = int((id_code or "0") + num_str)
        control_digit = base_number % 7
        return f"{num_str}{control_digit}"

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
            raise UserError(
                self.env._(
                    "The Transaction Initiator Identifier or Transaction Issuer "
                    "have not been configured."
                )
            )
        return converter.convert(start_68, 12)

    def _get_partner_address(self, partner):
        """Get the appropriate address for a partner (invoice > default)."""
        address = partner
        addr_map = partner.address_get(["invoice", "default"])
        if addr_map.get("invoice"):
            address = self.env["res.partner"].browse(addr_map["invoice"])
        elif addr_map.get("default"):
            address = self.env["res.partner"].browse(addr_map["default"])
        if not address:
            raise UserError(
                self.env._(
                    "User error:\n\nPartner %(partner)s has no "
                    "invoicing or default address.",
                    partner=partner.display_name,
                )
            )
        return address

    def _validate_line_length(self, text, line_type):
        """Validate that a line has the correct length (100 characters)."""
        if len(text) % 102 != 0:
            raise UserError(
                self.env._(
                    'Configuration error:\n\nA line in "%(line_type)s" is not 100 '
                    "characters long:\n%(content)s",
                    line_type=line_type,
                    content=text,
                )
            )

    def _create_beneficiary_line_010(self, line, partner):
        """Create beneficiary record type 010 (name)."""
        converter = self.env["payment.converter.spain"]
        text = self._cabecera_beneficiario_68(line)
        text += "010"
        text += converter.convert_text((partner.name or "")[:40], 40)
        text += " " * 29
        text += "\r\n"
        self._validate_line_length(text, "Beneficiary record, type 1")
        return text

    def _create_beneficiary_line_011(self, line, address):
        """Create beneficiary record type 011 (street)."""
        converter = self.env["payment.converter.spain"]
        text = self._cabecera_beneficiario_68(line)
        text += "011"
        street = " ".join(
            s for s in [(address.street or ""), (address.street2 or "")] if s
        )
        text += converter.convert(street[:45], 45)
        text += " " * 24
        text += "\r\n"
        self._validate_line_length(text, "Beneficiary record, type 2")
        return text

    def _create_beneficiary_line_012(self, line, address):
        """Create beneficiary record type 012 (city + zip short)."""
        converter = self.env["payment.converter.spain"]
        text = self._cabecera_beneficiario_68(line)
        text += "012"
        text += converter.convert(address.zip or "", 5)
        text += converter.convert((address.city or "")[:40], 40)
        text += " " * 24
        text += "\r\n"
        self._validate_line_length(text, "Beneficiary record, type 3")
        return text

    def _create_beneficiary_line_013(self, line, address):
        """Create beneficiary record type 013 (zip long + state + country)."""
        converter = self.env["payment.converter.spain"]
        text = self._cabecera_beneficiario_68(line)
        text += "013"
        text += converter.convert(address.zip or "", 9)
        text += converter.convert((address.state_id.name or "")[:30], 30)
        text += converter.convert((address.country_id.name or "")[:20], 20)
        text += " " * 10
        text += "\r\n"
        self._validate_line_length(text, "Beneficiary record, type 4")
        return text

    def _create_beneficiary_line_014(self, line, num_of_payment_txt, address, amount):
        """Create beneficiary record type 014 (payment details)."""
        converter = self.env["payment.converter.spain"]
        text = self._cabecera_beneficiario_68(line)
        text += "014"
        text += num_of_payment_txt

        pay_date = line.date or datetime.today().date()
        text += converter.convert(pay_date.strftime("%d%m%Y"), 8)
        text += converter.convert(abs(amount), 12)
        text += "0"

        country_code = address.country_id.code or ""
        text += country_code if country_code != "ES" else " " * 2
        text += " " * 6
        text += " " * 32
        text += "\r\n"
        self._validate_line_length(text, "Beneficiary record, type 5")
        return text

    def _create_beneficiary_line_015(self, line, num_of_payment_txt, amount):
        """Create beneficiary record type 015 (references + communication)."""
        converter = self.env["payment.converter.spain"]
        text = self._cabecera_beneficiario_68(line)
        text += "015"
        text += num_of_payment_txt

        # Communication/reference
        ref = (line.communication or "").strip()
        ref_payment = converter.convert(ref, 12)
        communication = converter.convert(ref, 26)

        # Generated date
        date_create = converter.convert(datetime.today().strftime("%d%m%Y"), 8)

        text += ref_payment
        text += date_create
        text += converter.convert(abs(amount), 12)
        text += "H"
        text += communication
        text += " " * 2
        text += "\r\n"
        self._validate_line_length(text, "Beneficiary record, type 6")
        return text

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
            raise UserError(
                self.env._(
                    "Configuration error:\n\n No account bank number found "
                    "for ordering party: Cabecera ordenante 68"
                )
            )
        txt += converter.convert(acc_number, 24)
        txt += " " * 30
        txt += "\r\n"

        self._validate_line_length(txt, "Cabecera ordenante 68")
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
        partner = line.partner_id
        address = self._get_partner_address(partner)
        num_of_payment_txt = self._calculate_num_of_payment(line, num_of_payment)

        # Get amount
        amount = getattr(line, "amount", None)
        if amount is None:
            amount = getattr(line, "amount_currency", 0.0)

        # Build all beneficiary record types
        txt = self._create_beneficiary_line_010(line, partner)
        txt += self._create_beneficiary_line_011(line, address)
        txt += self._create_beneficiary_line_012(line, address)
        txt += self._create_beneficiary_line_013(line, address)
        txt += self._create_beneficiary_line_014(
            line, num_of_payment_txt, address, amount
        )
        txt += self._create_beneficiary_line_015(line, num_of_payment_txt, amount)

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
        self._validate_line_length(txt, "Registration of totals")
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

        for line in self.payment_line_ids:
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
