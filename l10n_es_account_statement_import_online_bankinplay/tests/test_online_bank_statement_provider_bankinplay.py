# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=unused-variable
# pylint: disable=protected-access
from datetime import datetime
from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestOnlineBankStatementProviderBankinplay(TransactionCase):
    """Integration-ish tests for the BankInPlay provider adapter on v18.

    Notes:
    - Each provider must be bound to a distinct journal because the base model
      enforces UNIQUE(journal_id). We provide helpers to create fresh journals/providers.
    - We ensure EUR is active, and we create a proper liquidity account so
      statement line creation doesn’t blow up on missing accounts.
    """

    @classmethod
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company

        # Ensure EUR is active
        eur = cls.env.ref("base.EUR")
        if not eur.active:
            eur.active = True
        cls.currency_eur = eur

        cls._acc_seq = 0

        def _new_liquidity_account():
            """Create a liquidity account; handle company_id vs company_ids."""
            cls._acc_seq += 1
            Account = cls.env["account.account"]
            vals = {
                "name": f"Test Bank {cls._acc_seq}",
                "code": f"5719{cls._acc_seq:03d}",
                "account_type": "asset_cash",
            }
            # v18 uses company_ids (M2M); some forks may keep company_id (M2O).
            if "company_ids" in Account._fields:
                vals["company_ids"] = [(6, 0, [cls.company.id])]
            elif "company_id" in Account._fields:
                vals["company_id"] = cls.company.id
            return Account.create(vals)

        cls._new_liquidity_account = staticmethod(_new_liquidity_account)

    def _new_journal(self, code="BIPJ"):
        """Create a bank journal wired to a valid liquidity account."""
        liquidity = self._new_liquidity_account()
        return self.env["account.journal"].create(
            {
                "name": f"BankInPlay {code}",
                "code": code,
                "type": "bank",
                "company_id": self.company.id,
                "currency_id": self.currency_eur.id,
                "default_account_id": liquidity.id,
            }
        )

    def _new_provider(self, journal=None, **vals):
        """Create a provider on a fresh journal to avoid UNIQUE(journal_id)."""
        journal = journal or self._new_journal(
            code=f"B{int(datetime.now().timestamp())}"
        )
        base = {
            "journal_id": journal.id,
            "service": "bankinplay",
            "statement_creation_mode": "daily",
            "tz": "UTC",
            "bankinplay_date_field": "operation_date",
            "bankinplay_delay_days": 0,
            "bankinplay_end_point_type": "same_endpoint",
            "username": "user-key",
            "password": "pass-secret",
            "account_number": "ES1122334455667788990011",
        }
        base.update(vals)
        return self.env["online.bank.statement.provider"].create(base)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Basic service registration
    # ------------------------------------------------------------------

    def test_get_available_services_contains_bankinplay(self):
        prov = self._new_provider()
        services = prov._get_available_services()
        self.assertIn(("bankinplay", "BankInPlay.com"), services)

    # ------------------------------------------------------------------
    # Date helpers
    # ------------------------------------------------------------------

    def test_get_statement_date_since_monthly(self):
        prov = self._new_provider(
            bankinplay_delay_days=5, statement_creation_mode="monthly"
        )
        d = datetime(2025, 11, 20, 10, 0, 0)
        out = prov._get_statement_date_since(d)
        # 5 days back => 2025-11-15 -> month start = 2025-11-01
        self.assertEqual(out, datetime(2025, 11, 1, 0, 0, 0))

    # ------------------------------------------------------------------
    # Dispatch / bootstrap
    # ------------------------------------------------------------------

    def test_obtain_statement_data_dispatches_to_bankinplay(self):
        prov = self._new_provider()
        with patch.object(
            type(prov),
            "_bankinplay_obtain_statement_data",
            autospec=True,
            return_value=([], {"r": 1}),
        ) as mock:
            lines, extra = prov._obtain_statement_data(
                datetime(2025, 1, 1), datetime(2025, 1, 31)
            )
            self.assertEqual(lines, [])
            self.assertEqual(extra, {"r": 1})
            mock.assert_called_once()

    # ------------------------------------------------------------------
    # Retrieve (same / remote)
    # ------------------------------------------------------------------

    def test_bankinplay_retrieve_data_same_endpoint(self):
        prov = self._new_provider(bankinplay_end_point_type="same_endpoint")
        with patch(
            "odoo.addons.l10n_es_account_statement_import_online_bankinplay.models.bankinplay_interface.BankinplayInterface._login",
            return_value={"access_token": "tok", "username": "u", "password": "p"},
        ) as _, patch(
            "odoo.addons.l10n_es_account_statement_import_online_bankinplay.models.bankinplay_interface.BankinplayInterface._set_access_account"
        ) as _, patch(
            "odoo.addons.l10n_es_account_statement_import_online_bankinplay.models.bankinplay_interface.BankinplayInterface._set_close_movements_callback",
            return_value={"bankinplay_signature": "S", "bankinplay_responseid": "R"},
        ) as _:
            out = prov._bankinplay_retrieve_data(
                datetime(2025, 1, 1), datetime(2025, 1, 31)
            )
            self.assertEqual(out["bankinplay_signature"], "S")
            self.assertEqual(out["bankinplay_responseid"], "R")

    def test_bankinplay_retrieve_data_remote_endpoint(self):
        prov = self._new_provider(
            bankinplay_end_point_type="remote_endpoint",
            bankinplay_end_point="https://remote.example",
        )
        with patch(
            "odoo.addons.l10n_es_account_statement_import_online_bankinplay.models.bankinplay_interface.BankinplayInterface._set_close_movements_callback_remote_endpoint",
            return_value={"bankinplay_signature": "S2", "bankinplay_responseid": "R2"},
        ):
            out = prov._bankinplay_retrieve_data(
                datetime(2025, 2, 1), datetime(2025, 2, 28)
            )
            self.assertEqual(out["bankinplay_signature"], "S2")
            self.assertEqual(out["bankinplay_responseid"], "R2")

    # ------------------------------------------------------------------
    # Statement creation/update (BankInPlay path)
    # ------------------------------------------------------------------

    def test_create_or_update_no_lines_creates_nothing(self):
        """With an empty payload, no statement should be created."""
        prov = self._new_provider()
        before = self.env["account.bank.statement"].search_count(
            [("journal_id", "=", prov.journal_id.id)]
        )
        prov._create_or_update_statement_bankinplay(
            data=([], {}),
            statement_date_since=datetime(2025, 1, 1),
            statement_date_until=datetime(2025, 1, 31),
        )
        after = self.env["account.bank.statement"].search_count(
            [("journal_id", "=", prov.journal_id.id)]
        )
        self.assertEqual(before, after)

    # ------------------------------------------------------------------
    # Callback post-processing
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Data translation
    # ------------------------------------------------------------------

    def test_get_transactions_from_data_decrypts_and_maps(self):
        prov = self._new_provider()
        dec_payload = {
            "results": [
                {
                    "id": "1",
                    "descripcion": "  Hello   World ",
                    "importeAbsoluto": 10,
                    "signo": "Cobro",
                    "fechaOperacion": "2025-01-05T10:00:00Z",
                }
            ]
        }
        with patch(
            "odoo.addons.l10n_es_account_statement_import_online_bankinplay.models.bankinplay_interface.BankinplayInterface._login",
            return_value={"access_token": "tok", "username": "u", "password": "p"},
        ), patch(
            "odoo.addons.l10n_es_account_statement_import_online_bankinplay.models.bankinplay_interface.BankinplayInterface._decrypt_bankinplay_data",
            return_value=dec_payload,
        ):
            lines = prov._bankinplay_get_transactions_from_data("ciphertext==")
            self.assertEqual(len(lines), 1)
            self.assertEqual(lines[0]["ref"], "Hello World")
            self.assertEqual(lines[0]["amount"], 10.0)
            self.assertEqual(lines[0]["unique_import_id"], "1")

    def test_get_transactions_from_data_remote_uses_plain_results(self):
        prov = self._new_provider()
        lines = prov._bankinplay_get_transactions_from_data_remote(
            {
                "results": [
                    {
                        "id": "2",
                        "descripcion": "Ref",
                        "importeAbsoluto": 5,
                        "signo": "Pago",
                        "fechaOperacion": "2025-01-06T10:00:00Z",
                    }
                ]
            }
        )
        self.assertEqual(len(lines), 1)
        # Pago => negative
        self.assertEqual(lines[0]["amount"], -5.0)

    # ------------------------------------------------------------------
    # Date parsing & timezone
    # ------------------------------------------------------------------

    def test_datetime_parsing_operation_vs_value_and_tz(self):
        prov = self._new_provider(tz="Europe/Madrid")  # CET/CEST via pytz
        tx = {
            "id": "3",
            "descripcion": "Ref",
            "importeAbsoluto": 1,
            "signo": "Cobro",
            "fechaOperacion": "2024-05-31T14:00:00Z",  # UTC
            "fechaValor": "2024-05-31T12:00:00Z",
        }

        # operation_date is default
        dt_op = prov._bankinplay_get_transaction_datetime(tx)
        # May in Madrid -> CEST (UTC+2) => 16:00 local, naive datetime returned
        self.assertEqual(dt_op.hour, 16)
        self.assertIsNone(dt_op.tzinfo)

        # value_date switching
        prov.bankinplay_date_field = "value_date"
        dt_val = prov._bankinplay_get_transaction_datetime(tx)
        # 12:00Z -> 14:00 local
        self.assertEqual(dt_val.hour, 14)
        self.assertIsNone(dt_val.tzinfo)
