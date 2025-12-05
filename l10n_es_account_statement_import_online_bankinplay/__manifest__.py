# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Online Bank Statements: BankInPlay.com",
    "summary": "Add new functionality that allows the import of account bank \
                statement and statement lines from BankInPlay API services.",
    "version": "18.0.1.0.0",
    "category": "Localization",
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        "account_statement_import_online",
    ],
    "data": [
      #  "data/ir_cron_delete_old_responses.xml",
      #  "views/online_bank_statement_provider.xml",
      #  "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
