# tests/test_common_functions.py
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import base64
import datetime as dt
import unittest

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# --- Odoo test base: SavepointCase (si existe) o TransactionCase (OCB-18) ---
try:
    from odoo.tests.common import SavepointCase as BaseCase
except ImportError:
    from odoo.tests.common import TransactionCase as BaseCase

from odoo.tools.misc import format_date as odoo_format_date
from odoo.tools.misc import formatLang


def env_with_lang(env, lang):
    """Devuelve un env con el lang en contexto (compatible OCB-18)."""
    return env(context=dict(env.context, lang=lang))


class TestCommonFunctions(BaseCase):
    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.cf = cls.env["common.functions"]
        cls.key = "super-secret-key-32bytes"

    # -------------------------
    # transform_float_to_locale
    # -------------------------
    def test_transform_float_to_locale_es_en(self):
        val = 1234.567
        expected_es = formatLang(env_with_lang(self.env, "es_ES"), val, digits=2)
        expected_en = formatLang(env_with_lang(self.env, "en_US"), val, digits=2)

        got_es = self.cf.transform_float_to_locale(val, 2, lang="es_ES")
        got_en = self.cf.transform_float_to_locale(val, 2, lang="en_US")

        self.assertEqual(got_es, expected_es)
        self.assertEqual(got_en, expected_en)

    # -------------------------
    # transform_date_to_locale
    # -------------------------
    def test_transform_date_to_locale_matches_odoo_helper(self):
        d = dt.date(2025, 11, 6)
        expected_es = odoo_format_date(env_with_lang(self.env, "es_ES"), d)
        expected_en = odoo_format_date(env_with_lang(self.env, "en_US"), d)

        got_es = self.cf.transform_date_to_locale(d, lang="es_ES")
        got_en = self.cf.transform_date_to_locale(d, lang="en_US")

        self.assertEqual(got_es, expected_es)
        self.assertEqual(got_en, expected_en)

    # -------------------------
    # get_value_from_translation
    # -------------------------
    def test_get_value_from_translation_hits_ir_translation(self):
        # Si por cualquier motivo el modelo no está disponible en este build, saltamos.
        if "ir.translation" not in self.env:
            raise unittest.SkipTest("ir.translation no disponible en este entorno")

        module = "test_common_functions"
        src = "HELLO_WORLD"
        es_value = "HOLA_MUNDO"

        self.env["ir.translation"].sudo().create(
            {
                "name": "common.functions",  # cualquier nombre
                "lang": "es_ES",
                "type": "model",
                "src": src,
                "value": es_value,
                "module": module,
                "state": "translated",
            }
        )

        got_es = self.cf.get_value_from_translation(module, src, lang="es_ES")
        got_en = self.cf.get_value_from_translation(module, src, lang="en_US")

        self.assertEqual(got_es, es_value)
        self.assertEqual(got_en, src)

    # -------------------------
    # encrypt_data
    # -------------------------
    def test_encrypt_data_roundtrip_with_local_decrypt(self):
        params = ["user123", "tokenABC", "scope-read"]
        b64 = self.cf.encrypt_data(params, self.key)

        raw = base64.b64decode(b64)
        self.assertGreater(len(raw), 16)

        iv, ct = raw[:16], raw[16:]
        key_bytes = self.key.encode("utf-8")
        if len(key_bytes) not in (16, 24, 32):
            if len(key_bytes) < 32:
                key_bytes = (key_bytes + b"\x00" * 32)[:32]
            else:
                key_bytes = key_bytes[:32]

        cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
        payload = unpad(cipher.decrypt(ct), 16).decode("utf-8")
        self.assertEqual(payload, "-".join(params))

    def test_encrypt_data_changes_iv_each_time(self):
        params = ["a", "b", "c"]
        b64_a = self.cf.encrypt_data(params, self.key)
        b64_b = self.cf.encrypt_data(params, self.key)
        self.assertNotEqual(b64_a, b64_b)

    # -------------------------
    # get_date_as_text
    # -------------------------
    def test_get_date_as_text_es(self):
        d = dt.date(2025, 11, 6)
        txt = self.cf.get_date_as_text(d, with_year=True, lang="es_ES")
        self.assertEqual(txt, "6 de noviembre de 2025")

        txt_no_year = self.cf.get_date_as_text(d, with_year=False, lang="es_ES")
        self.assertEqual(txt_no_year, "6 de noviembre")

    def test_get_date_as_text_en(self):
        d = dt.date(2025, 11, 6)
        txt = self.cf.get_date_as_text(d, with_year=True, lang="en_US")
        self.assertEqual(txt, "November 6, 2025")

        txt_no_year = self.cf.get_date_as_text(d, with_year=False, lang="en_US")
        self.assertEqual(txt_no_year, "November 6")

    # -------------------------
    # remove_accents
    # -------------------------
    def test_remove_accents(self):
        self.assertEqual(self.cf.remove_accents("canción"), "cancion")
        self.assertEqual(
            self.cf.remove_accents("Árbol Ñandú Ümlaut"), "Arbol Nandu Umlaut"
        )
        self.assertEqual(self.cf.remove_accents(""), "")
        self.assertIsNone(self.cf.remove_accents(None))


if __name__ == "__main__":
    unittest.main()
