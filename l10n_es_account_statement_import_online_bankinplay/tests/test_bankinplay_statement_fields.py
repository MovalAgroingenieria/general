# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=unused-variable
# pylint: disable=protected-access
from datetime import date

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestBankinplayStatementFields(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company
        cls.currency_eur = cls.env.ref("base.EUR")

        # Crea un diario bancario mínimo para poder crear extractos
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "BankInPlay Test Bank",
                "code": "BIPT",
                "type": "bank",
                "company_id": cls.company.id,
                "currency_id": cls.currency_eur.id,
            }
        )

    def _create_statement(self, name_suffix="", vals=None):
        values = {
            "name": f"TEST/{date.today().isoformat()}{name_suffix}",
            "journal_id": self.journal.id,
            "date": date.today(),
        }
        if vals:
            values.update(vals)
        return self.env["account.bank.statement"].create(values)

    def test_create_statement_with_bankinplay_fields(self):
        """Debe poder crear un extracto con los campos BankInPlay informados."""
        st = self._create_statement(
            "-A",
            {
                "bankinplay_signature": "sig-001",
                "bankinplay_responseid": "resp-001",
                "bankinplay_date_since": "2025-01-01 00:00:00",
                "bankinplay_date_until": "2025-01-31 23:59:59",
            },
        )
        self.assertEqual(st.bankinplay_signature, "sig-001")
        self.assertEqual(st.bankinplay_responseid, "resp-001")
        self.assertTrue(st.bankinplay_date_since)
        self.assertTrue(st.bankinplay_date_until)

    def test_allow_multiple_null_pairs(self):
        """La restricción única permite múltiples filas con (NULL, NULL)."""
        st1 = self._create_statement("-N1")
        st2 = self._create_statement("-N2")
        self.assertTrue(st1)
        self.assertTrue(st2)

    def test_allow_partial_duplicates(self):
        """Duplicados parciales (solo uno de los dos campos) están permitidos."""
        # Mismo responseid, distinta signature
        self._create_statement(
            "-P1",
            {"bankinplay_responseid": "RID-100", "bankinplay_signature": "SIG-100"},
        )
        self._create_statement(
            "-P2",
            {"bankinplay_responseid": "RID-100", "bankinplay_signature": "SIG-101"},
        )

        # Misma signature, distinto responseid
        self._create_statement(
            "-P3",
            {"bankinplay_responseid": "RID-200", "bankinplay_signature": "SIG-200"},
        )
        self._create_statement(
            "-P4",
            {"bankinplay_responseid": "RID-201", "bankinplay_signature": "SIG-200"},
        )

    def test_block_exact_duplicate_pair(self):
        """No debe permitir crear dos extractos con el mismo (responseid, signature)."""
        self._create_statement(
            "-D1",
            {"bankinplay_responseid": "RID-XYZ", "bankinplay_signature": "SIG-XYZ"},
        )

        with mute_logger("odoo.sql_db"), self.assertRaises(Exception):
            # El tipo concreto es IntegrityError de psycopg2; usamos Exception
            # para evitar dependencia directa. Odoo lo re-lanza como excepción SQL.
            self._create_statement(
                "-D2",
                {"bankinplay_responseid": "RID-XYZ", "bankinplay_signature": "SIG-XYZ"},
            )
