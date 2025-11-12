# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# pylint: disable=protected-access
# pylint: disable=no-else-return
import json
import logging
import re
from datetime import datetime

import pytz
from dateutil.relativedelta import MO, relativedelta
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class OnlineBankStatementProviderBankinplay(models.Model):
    _inherit = "online.bank.statement.provider"

    # --- BankInPlay configuration -------------------------------------------

    # Which Bankinplay date field is mapped to the Odoo statement line date
    bankinplay_date_field = fields.Selection(
        [
            ("operation_date", "Operation Date"),
            ("value_date", "Value Date"),
        ],
        required=True,
        default="operation_date",
        help="Select the Bankinplay date field that will be used as the "
        "statement line date in Odoo.",
    )

    # Days of delay to apply when computing the statement period
    bankinplay_delay_days = fields.Integer(
        string="Delay Days",
        required=True,
        default=0,
        help="Shift the date range this many days back to account for provider delays.",
    )

    # Whether callbacks will be handled by this DB or a remote one
    bankinplay_end_point_type = fields.Selection(
        [
            ("same_endpoint", "Same Endpoint"),
            ("remote_endpoint", "Remote Endpoint"),
        ],
        string="Bankinplay End Point",
        required=True,
        default="same_endpoint",
        help="Choose whether callbacks will be handled by this Odoo database "
        "or a remote one.",
    )

    # Base URL of the remote endpoint (only used when 'remote_endpoint')
    bankinplay_end_point = fields.Char(
        string="Bankinplay Endpoint",
        help="Base URL where the webhook will be registered if using a "
        "remote endpoint.",
    )

    # --- Service registration ------------------------------------------------

    @api.model
    def _get_available_services(self):
        """Register BankInPlay as an available provider."""
        return super()._get_available_services() + [("bankinplay", "BankInPlay.com")]

    # --- Date helpers --------------------------------------------------------

    def _get_statement_date_since(self, date):
        """Compute the start bound (00:00) minus the configured delay.

        Matches v18 base semantics (daily/weekly/monthly “bucket” start),
        but applies bankinplay_delay_days before bucketing.
        """
        self.ensure_one()
        date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date = date - relativedelta(days=self.bankinplay_delay_days)
        if self.statement_creation_mode == "daily":
            return date
        elif self.statement_creation_mode == "weekly":
            # Monday of the previous week relative to (delayed) date
            return date + relativedelta(weekday=MO(-1))
        elif self.statement_creation_mode == "monthly":
            return date.replace(day=1)
        return date  # fallback

    # --- Entry point ---------------------------------------------------------

    def _obtain_statement_data(self, date_since, date_until):
        """Dispatch per service; only handle 'bankinplay' here."""
        self.ensure_one()
        if self.service != "bankinplay":  # pragma: no cover
            return super()._obtain_statement_data(date_since, date_until)
        return self._bankinplay_obtain_statement_data(date_since, date_until)

    def _bankinplay_obtain_statement_data(self, date_since, date_until):
        """Schedule BankInPlay callbacks; statement lines arrive via webhook."""
        self.ensure_one()
        _logger.debug(
            "Bankinplay obtain statement data for journal %s from %s to %s",
            self.journal_id.name,
            date_since,
            date_until,
        )
        response_data = self._bankinplay_retrieve_data(date_since, date_until)
        # Base contract: (lines, extra_values). We return no lines now.
        return [], response_data

    # --- Statement creation/update (BankInPlay path) -------------------------

    def _create_or_update_statement_bankinplay(
        self, data, statement_date_since, statement_date_until
    ):
        """Create or update a bank statement with BankInPlay data
        (Odoo v18 compatible).

        - Does not call `_get_statement_date` (no longer exists in v18).
        - No `state` logic such as reopen/post — statements in v18 do
         not have that field.
        - Identifies statements by their `name` (computed via
        `make_statement_name()`).
        - Reuses base provider helpers for line filtering and balance calculation.
        """
        self.ensure_one()

        # Normalize payload structure
        if not data:
            data = ([], {})
        lines_data, statement_values = data
        lines_data = lines_data or []
        statement_values = (statement_values or {}).copy()

        # Compute statement name based on the period start date (v18 style)
        statement_values["name"] = self.make_statement_name(statement_date_since)

        # Filter transaction lines within the given date range
        filtered_lines = self._get_statement_filtered_lines(
            lines_data,
            statement_values,
            statement_date_since,
            statement_date_until,
        )
        if not filtered_lines:
            # Nothing to create or update
            return self.env["account.bank.statement"]

        # Attach new statement lines to the values dictionary
        statement_values["line_ids"] = [[0, False, line] for line in filtered_lines]

        # Compute opening/closing balances using the base helper
        self._update_statement_balances(statement_values)

        # Create or update the statement (v18 identifies by name + journal)
        statement = self._statement_create_or_write(statement_values)
        return statement

    # --- Callback post-processing -------------------------------------------

    def _bankinplay_update_statement_data_after_callback(self, bank_statement, data):
        """Translate BankInPlay payload into Odoo statement lines and write them."""
        self.ensure_one()
        if self.bankinplay_end_point_type == "remote_endpoint":
            # Already decrypted upstream
            all_transactions = self._bankinplay_get_transactions_from_data_remote(data)
        else:
            all_transactions = self._bankinplay_get_transactions_from_data(data)

        if not all_transactions:
            msg = self.env._(
                "There are no transactions from Bankinplay. Original message: "
            )
            bank_statement.message_post(body=msg + json.dumps(data))
            return

        self._create_or_update_statement_bankinplay(
            (all_transactions, {}),
            bank_statement.bankinplay_date_since,
            bank_statement.bankinplay_date_until,
        )
        # Align end balance after insertion
        bank_statement.balance_end_real = bank_statement.balance_end

    # --- Provider interaction ------------------------------------------------

    def _bankinplay_retrieve_data(self, date_since, date_until):
        """Request BankInPlay to prepare data (local or remote endpoint)."""
        interface_model = self.env["bankinplay.interface"]
        if self.bankinplay_end_point_type == "same_endpoint":
            access_data = interface_model._login(self.username, self.password)
            interface_model._set_access_account(access_data, self.account_number)
            return interface_model._set_close_movements_callback(
                access_data, date_since, date_until
            )
        else:
            return interface_model._set_close_movements_callback_remote_endpoint(
                date_since, date_until, self.bankinplay_end_point, self.account_number
            )

    # --- Data translation ----------------------------------------------------

    def _bankinplay_get_transactions_from_data(self, data):
        """Decrypt payload with provider credentials and build line values."""
        interface_model = self.env["bankinplay.interface"]
        access_data = interface_model._login(self.username, self.password)
        decrypted = interface_model._decrypt_bankinplay_data(
            data, access_data["username"], access_data["password"]
        )
        transactions = decrypted.get("results", []) or []
        return [
            self._bankinplay_get_transaction_vals(tx, i)
            for i, tx in enumerate(transactions)
        ]

    def _bankinplay_get_transactions_from_data_remote(self, data):
        """Use already-decrypted remote payload to build line values."""
        transactions = data.get("results", []) or []
        return [
            self._bankinplay_get_transaction_vals(tx, i)
            for i, tx in enumerate(transactions)
        ]

    def _bankinplay_get_transaction_vals(self, transaction, sequence):
        """Map one BankInPlay transaction to account.bank.statement.line vals."""
        date = self._bankinplay_get_transaction_datetime(transaction)
        ref = (transaction.get("descripcion") or "/").strip()
        ref = re.sub(r"\s+", " ", ref) or "/"

        amount = float(transaction.get("importeAbsoluto", 0) or 0.0)
        # Bankinplay uses 'signo' == 'Cobro' for incoming; anything else => outgoing
        if transaction.get("signo", "Cobro") != "Cobro":
            amount *= -1

        return {
            "sequence": sequence,
            "date": date,
            "ref": ref,
            "unique_import_id": str(transaction.get("id")),
            "amount": amount,
            "raw_data": json.dumps(transaction),
        }

    # --- Date parsing --------------------------------------------------------

    def _bankinplay_get_transaction_datetime(self, transaction):
        """Choose operation/value timestamp from the transaction based on settings."""
        if self.bankinplay_date_field == "value_date":
            datetime_str = transaction.get("fechaValor")
        else:
            datetime_str = transaction.get("fechaOperacion")
        return self._bankinplay_datetime_from_string(datetime_str)

    def _bankinplay_datetime_from_string(self, datetime_str):
        """BankInPlay timestamps are UTC (Zulu). Convert to
        provider TZ and return naive."""
        if not datetime_str:
            # fallback to now to avoid crashes if upstream payload is missing the date
            return fields.Datetime.now()
        dt = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%SZ")
        provider_tz = self.tz or self.env.user.tz or "UTC"
        dt = dt.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(provider_tz))
        # Odoo stores naive datetimes; base API expects naive here
        return dt.replace(tzinfo=None)
