# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=unused-variable
# pylint: disable=protected-access

import base64
import json
from unittest.mock import patch

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


def _aes_cbc_encrypt_base64(payload_dict, key, iv):
    """Helper used by tests to craft Bankinplay V2-like ciphertext."""
    key_size = 16
    iv_size = 16
    key = (key or "").ljust(key_size, "$")[:key_size].encode()
    iv = (iv or "").ljust(iv_size, "$")[:iv_size].encode()

    plaintext = json.dumps(payload_dict, separators=(",", ":")).encode()
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded = padder.update(plaintext) + padder.finalize()

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ct = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(ct).decode()


class FakeResponse:
    """Minimal HTTP response stub compatible with our helper expectations."""

    def __init__(self, status=200, body=None, url="http://test", json_obj=None):
        self.status_code = status
        self.text = (
            body
            if body is not None
            else (json.dumps(json_obj) if json_obj is not None else "")
        )
        self._json_obj = json_obj
        self.url = url

    def json(self):
        if self._json_obj is None:
            raise ValueError("No JSON")
        return self._json_obj


class TestBankinplayInterface(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.iface = cls.env["bankinplay.interface"]

    # ---------------------------
    # Crypto
    # ---------------------------

    def test_decrypt_roundtrip(self):
        """AES-CBC base64 ciphertext should decrypt back to the original dict."""
        key = "user-key"
        iv = "pass-secret"
        payload = {"results": [{"id": 1, "amount": 10.5}]}
        cipher_b64 = _aes_cbc_encrypt_base64(payload, key, iv)

        out = self.iface._decrypt_bankinplay_data(cipher_b64, key, iv)
        self.assertEqual(out, payload)

    # ---------------------------
    # Login
    # ---------------------------

    def test_login_success(self):
        """_login returns access token and echoes credentials on success."""
        with patch("requests.post") as mpost:
            mpost.return_value = FakeResponse(json_obj={"access_token": "tok"})
            data = self.iface._login("u", "p")
            self.assertEqual(data["access_token"], "tok")
            self.assertEqual(data["username"], "u")
            self.assertEqual(data["password"], "p")

    def test_login_missing_creds(self):
        """_login must fail if username/password missing."""
        with self.assertRaises(UserError):
            self.iface._login("", "p")
        with self.assertRaises(UserError):
            self.iface._login("u", "")

    def test_login_no_token(self):
        """Missing token in HTTP 200 should raise."""
        with patch("requests.post") as mpost:
            mpost.return_value = FakeResponse(json_obj={"not": "here"})
            with self.assertRaises(UserError):
                self.iface._login("u", "p")

    # ---------------------------
    # _get_response_data
    # ---------------------------

    def test_get_response_data_non_json(self):
        """Non-JSON 200 body should raise a clean UserError."""
        resp = FakeResponse(status=200, body="not-json", json_obj=None)
        with self.assertRaises(UserError):
            self.iface._get_response_data(resp)

    def test_get_response_data_status_error(self):
        """Non 200/201 status must raise with body included."""
        resp = FakeResponse(status=500, body="oops")
        with self.assertRaises(UserError):
            self.iface._get_response_data(resp)

    # ---------------------------
    # POST/GET helpers & V2 decryption
    # ---------------------------

    def test_post_request_decrypts_when_signature_and_data(self):
        """_post_request should transparently decrypt V2 payloads."""
        access = {
            "access_token": "tok",
            "username": "user-key",
            "password": "pass-secret",
        }
        decrypted = {"results": [{"id": 7}]}
        ciphertext = _aes_cbc_encrypt_base64(
            decrypted, access["username"], access["password"]
        )

        with patch("requests.post") as mpost:
            mpost.return_value = FakeResponse(
                json_obj={"signature": "SIG", "data": ciphertext}
            )
            out = self.iface._post_request(access, "http://api/endpoint", {"a": 1})
            self.assertEqual(out["data"], decrypted)

    def test_get_request_decrypts_when_signature_and_data(self):
        """_get_request should transparently decrypt V2 payloads."""
        access = {
            "access_token": "tok",
            "username": "user-key",
            "password": "pass-secret",
        }
        decrypted = {"results": [{"id": 8}]}
        ciphertext = _aes_cbc_encrypt_base64(
            decrypted, access["username"], access["password"]
        )

        with patch("requests.get") as mget:
            mget.return_value = FakeResponse(
                json_obj={"signature": "SIG", "data": ciphertext}
            )
            out = self.iface._get_request(access, "http://api/endpoint", {"a": 1})
            self.assertEqual(out["data"], decrypted)

    # ---------------------------
    # Remote POST helper
    # ---------------------------

    def test_post_request_remote_unwraps_result(self):
        """type='json' routes wrap payload in {'result': ...}; method should unwrap."""
        with patch("requests.post") as mpost:
            mpost.return_value = FakeResponse(
                json_obj={"result": {"ok": True, "signature": "S"}}
            )
            out = self.iface._post_request_remote("http://remote/route", {"p": 1})
            self.assertEqual(out, {"ok": True, "signature": "S"})

    # ---------------------------
    # Account selection
    # ---------------------------

    def test_set_access_account_matches_iban(self):
        """Should set internal account ID when IBAN matches."""
        access = {"access_token": "tok", "username": "u", "password": "p"}
        payload = {
            "data": [
                {"id": 123, "cuentaCompleta": "ES12 3456 7890 1234 5678 9012"},
                {"id": 999, "cuentaCompleta": "ES00 0000 0000 0000 0000 0000"},
            ]
        }
        with patch("requests.get") as mget:
            mget.return_value = FakeResponse(json_obj=payload)
            self.iface._set_access_account(access, "ES1234567890123456789012")
            self.assertEqual(access["bankinplay_account"], 123)

    def test_set_access_account_not_found_raises(self):
        """If IBAN cannot be found in provider payload, raise a clear error."""
        access = {"access_token": "tok", "username": "u", "password": "p"}
        with patch("requests.get") as mget:
            mget.return_value = FakeResponse(json_obj={"data": []})
            with self.assertRaises(UserError):
                self.iface._set_access_account(access, "ES0012345678901234567890")
