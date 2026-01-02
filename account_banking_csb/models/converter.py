# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import re
import traceback
from decimal import Decimal
from unicodedata import combining, normalize

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_FLOAT_RE = re.compile(r"^[+-]?\d+([.,]\d+)?([eE][+-]?\d+)?$")


class PaymentConverterSpain(models.Model):
    _name = "payment.converter.spain"
    _description = "Payment converter for Spain"

    # ------------------------------ utils ------------------------------------

    @api.model
    def digits_only(self, s):
        """Return only numeric characters from the input."""
        return "".join(ch for ch in (s or "") if ch.isdigit())

    @api.model
    def _strip_accents(self, text: str) -> str:
        """
        Convert accented chars to closest ASCII; keep ñ/Ñ → n/N, ç/Ç → c/C,
        and map a few special symbols.
        """
        text = text or ""
        # Normalize and drop combining marks
        nfkd = normalize("NFKD", text)
        base = "".join(ch for ch in nfkd if not combining(ch))
        # Post-map cases not covered nicely by NFKD or for consistency
        replacements = {
            "ñ": "n",
            "Ñ": "N",
            "ç": "c",
            "Ç": "C",
            "ª": "a",
            "º": "o",
            "·": ".",
            "\n": " ",
        }
        for old, new in replacements.items():
            base = base.replace(old, new)
        return base

    @api.model
    def to_ascii(self, text: str) -> str:
        """Public ASCII-normalizer (kept for API compatibility)."""
        return self._strip_accents(text)

    # --------------------------- formatting ----------------------------------

    @api.model
    def convert_text(self, text, size: int, justified: str = "left") -> str:
        txt = self.to_ascii(str(text or ""))
        txt = txt[:size]
        return txt.ljust(size) if justified == "left" else txt.rjust(size)

    @api.model
    def convert_float(self, number, size: int) -> str:
        """
        Format monetary/float as integer cents, zero-filled to `size`.
        """
        # Accept float/Decimal/str
        if isinstance(number, str):
            try:
                number = Decimal(number)
            except Exception as exc:
                _logger.exception(
                    "Invalid float string in convert_float. "
                    "value=%r size=%s\nSTACK:\n%s",
                    number,
                    size,
                    "".join(traceback.format_stack(limit=25)),
                )
                raise UserError(
                    self.env._("Invalid float string: %(value)s", value=number)
                ) from exc
        elif isinstance(number, float):
            number = Decimal(str(number))
        elif isinstance(number, int):
            number = Decimal(number)

        if not isinstance(number, Decimal):
            raise UserError(
                self.env._(
                    "Unsupported number type: %(tname)s", tname=type(number).__name__
                )
            )

        cents = int((number * Decimal("100")).quantize(Decimal("1")))
        text = str(cents)
        if len(text) > size:
            raise UserError(
                self.env._(
                    "Error:\n\nCan not convert float number %(num).2f to "
                    "fit in %(size)d characters.",
                    num=float(number),
                    size=size,
                )
            )
        return text.zfill(size)

    @api.model
    def convert_int(self, number, size: int) -> str:
        try:
            ival = int(number)
        except Exception as exc:
            raise UserError(
                self.env._("Invalid integer: %(value)s", value=number)
            ) from exc
        text = str(ival)
        if len(text) > size:
            raise UserError(
                self.env._(
                    "Error:\n\nCan not convert integer number %(num)d to fit "
                    "in %(size)d characters.",
                    num=ival,
                    size=size,
                )
            )
        return text.zfill(size)

    @api.model
    def convert(self, value, size: int, justified: str = "left") -> str:
        """
        Generic converter:
          - None/'' → padded blank text
          - float/Decimal → convert_float
          - int → convert_int
          - else → convert_text
        """
        if value in (None, "", False):
            return self.convert_text("", size, justified)

        if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
            return self.convert_int(value, size)

        if isinstance(value, (float, Decimal, str)) and self._looks_numeric_float(
            value
        ):
            _logger.debug(
                "Routing value to convert_float. value=%r type=%s "
                "size=%s justified=%s\nSTACK:\n%s",
                value,
                type(value).__name__,
                size,
                justified,
                "".join(traceback.format_stack(limit=25)),
            )
            return self.convert_float(value, size)

        return self.convert_text(value, size, justified)

    @api.model
    def _looks_numeric_float(self, value) -> bool:
        if isinstance(value, (float, Decimal, int)):
            return True
        if isinstance(value, str):
            v = value.strip()
            return bool(_FLOAT_RE.match(v))
        return False

    # --------------------------- bank helpers --------------------------------

    @api.model
    def _extract_ccc_from_any(self, value: str) -> str:
        """
        Try to extract a 20-digit Spanish CCC from either:
          - raw CCC (20 digits), or
          - Spanish IBAN (ESkk + 20 digits) → take last 20 digits.
        """
        digits = self.digits_only(value)
        if len(digits) == 20:
            return digits
        # ES IBAN has 24 chars; if we see >= 22 digits, take the last 20
        if (
            value
            and isinstance(value, str)
            and value.strip().upper().startswith("ES")
            and len(digits) >= 22
        ):
            return digits[-20:]
        return digits  # let caller validate length

    @api.model
    def convert_bank_account(self, value, partner_name: str) -> str:
        """
        Return a 20-digit CCC for Spain. Accepts CCC or ES IBAN.
        Raises UserError if not valid.
        """
        if not value:
            raise UserError(
                self.env._(
                    "User error:\n\nThe bank account number of %(partner)s "
                    "is not defined.",
                    partner=partner_name,
                )
            )
        ccc = self._extract_ccc_from_any(value)
        if len(ccc) != 20:
            raise UserError(
                self.env._(
                    "User error:\n\nThe bank account number of %(partner)s does "
                    "not have 20 digits.",
                    partner=partner_name,
                )
            )
        return ccc

    @api.model
    def bank_account_parts(self, value, partner_name: str):
        """
        Split a Spanish CCC (20 digits) into parts: bank, office, dc, account.
        Accepts CCC or ES IBAN.
        """
        ccc = self.convert_bank_account(value, partner_name)
        return {
            "bank": ccc[:4],
            "office": ccc[4:8],
            "dc": ccc[8:10],
            "account": ccc[10:],
        }
