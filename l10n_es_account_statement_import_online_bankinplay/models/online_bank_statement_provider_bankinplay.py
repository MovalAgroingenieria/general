# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
import logging
import re
from datetime import datetime
from dateutil.relativedelta import MO, relativedelta

import pytz

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class OnlineBankStatementProviderBankinplay(models.Model):
    _inherit = 'online.bank.statement.provider'

    bankinplay_date_field = fields.Selection(
        [
            ('operation_date', 'Operation Date'),
            ('value_date', 'Value Date'),
        ],
        string='Bankinplay Date Field',
        required=True,
        default='operation_date',
        help='Select the Bankinplay date field that will be used for '
        'the Odoo bank statement line date.',
    )

    bankinplay_delay_days = fields.Integer(
        string='Delay Days',
        required=True,
        default=0,
    )

    bankinplay_end_point_type = fields.Selection(
        [
            ('same_endpoint', 'Same Endpoint'),
            ('remote_endpoint', 'Remote Endpoint'),
        ],
        string='Bankinplay End Point',
        required=True,
        default='same_endpoint',
    )

    bankinplay_end_point = fields.Char(
        string='Bankinplay endpoint',
        help='Where callback webhook is gonna be setted, just in case don\'t. '
        'want to use the default controller functions',
    )

    @api.model
    def _get_available_services(self):
        '''Each provider model must register its service.'''
        return super()._get_available_services() + [
            ('bankinplay', 'BankInPlay.com'),
        ]

    def _get_statement_date_since(self, date):
        self.ensure_one()
        date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date = date - relativedelta(days=self.bankinplay_delay_days)
        if self.statement_creation_mode == "daily":
            return date
        elif self.statement_creation_mode == "weekly":
            return date + relativedelta(weekday=MO(-1))
        elif self.statement_creation_mode == "monthly":
            return date.replace(day=1)

    def _obtain_statement_data(self, date_since, date_until):
        '''Check wether called for bankinplay servide, otherwise pass the
           buck.'''
        self.ensure_one()
        if self.service != 'bankinplay':  # pragma: no cover
            return super()._obtain_statement_data(
                date_since,
                date_until,
            )
        return self._bankinplay_obtain_statement_data(date_since, date_until)

    def _bankinplay_obtain_statement_data(self, date_since, date_until):
        '''Create Callbacks to being processed afterwards.'''
        self.ensure_one()
        _logger.debug(
            _('Bankinplay obtain statement data for journal %s from %s to %s'),
            self.journal_id.name,
            date_since,
            date_until,
        )
        response_data = self._bankinplay_retrieve_data(date_since, date_until)
        return [], response_data

    def _create_or_update_statement_bankinplay(
        self, data, statement_date_since, statement_date_until
    ):
        """Create or update bank statement with the data retrieved from
           provider."""
        self.ensure_one()
        repost_statement = False
        AccountBankStatement = self.env["account.bank.statement"]
        is_scheduled = self.env.context.get("scheduled")
        if is_scheduled:
            AccountBankStatement = AccountBankStatement.with_context(
                tracking_disable=True,
            )
        if not data:
            data = ([], {})
        if not data[0] and not data[1] and not self.allow_empty_statements:
            return
        lines_data, statement_values = data
        if not lines_data:
            lines_data = []
        if not statement_values:
            statement_values = {}
        statement_date = self._get_statement_date(
            statement_date_since,
            statement_date_until,
        )
        statement = AccountBankStatement.search(
            [
                ("journal_id", "=", self.journal_id.id),
                ("date", "=", statement_date),
            ],
            limit=1,
        )
        if not statement:
            statement_values.update(
                {
                    "name": "%s/%s"
                    % (self.journal_id.code, statement_date.strftime(
                        "%Y-%m-%d")),
                    "journal_id": self.journal_id.id,
                    "date": statement_date,
                }
            )
            statement = AccountBankStatement.with_context(
                journal_id=self.journal_id.id,
            ).create(
                # NOTE: This is needed since create() alters values
                statement_values.copy()
            )
        # If posted but not lines reconciled, try to add new data
        elif (statement.state == 'posted' and len(statement.line_ids.filtered(
                lambda x: x.is_reconciled)) < 1):
            statement.button_reopen()
            repost_statement = True
        filtered_lines = self._get_statement_filtered_lines(
            lines_data, statement_values, statement_date_since,
            statement_date_until
        )
        statement_values.update(
            {"line_ids": [[0, False, line] for line in filtered_lines]}
        )
        if "balance_start" in statement_values:
            statement_values["balance_start"] = float(
                statement_values["balance_start"])
        if "balance_end_real" in statement_values:
            statement_values["balance_end_real"] = float(
                statement_values["balance_end_real"]
            )
        statement.write(statement_values)
        if (repost_statement):
            statement.button_post()

    def _bankinplay_update_statement_data_after_callback(
            self, bank_statement, data):
        '''Translate information from Bankinplay to Odoo bank statement
           lines.'''
        self.ensure_one()
        if (self.bankinplay_end_point_type == 'remote_endpoint'):
            # Already decoded
            all_transactions = self.\
                _bankinplay_get_transactions_from_data_remote(data)
        else:
            all_transactions = self._bankinplay_get_transactions_from_data(
                data)
        if (not all_transactions or len(all_transactions) < 1):
            message_to_user = _(
                'There is no transactions from bankinplay, original message:')
            message_to_user += json.dumps(data)
            bank_statement.message_post(
                body=message_to_user
            )
        self._create_or_update_statement_bankinplay(
            (all_transactions, {}), bank_statement.bankinplay_date_since,
            bank_statement.bankinplay_date_until)
        bank_statement.balance_end_real = bank_statement.balance_end

    def _bankinplay_retrieve_data(self, date_since, date_until):
        '''Fill buffer with data from Bankinplay.

        Register a method for retrieval of transactions which will be processed
        later by the callback action by adding the statement lines.
        '''
        response_data = {}
        interface_model = self.env['bankinplay.interface']
        if (self.bankinplay_end_point_type == 'same_endpoint'):
            access_data = interface_model._login(self.username, self.password)
            interface_model._set_access_account(
                access_data, self.account_number)
            response_data = interface_model._set_close_movements_callback(
                access_data, date_since, date_until)
        else:
            response_data = interface_model.\
                _set_close_movements_callback_remote_endpoint(
                    date_since, date_until, self.bankinplay_end_point,
                    self.account_number)
        return response_data

    def _bankinplay_get_transactions_from_data(self, data):
        '''Translate information from Bankinplay to statement line vals.'''
        interface_model = self.env['bankinplay.interface']
        access_data = interface_model._login(self.username, self.password)
        transactions_decrypted = interface_model._decrypt_bankinplay_data(
            data, access_data['username'], access_data['password']).get(
            'results', [])
        sequence = 0
        all_transactions = []
        for transaction_decrypted in transactions_decrypted:
            transaction_line = self._bankinplay_get_transaction_vals(
                transaction_decrypted, sequence)
            all_transactions.append(transaction_line)
            sequence += 1
        return all_transactions

    def _bankinplay_get_transactions_from_data_remote(self, data):
        '''Translate information from Bankinplay to statement line vals.'''
        transactions_decrypted = data.get('results', [])
        sequence = 0
        all_transactions = []
        for transaction_decrypted in transactions_decrypted:
            transaction_line = self._bankinplay_get_transaction_vals(
                transaction_decrypted, sequence)
            all_transactions.append(transaction_line)
            sequence += 1
        return all_transactions

    def _bankinplay_get_transaction_vals(self, transaction, sequence):
        '''Translate information from Bankinplay to statement line vals.'''
        date = self._bankinplay_get_transaction_datetime(transaction)
        ref = transaction.get('descripcion')
        amount = transaction.get('importeAbsoluto', 0)
        amount_multiplier = transaction.get('signo', 'Cobro')
        if (amount_multiplier != 'Cobro'):
            amount *= -1
        vals_line = {
            'sequence': sequence,
            'date': date,
            'ref': re.sub(' +', ' ', ref) or '/',
            'unique_import_id': str(transaction['id']),
            'amount': amount,
            'raw_data': json.dumps(transaction),
        }
        return vals_line

    def _bankinplay_get_transaction_datetime(self, transaction):
        '''Get execution datetime for a transaction.

        Odoo often names variables containing date and time just xxx_date or
        date_xxx. We try to avoid this misleading naming by using datetime as
        much for variables and fields of type datetime.
        '''
        if self.bankinplay_date_field == 'value_date':
            datetime_str = transaction.get('fechaValor')
        else:
            datetime_str = transaction.get('fechaOperacion')
        return self._bankinplay_datetime_from_string(datetime_str)

    def _bankinplay_datetime_from_string(self, datetime_str):
        '''Dates in Bankinplay are expressed in UTC, so we need to convert them
        to supplied tz for proper classification.
        '''
        dt = datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%SZ')
        dt = dt.replace(tzinfo=pytz.utc).astimezone(
            pytz.timezone(self.tz or "utc"))
        return dt.replace(tzinfo=None)
