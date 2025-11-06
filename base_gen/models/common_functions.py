# 2025 Alquiber / Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import base64
import datetime as dt
import secrets
import unicodedata

import babel.dates
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from odoo import models
from odoo.tools.misc import format_date as odoo_format_date
from odoo.tools.misc import formatLang


class CommonFunctions(models.AbstractModel):
    _name = "common.functions"
    _description = "Common functions to be used by other models"

    # -------------------------
    # Locale / Formatting
    # -------------------------

    def _lang_code(self, lang=None):
        return (
            lang
            or self.env.context.get("lang")
            or getattr(self.env, "lang", None)
            or "es_ES"
        )

    def transform_float_to_locale(self, float_number, precision, lang=False):
        """OCB-18: idioma por contexto y digits como entero; sin monetary/grouping."""
        lang_env = self.env(context={**self.env.context, "lang": self._lang_code(lang)})
        return formatLang(lang_env, float_number, digits=int(precision))

    def transform_date_to_locale(self, date, lang=False):
        """OCB-18: usar format_date con idioma por contexto (sin lang_code kwarg)."""
        if not date:
            return ""
        if isinstance(date, dt.datetime):
            date = date.date()
        lang_env = self.env(context={**self.env.context, "lang": self._lang_code(lang)})
        return odoo_format_date(lang_env, date)

    # -------------------------
    # Translations
    # -------------------------

    def get_value_from_translation(self, module, src, lang=None):
        """Devuelve traducción si existe; tolera builds sin ir.translation."""
        resp = src
        lang_code = self._lang_code(lang)
        if "ir.translation" not in self.env:
            return resp
        rec = (
            self.env["ir.translation"]
            .sudo()
            .search(
                [("lang", "=", lang_code), ("module", "=", module), ("src", "=", src)],
                limit=1,
            )
        )
        return rec.value or resp

    # -------------------------
    # Crypto
    # -------------------------

    def encrypt_data(self, params, cipher_key):
        """
        Cifra "-".join(params) con AES-CBC + PKCS#7 y IV aleatorio.
        Retorna base64(IV||CIPHERTEXT). Clave normalizada a 16/24/32 bytes.
        """
        payload = "-".join(params).encode("utf-8")

        key_bytes = cipher_key.encode("utf-8")
        if len(key_bytes) not in (16, 24, 32):
            key_bytes = (
                (key_bytes + b"\x00" * 32)[:32]
                if len(key_bytes) < 32
                else key_bytes[:32]
            )

        iv = secrets.token_bytes(16)
        ct = AES.new(key_bytes, AES.MODE_CBC, iv).encrypt(pad(payload, 16))
        return base64.b64encode(iv + ct).decode("utf-8")

    # -------------------------
    # Humanized date-as-text
    # -------------------------

    def get_date_as_text(self, date, with_year=True, lang=False):
        """p.ej., es_ES: '6 de noviembre de 2025'; en_US: 'November 6, 2025'."""
        if not date:
            return ""
        if isinstance(date, dt.datetime):
            date = date.date()
        lang_code = self._lang_code(lang)

        if lang_code.lower().startswith("es"):
            pattern = "d 'de' LLLL" + (" 'de' y" if with_year else "")
            return babel.dates.format_date(date, format=pattern, locale=lang_code)

        return babel.dates.format_date(
            date, format=("LLLL d, y" if with_year else "LLLL d"), locale=lang_code
        )

    # -------------------------
    # Text utilities
    # -------------------------

    def remove_accents(self, original_string):
        if not original_string:
            return original_string
        normalized = unicodedata.normalize("NFD", original_string)
        return "".join(c for c in normalized if not unicodedata.combining(c))
