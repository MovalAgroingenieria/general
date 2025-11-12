# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
from unittest.mock import patch

from odoo.tests.common import TransactionCase

# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=unused-variable


class _CommonSetup(TransactionCase):
    """Common records used by multiple HTTP tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        cls.company = cls.env.company
        cls.currency_eur = cls.env.ref("base.EUR")

        # Bank journal required by statements
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "BIP Test Bank",
                "code": "BIPT",
                "type": "bank",
                "company_id": cls.company.id,
                "currency_id": cls.currency_eur.id,
            }
        )

        # Online provider attached to the journal
        cls.provider = cls.env["online.bank.statement.provider"].create(
            {
                "journal_id": cls.journal.id,
                "service": "bankinplay",
                "statement_creation_mode": "daily",
                "tz": "UTC",
                # any other defaults the base model may need
            }
        )

    def _json_post(self, url, payload, expect_status=200):
        """Utility to call a json route and extract the JSON-RPC 'result'."""
        # Use HttpCase.url_open in subclasses; here we only define signature
        raise NotImplementedError

    def test_webhook_missing_fields(self):
        """Should ignore when required fields are missing."""
        out = self._json_post(
            "/webhook/bankinplay_callback",
            payload={"foo": "bar"},
        )
        self.assertEqual(out["status"], "ignored")
        self.assertIn("Missing required fields", out["message"])

    def test_webhook_wrong_event(self):
        """Should ignore events other than 'lectura_cierre'."""
        payload = {
            "responseId": "RID-1",
            "signature": "SIG-1",
            "triggered_event": "other_event",
            "data": {},
        }
        out = self._json_post("/webhook/bankinplay_callback", payload)
        self.assertEqual(out["status"], "ignored")
        self.assertIn("Event not handled", out["message"])

    def test_webhook_updates_local_statement(self):
        """When a matching statement exists, provider hook must be called and 'ok' returned."""
        # Create a statement bound to our journal and with matching keys
        st = self.env["account.bank.statement"].create(
            {
                "name": "TEST/LOCAL",
                "journal_id": self.journal.id,
                "date": "2025-01-10",
                "bankinplay_responseid": "RID-LOCAL",
                "bankinplay_signature": "SIG-LOCAL",
            }
        )

        # Patch the provider hook to assert it is invoked
        with patch.object(
            type(self.provider),
            "_bankinplay_update_statement_data_after_callback",
            autospec=True,
        ) as mocked:
            payload = {
                "responseId": "RID-LOCAL",
                "signature": "SIG-LOCAL",
                "triggered_event": "lectura_cierre",
                "data": {"results": []},
            }
            out = self._json_post("/webhook/bankinplay_callback", payload)
            self.assertEqual(out["status"], "ok")
            self.assertIn("Statement updated", out["message"])
            # Called exactly once with (self, bank_statement, data)
            mocked.assert_called_once()
            args, kwargs = mocked.call_args
            self.assertEqual(args[1], st)  # bank_statement
            self.assertEqual(args[2], {"results": []})  # data

    def test_webhook_remote_forward(self):
        """When only a bankinplay.response exists, data must be decrypted and forwarded."""
        # Prepare a stored response pointing to an external endpoint
        resp_row = self.env["bankinplay.response"].create(
            {
                "bankinplay_responseid": "RID-REMOTE",
                "bankinplay_signature": "SIG-REMOTE",
                "endpoint_return_url": "http://example.test",
            }
        )
        # Config params used by the controller to decrypt
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param(
            "l10n_es_account_statement_import_online_bankinplay.bankinplay_integration_api_key",
            "user-key",
        )
        icp.set_param(
            "l10n_es_account_statement_import_online_bankinplay.bankinplay_integration_api_secret",
            "pass-secret",
        )

        # Mock decrypt to return already-dict data; mock requests.post to avoid real IO
        with patch(
            "odoo.addons.l10n_es_account_statement_import_online_bankinplay.models.bankinplay_interface.BankedInplayInterface._decrypt_bankinplay_data",  # noqa: E501
            return_value={"results": [{"id": 1}]},
        ) as _, patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.text = json.dumps({"result": {"ok": True}})

            payload = {
                "responseId": "RID-REMOTE",
                "signature": "SIG-REMOTE",
                "triggered_event": "lectura_cierre",
                "data": "ciphertext==",
            }
            out = self._json_post("/webhook/bankinplay_callback", payload)
            self.assertEqual(out["status"], "ok")
            self.assertIn("Forwarded to remote endpoint", out["message"])

            # requests.post called with decrypted payload
            mock_post.assert_called_once()
            (called_url,) = mock_post.call_args[0]
            called_kwargs = mock_post.call_args.kwargs
            self.assertTrue(called_url.endswith("/webhook/bankinplay_callback"))
            self.assertEqual(called_kwargs["headers"]["Accept"], "application/json")
            forwarded = called_kwargs["json"]
            self.assertEqual(forwarded["data"], {"results": [{"id": 1}]})

            # The decrypted payload must be stored back in the response row
            self.assertTrue(resp_row.refresh())
            self.assertIn('"results": [{"id": 1}]', resp_row.bankinplay_response)

    # ---------------------------------
    # /remote/bankinplay_callback
    # ---------------------------------

    def test_remote_callback_invalid_params(self):
        """Invalid date / shape must return an error payload."""
        out = self._json_post(
            "/remote/bankinplay_callback",
            {
                "date_since": "BAD",
                "date_until": "BAD",
                "bankinplay_account": [],
                "return_url": "",
            },
        )
        self.assertEqual(out["status"], "error")
        self.assertIn("Invalid parameters", out["message"])

    def test_remote_callback_happy_path(self):
        """Should login, set account, ask for callback, and create a stored response."""
        with patch(
            "odoo.addons.l10n_es_account_statement_import_online_bankinplay.models.bankinplay_interface.BankinplayInterface._login",  # noqa: E501
            return_value={"access_token": "tok", "username": "u", "password": "p"},
        ) as _, patch(
            "odoo.addons.l10n_es_account_statement_import_online_bankinplay.models.bankinplay_interface.BankinplayInterface._set_access_account",  # noqa: E501
        ) as _, patch(
            "odoo.addons.l10n_es_account_statement_import_online_bankinplay.models.bankinplay_interface.BankinplayInterface._set_close_movements_callback",  # noqa: E501
            return_value={
                "bankinplay_signature": "SIG-X",
                "bankinplay_responseid": "RID-X",
            },
        ) as _:
            payload = {
                "date_since": "01/01/2025",
                "date_until": "31/01/2025",
                "bankinplay_account": [123, "ACC"],
                "return_url": "http://caller.example",
            }
            out = self._json_post("/remote/bankinplay_callback", payload)
            # Controller returns {"result": {...}} with signature/response_id
            self.assertEqual(out["signature"], "SIG-X")
            self.assertEqual(out["response_id"], "RID-X")

            # Stored response should have been created
            stored = self.env["bankinplay.response"].search(
                [
                    ("bankinplay_signature", "=", "SIG-X"),
                    ("bankinplay_responseid", "=", "RID-X"),
                    ("endpoint_return_url", "=", "http://caller.example"),
                ],
                limit=1,
            )
            self.assertTrue(stored)

    def test_remote_callback_provider_missing_ids(self):
        """If provider returns no signature/response_id, controller should error."""
        with patch(
            "odoo.addons.l10n_es_account_statement_import_online_bankinplay.models.bankinplay_interface.BankinplayInterface._login",  # noqa: E501
            return_value={"access_token": "tok", "username": "u", "password": "p"},
        ), patch(
            "odoo.addons.l10n_es_account_statement_import_online_bankinplay.models.bankinplay_interface.BankinplayInterface._set_access_account",  # noqa: E501
        ), patch(
            "odoo.addons.l10n_es_account_statement_import_online_bankinplay.models.bankinplay_interface.BankinplayInterface._set_close_movements_callback",  # noqa: E501
            return_value={"bankinplay_signature": None, "bankinplay_responseid": None},
        ):
            payload = {
                "date_since": "01/01/2025",
                "date_until": "31/01/2025",
                "bankinplay_account": [123, "ACC"],
                "return_url": "http://caller.example",
            }
            out = self._json_post("/remote/bankinplay_callback", payload)
            self.assertEqual(out["status"], "error")
            self.assertIn("Provider did not return", out["message"])
