# -*- coding: utf-8 -*-
# Copyright 2025-2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0.html).
# pylint: disable=protected-access

import json
from contextlib import contextmanager

from odoo.addons.sms.tests.common import SMSCase
from odoo.tests.common import TransactionCase
from requests import Response


class MockSmsWauSmsApi(SMSCase):
    """Mock WauSMS HTTP gateway for tests."""

    _WAUSMS_ENDPOINT = "https://dashboard.wausms.com/api/rest/message"

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.user_admin = cls.env.ref("base.user_admin")
        cls.company_admin = cls.user_admin.company_id

        cls.wausms_valid_phone_number = "+34600111222"
        cls.wausms_invalid_phone_number = "+34600000000"

        cls._mock_http_code = 202
        cls._mock_error_in_body = None  # None => auto based on http_code
        cls._mock_error_description = "Bad request"
        cls._mock_ok_json = {"result": "accepted"}

    @classmethod
    def _setup_sms_wausms(cls, company):
        company.sudo().write(
            {
                "sms_provider": "wausms",
                "sms_wausms_service_url": cls._WAUSMS_ENDPOINT,
                "sms_wausms_api_user": "user",
                "sms_wausms_api_passwd": "passwd",
                "sms_wausms_sender": "MOVAL",
            }
        )

    @classmethod
    def _update_mock(cls, http_code=None, error_in_body=None, error_description=None):
        if http_code is not None:
            cls._mock_http_code = http_code
        if error_in_body is not None:
            cls._mock_error_in_body = error_in_body
        if error_description is not None:
            cls._mock_error_description = error_description

    @classmethod
    def _request_handler(cls, session, request, **kwargs):
        url = request.url or ""
        if url.startswith(cls._WAUSMS_ENDPOINT):
            response = Response()
            response.status_code = cls._mock_http_code

            # Auto: error body for non-OK HTTP statuses
            if cls._mock_error_in_body is None:
                error_in_body = cls._mock_http_code not in (202, 207)
            else:
                error_in_body = bool(cls._mock_error_in_body)

            if error_in_body:
                payload = {"error": {"description": cls._mock_error_description}}
            else:
                payload = cls._mock_ok_json

            response._content = json.dumps(payload).encode("utf-8")
            response.headers["Content-Type"] = "application/json"
            response.json = lambda: json.loads(response.content.decode("utf-8"))
            return response

        return super()._request_handler(session, request, **kwargs)

    @contextmanager
    def mock_sms_wausms_gateway(
        self, http_code=202, error_in_body=None, error_description="Bad request"
    ):
        """Enable WauSMS mocked gateway (wraps SMSCase.mockSMSGateway())."""
        self._clear_sms_sent()
        self._update_mock(
            http_code=http_code,
            error_in_body=error_in_body,
            error_description=error_description,
        )
        with self.mockSMSGateway():
            yield


class MockSmsWauSms(MockSmsWauSmsApi, TransactionCase):
    """Base test case for WauSMS tests."""
