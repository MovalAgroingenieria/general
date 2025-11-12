# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# pylint: disable=protected-access
# pylint: disable=unused-argument

import json
from datetime import datetime
from typing import Any, Dict, Optional

import requests
from odoo import http
from odoo.http import request

REQUEST_TIMEOUT = 15  # seconds for outbound HTTP calls


class BankinplayCallbackController(http.Controller):
    """Controller for handling Bankinplay callbacks."""

    def _get_bankinplay_credentials(self) -> tuple:
        """Get Bankinplay API credentials from system parameters."""
        return (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "l10n_es_account_statement_import_online_bankinplay"
                ".bankinplay_integration_api_key"
            ),
            request.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "l10n_es_account_statement_import_online_bankinplay"
                ".bankinplay_integration_api_secret"
            ),
        )

    def _handle_local_statement_update(
        self, response_id: str, signature: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, str]]:
        """Handle callback for locally created statement."""
        import_statement = (
            request.env["account.bank.statement"]
            .sudo()
            .search(
                [
                    ("bankinplay_responseid", "=", response_id),
                    ("bankinplay_signature", "=", signature),
                ],
                limit=1,
            )
        )

        if import_statement:
            provider = import_statement.journal_id.online_bank_statement_provider_id
            provider._bankinplay_update_statement_data_after_callback(
                import_statement, data
            )
            return {"status": "ok", "message": "Statement updated."}
        return None

    def _handle_remote_forwarding(
        self, response_id: str, signature: str, callback_data: Dict[str, Any]
    ) -> Optional[Dict[str, str]]:
        """Handle callback forwarding to remote endpoint."""
        remote_response = (
            request.env["bankinplay.response"]
            .sudo()
            .search(
                [
                    ("bankinplay_responseid", "=", response_id),
                    ("bankinplay_signature", "=", signature),
                ],
                limit=1,
            )
        )

        if not remote_response:
            return None

        bankinplay_api_key, bankinplay_api_secret = self._get_bankinplay_credentials()
        interface_model = request.env["bankinplay.interface"].sudo()

        # Decrypt only the 'data' part; keep original envelope
        decrypted = interface_model._decrypt_bankinplay_data(
            callback_data.get("data"), bankinplay_api_key, bankinplay_api_secret
        )
        json_to_forward = dict(callback_data)
        json_to_forward["data"] = decrypted

        url = f"{remote_response.endpoint_return_url}/webhook/bankinplay_callback"
        try:
            requests.post(
                url,
                json=json_to_forward,
                headers={"Accept": "application/json"},
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as exc:
            return {"status": "error", "message": f"Forward failed: {exc}"}

        # Store the decrypted payload for traceability
        remote_response.bankinplay_response = json.dumps(json_to_forward)
        return {"status": "ok", "message": "Forwarded to remote endpoint."}

    @http.route(
        "/webhook/bankinplay_callback",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def handle_bankinplay_callback(self, **post_data):
        """Handle Bankinplay callbacks.

        Currently only supports the 'lectura_cierre' (close reading) event.
        Behavior:
          1) If there's a local account.bank.statement with matching response/signature,
             update it via the provider hook.
          2) Else, if we have a bankinplay.response record (meaning data belongs to a
             remote DB), decrypt payload and forward to that endpoint.
        """
        json_data = request.get_json_data() or {}

        # Minimal payload validation
        response_id = json_data.get("responseId")
        signature = json_data.get("signature")
        triggered_event = json_data.get("triggered_event")
        if not (response_id and signature and triggered_event):
            return {"status": "ignored", "message": "Missing required fields."}

        # Only handle close readings
        if triggered_event != "lectura_cierre":
            return {"status": "ignored", "message": "Event not handled."}

        # 1) Try to find an already created statement in this database
        local_result = self._handle_local_statement_update(
            response_id, signature, json_data.get("data", {})
        )
        if local_result:
            return local_result

        # 2) If not found locally, check if the response is
        # registered for remote forwarding
        remote_result = self._handle_remote_forwarding(
            response_id, signature, json_data
        )
        if remote_result:
            return remote_result

        # Nothing to do locally or remotely
        return {"status": "ignored", "message": "No local/remote match."}

    def _validate_remote_callback_params(self, params: Dict[str, Any]) -> tuple:
        """Validate and extract parameters for remote callback."""
        try:
            date_since = datetime.strptime(params["date_since"], "%d/%m/%Y")
            date_until = datetime.strptime(params["date_until"], "%d/%m/%Y")
            # Typical many2one value: [id, name]; we only need the ID
            bankinplay_account = params["bankinplay_account"][0]
            return_url = params["return_url"]
            return date_since, date_until, bankinplay_account, return_url
        except (KeyError, ValueError, TypeError, IndexError) as exc:
            raise ValueError(f"Invalid parameters: {exc}") from exc

    def _initiate_remote_close_reading(
        self,
        date_since: datetime,
        date_until: datetime,
        bankinplay_account: int,
        return_url: str,
    ) -> Dict[str, str]:
        """Initiate remote close reading process."""
        interface_model = request.env["bankinplay.interface"].sudo()
        bankinplay_api_key, bankinplay_api_secret = self._get_bankinplay_credentials()

        access_data = interface_model._login(bankinplay_api_key, bankinplay_api_secret)
        interface_model._set_access_account(access_data, bankinplay_account)
        response_data = interface_model._set_close_movements_callback(
            access_data, date_since, date_until
        )

        signature = response_data.get("bankinplay_signature")
        response_id = response_data.get("bankinplay_responseid")
        if not (signature and response_id):
            raise ValueError("Provider did not return signature/response_id.")

        request.env["bankinplay.response"].sudo().create(
            {
                "bankinplay_signature": signature,
                "bankinplay_responseid": response_id,
                "endpoint_return_url": return_url,
            }
        )

        return {"signature": signature, "response_id": response_id}

    @http.route(
        "/remote/bankinplay_callback",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def handle_remote_bankinplay_callback(self, **post_data):
        """Start a remote close-reading process and register where to callback.

        Expects JSON with:
          - date_since: 'dd/mm/YYYY'
          - date_until: 'dd/mm/YYYY'
          - bankinplay_account: [id, display_name] (standard many2one-like shape)
          - return_url: base URL where '/webhook/bankinplay_callback' exists
        Returns:
          - signature
          - response_id
        """
        params = request.get_json_data() or {}

        try:
            (date_since, date_until, bankinplay_account, return_url) = (
                self._validate_remote_callback_params(params)
            )

            result = self._initiate_remote_close_reading(
                date_since, date_until, bankinplay_account, return_url
            )
            return result

        except ValueError as exc:
            return {"status": "error", "message": str(exc)}
        except Exception as exc:  # pylint: disable=W0718
            # Log the unexpected error for debugging
            # Consider using a more specific exception if possible
            return {"status": "error", "message": f"Unexpected error: {str(exc)}"}
