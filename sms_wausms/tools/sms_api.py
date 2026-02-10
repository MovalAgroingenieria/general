# -*- coding: utf-8 -*-
# Copyright 2025-2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0.html).
# pylint: disable=too-many-locals
# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
# pylint: disable=too-many-return-statements
from __future__ import annotations

import base64
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import requests
from odoo.addons.sms.tools.sms_api import SmsApiBase

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WauSmsEndpoints:
    """Default WauSMS endpoints."""

    rest: str = "https://dashboard.wausms.com/Api/rest/message"
    get: str = "https://dashboard.wausms.com/Api/get/send.php"


class SmsApiWauSms(SmsApiBase):
    """WauSMS provider implementation for Odoo v18 SMS framework.

    Odoo contract:
      - _send_sms_batch(messages, delivery_reports_url=False) -> list[dict]
      - each dict: {"uuid": <uuid>, "state": <provider_state>, ...}
      - optional keys: "failure_reason", "wausms_response", "credit"

    Provider states must be IAP-like because Odoo core maps them to sms.sms.state
    and derives failure_type via PROVIDER_TO_SMS_FAILURE_TYPE.
    """

    ENDPOINTS = WauSmsEndpoints()
    REST_OK_HTTP_STATUSES = (202, 207)
    TIMEOUT_SECONDS = 10

    PROVIDER_TO_SMS_FAILURE_TYPE = SmsApiBase.PROVIDER_TO_SMS_FAILURE_TYPE | {
        "insufficient_credit": "sms_credit",
        "unregistered": "sms_acc",
        "wrong_number_format": "sms_number_format",
        "country_not_supported": "sms_country_not_supported",
        "server_error": "sms_server",
    }

    # -------------------------------------------------------------------------
    # Odoo API
    # -------------------------------------------------------------------------

    def _send_sms_batch(self, messages, delivery_reports_url=False):
        company = (self.company or self.env.company).sudo()
        # Use public method instead of protected access
        company.assert_wausms_config()

        msgs = messages or []
        service_url = (
            company.sms_wausms_service_url or ""
        ).strip() or self.ENDPOINTS.rest

        if self._is_rest_endpoint(service_url):
            return self._send_batch_rest(
                service_url=service_url,
                company=company,
                messages=msgs,
                delivery_reports_url=delivery_reports_url,
            )

        return self._send_batch_get(
            service_url=(service_url or "").strip() or self.ENDPOINTS.get,
            company=company,
            messages=msgs,
            delivery_reports_url=delivery_reports_url,
        )

    def _get_sms_api_error_messages(self):
        messages = super()._get_sms_api_error_messages()
        messages.update(
            {
                "unregistered": self.env._(
                    "Authentication failed (WauSMS account not recognized)."
                ),
                "insufficient_credit": self.env._("Insufficient credit."),
                "wrong_number_format": self.env._(
                    "Invalid recipient / wrong number format."
                ),
                "server_error": self.env._(
                    "Server error / bad request / "
                    "network error while contacting WauSMS."
                ),
            }
        )
        return messages

    # -------------------------------------------------------------------------
    # REST mode
    # -------------------------------------------------------------------------

    def _send_batch_rest(
        self,
        service_url: str,
        company,
        messages: List[Dict[str, Any]],
        delivery_reports_url: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Send batch using REST API."""
        session = requests.Session()
        headers = self._rest_headers(
            company.sms_wausms_api_user, company.sms_wausms_api_passwd
        )
        sender = (company.sms_wausms_sender or "").strip()

        results: List[Dict[str, Any]] = []
        for message in messages:
            # Extract message data
            body, number_uuid = self._extract_message_data(message)
            if not number_uuid:
                continue

            # Prepare payload
            payload = self._rest_payload(
                to_numbers=list(number_uuid.keys()),
                body=body,
                sender=sender,
                delivery_reports_url=delivery_reports_url,
            )

            # Send request
            try:
                response = session.post(
                    service_url,
                    headers=headers,
                    json=payload,
                    timeout=self.TIMEOUT_SECONDS,
                )
            except requests.exceptions.RequestException as exc:
                _logger.warning("WauSMS REST network error: %s", exc)
                results.extend(
                    self._results_error(
                        uuids=number_uuid.values(),
                        provider_state="server_error",
                        failure_reason=self.env._(
                            "Network error while contacting WauSMS."
                        ),
                        wausms_response=str(exc),
                    )
                )
                continue

            raw = (response.text or "").strip() or None

            if response.status_code in self.REST_OK_HTTP_STATUSES:
                data = self._safe_json(response)

                # Some implementations return a list per-recipient, others
                # return a dict like: {"result": "accepted"}
                if isinstance(data, list):
                    results.extend(self._map_rest_list_response(data, number_uuid, raw))
                else:
                    results.extend(
                        self._results_success(number_uuid.values(), wausms_response=raw)
                    )
                continue

            # Handle error
            err_desc, err_code = self._extract_rest_error(response)
            http_status = getattr(response, "status_code", None)
            provider_state = self._map_rest_http_to_provider_state(
                http_status, err_code
            )
            # Ensure 401 is always mapped to unregistered (sms_acc)
            if http_status == 401:
                provider_state = "unregistered"
            results.extend(
                self._results_error(
                    uuids=number_uuid.values(),
                    provider_state=provider_state,
                    failure_reason=err_desc,
                    wausms_response=raw,
                )
            )

        return results

    def _map_rest_list_response(
        self,
        data: List[Dict[str, Any]],
        number_uuid: Mapping[str, str],
        raw: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Map per-recipient REST responses to Odoo results.

        Expected list items:
          - {"to": "...", "accepted": true}
          - {"to": "...", "accepted": false, "error": {"code": <int>,
            "description": "..."}}
        """
        results: List[Dict[str, Any]] = []
        seen: set[str] = set()

        for entry in data:
            if not isinstance(entry, dict):
                continue

            to_number = entry.get("to")
            uuid = number_uuid.get(to_number)
            if not uuid:
                continue

            seen.add(uuid)

            if entry.get("accepted") is True:
                results.append(self._result_ok(uuid, wausms_response=raw))
                continue

            err = entry.get("error") if isinstance(entry.get("error"), dict) else {}
            code = err.get("code") if isinstance(err.get("code"), int) else None
            desc = err.get("description") or self.env._("WauSMS error.")
            provider_state = self._map_wausms_error_code_to_provider_state(code)

            results.append(
                self._result_error(
                    uuid,
                    provider_state=provider_state,
                    failure_reason=desc,
                    wausms_response=raw,
                )
            )

        missing = set(number_uuid.values()) - seen
        if missing:
            results.extend(
                self._results_error(
                    uuids=missing,
                    provider_state="server_error",
                    failure_reason=self.env._("Incomplete response from WauSMS."),
                    wausms_response=raw,
                )
            )

        return results

    def _rest_payload(
        self,
        to_numbers: Sequence[str],
        body: str,
        sender: str,
        delivery_reports_url: Optional[str],
    ) -> Dict[str, Any]:
        encoding = self._detect_encoding(body)
        parts = self._count_sms_parts(len(body or ""), encoding)

        payload: Dict[str, Any] = {
            "to": list(to_numbers),
            "text": body,
            "from": sender,
            "coding": encoding,
            "parts": parts,
        }
        if delivery_reports_url:
            payload["dlr-url"] = delivery_reports_url
        return payload

    def _rest_headers(self, user: str, passwd: str) -> Dict[str, str]:
        token = base64.b64encode(f"{user}:{passwd}".encode("utf-8")).decode("utf-8")
        return {
            "Authorization": f"Basic {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _extract_rest_error(
        self, response: requests.Response
    ) -> Tuple[str, Optional[int]]:
        data = self._safe_json(response)
        if isinstance(data, dict) and isinstance(data.get("error"), dict):
            err = data["error"]
            code = err.get("code") if isinstance(err.get("code"), int) else None
            desc = err.get("description") or self.env._("WauSMS error.")
            return desc, code

        text = (response.text or "").strip()
        return (text or self.env._("WauSMS error."), None)

    def _map_rest_http_to_provider_state(
        self, http_status: Optional[int], err_code: Optional[int]
    ) -> str:
        if http_status == 401:
            return "unregistered"
        if http_status == 402:
            return "insufficient_credit"
        if http_status == 400:
            return self._map_wausms_error_code_to_provider_state(err_code)
        return "server_error"

    def _map_wausms_error_code_to_provider_state(self, code: Optional[int]) -> str:
        if code == 111:
            return "insufficient_credit"
        if code == 103:
            return "unregistered"
        if code == 102:
            return "wrong_number_format"
        return "server_error"

    # -------------------------------------------------------------------------
    # GET mode (legacy)
    # -------------------------------------------------------------------------

    def _send_batch_get(
        self,
        service_url: str,
        company,
        messages: List[Dict[str, Any]],
        delivery_reports_url: Optional[str],
    ) -> List[Dict[str, Any]]:
        session = requests.Session()
        username = company.sms_wausms_api_user
        password = company.sms_wausms_api_passwd
        sender = (company.sms_wausms_sender or "").strip()

        results: List[Dict[str, Any]] = []
        for message in messages:
            body = message.get("content") or ""
            for item in message.get("numbers") or []:
                uuid = item.get("uuid")
                to_number = item.get("number")
                if not uuid or not to_number:
                    continue

                results.append(
                    self._send_one_get(
                        session=session,
                        service_url=service_url,
                        username=username,
                        password=password,
                        sender=sender,
                        to_number=str(to_number),
                        body=body,
                        delivery_reports_url=delivery_reports_url,
                        uuid=str(uuid),
                    )
                )

        return results

    def _send_one_get(
        self,
        session: requests.Session,
        service_url: str,
        username: str,
        password: str,
        sender: str,
        to_number: str,
        body: str,
        delivery_reports_url: Optional[str],
        uuid: str,
    ) -> Dict[str, Any]:
        """Send single SMS using GET API."""
        encoding = self._detect_encoding(body)
        parts = self._count_sms_parts(len(body or ""), encoding)

        params: Dict[str, Any] = {
            "username": username,
            "password": password,
            "to": to_number,
            "text": body,
            "from": sender,
            "coding": encoding,
            "parts": parts,
        }
        if delivery_reports_url:
            params["dlr-mask"] = 8
            params["dlr-url"] = delivery_reports_url

        try:
            response = session.get(
                service_url, params=params, timeout=self.TIMEOUT_SECONDS
            )
        except requests.exceptions.RequestException as exc:
            _logger.warning("WauSMS GET network error: %s", exc)
            return self._result_error(
                uuid,
                provider_state="server_error",
                failure_reason=self.env._("Network error while contacting WauSMS."),
                wausms_response=str(exc),
            )

        raw = (response.text or "").strip() or None
        ok, provider_state, failure_reason = self._parse_get_response(raw)
        # When gateway returns JSON (e.g. REST-style mock), map HTTP status
        if not ok and provider_state == "server_error":
            http_status = getattr(response, "status_code", None)
            if http_status == 401:
                provider_state = "unregistered"
                failure_reason = failure_reason or self.env._(
                    "Authentication failed (WauSMS account not recognized)."
                )
            elif http_status == 402:
                provider_state = "insufficient_credit"

        if ok:
            return self._result_ok(uuid, wausms_response=raw)

        return self._result_error(
            uuid, provider_state, failure_reason, wausms_response=raw
        )

    def _parse_get_response(self, raw: Optional[str]) -> Tuple[bool, str, str]:
        """Parse legacy GET response: '<code>: <message>'."""
        if not raw:
            return False, "server_error", self.env._("Empty response from WauSMS.")

        match = re.match(r"^\s*(\d+)\s*:\s*(.*)$", raw)
        if not match:
            return False, "server_error", self.env._("Unexpected response from WauSMS.")

        code = int(match.group(1))
        msg = (match.group(2) or "").strip() or self.env._("WauSMS error.")

        # IMPORTANT: return 'pending' so Odoo treats it as accepted (and sets
        # to_delete)
        if code == 0:
            return True, "pending", ""
        if code == 103:
            return False, "unregistered", msg
        if code == 111:
            return False, "insufficient_credit", msg
        if code == 102:
            return False, "wrong_number_format", msg

        return False, "server_error", msg

    # -------------------------------------------------------------------------
    # Shared helpers
    # -------------------------------------------------------------------------

    def _is_rest_endpoint(self, url: str) -> bool:
        """Detect REST endpoint (case-insensitive)."""
        clean = (url or "").strip().rstrip("/")
        lower = clean.lower()
        return "/api/rest/" in lower or lower.endswith("/api/rest/message")

    def _safe_json(self, response: requests.Response) -> Any:
        try:
            return response.json()
        except ValueError:  # More specific exception
            return None

    def _extract_message_data(
        self, message: Mapping[str, Any]
    ) -> Tuple[str, Dict[str, str]]:
        """Extract message content and build a number->uuid mapping."""
        body = message.get("content") or ""
        numbers = message.get("numbers") or []

        number_uuid: Dict[str, str] = {}
        for item in numbers:
            if not isinstance(item, dict):
                continue
            number = item.get("number")
            uuid = item.get("uuid")
            if number and uuid:
                number_uuid[str(number)] = str(uuid)

        return body, number_uuid

    def _results_success(
        self, uuids: Iterable[str], wausms_response: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return [
            self._result_ok(uuid, wausms_response=wausms_response) for uuid in uuids
        ]

    def _results_error(
        self,
        uuids: Iterable[str],
        provider_state: str,
        failure_reason: Optional[str],
        wausms_response: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return [
            self._result_error(
                uuid,
                provider_state=provider_state,
                failure_reason=failure_reason,
                wausms_response=wausms_response,
            )
            for uuid in uuids
        ]

    def _result_ok(
        self, uuid: str, wausms_response: Optional[str] = None
    ) -> Dict[str, Any]:
        values: Dict[str, Any] = {"uuid": uuid, "state": "success"}
        if wausms_response is not None:
            values["wausms_response"] = wausms_response
        return values

    def _result_error(
        self,
        uuid: str,
        provider_state: str,
        failure_reason: Optional[str],
        wausms_response: Optional[str] = None,
    ) -> Dict[str, Any]:
        values: Dict[str, Any] = {
            "uuid": uuid,
            "state": provider_state,
            "failure_reason": failure_reason or self.env._("WauSMS error."),
        }
        if wausms_response is not None:
            values["wausms_response"] = wausms_response
        return values

    # -------------------------------------------------------------------------
    # Encoding helpers
    # -------------------------------------------------------------------------

    _GSM7_RE = re.compile(
        r"^[@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ "
        r"!\"#¤%&'()*+,-./0123456789:;<=>?¡"
        r"ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿"
        r"abcdefghijklmnopqrstuvwxyzäöñüà]*$"
    )

    def _detect_encoding(self, content: str) -> str:
        """Return WauSMS coding: 'gsm' or 'utf-16'."""
        return "gsm" if self._GSM7_RE.match(str(content or "")) else "utf-16"

    def _count_sms_parts(self, num_char: int, encoding: str) -> int:
        """Return number of SMS parts based on encoding."""
        if not num_char:
            return 0
        if encoding == "utf-16":
            return 1 if num_char <= 70 else -(-num_char // 67)
        return 1 if num_char <= 160 else -(-num_char // 153)
