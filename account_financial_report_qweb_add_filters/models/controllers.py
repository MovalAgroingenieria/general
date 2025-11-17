# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from io import BytesIO

import xlsxwriter
from odoo import _, http
from odoo.http import content_disposition, request


class ReportController(http.Controller):

    def get_group_by_header_and_field(self, group_by):
        group_by_map = {
            "product_id": _("Product"),
            "partner_id": _("Partner"),
            "journal_id": _("Journal"),
            "tag": _("Tag"),
            "analytic_account_id": _("Analytic Account"),
        }
        return group_by_map.get(group_by, _("N/A")), group_by

    @http.route(
        "/report/trial_balance_excel/<int:wizard_id>",
        type="http",
        auth="user",
        website=True,
    )
    def report_trial_balance_excel(self, wizard_id, **kw):
        wizard = (
            request.env["trial.balance.report.grouped.wizard"].sudo().browse(wizard_id)
        )
        if not wizard:
            return request.not_found()

        # Generar el archivo Excel
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet()

        # Definir formatos para el archivo Excel.
        bold_format = workbook.add_format({"bold": True})
        decimal_format = workbook.add_format({"num_format": "#,##0.00"})
        bold_decimal_format = workbook.add_format(
            {"bold": True, "num_format": "#,##0.00"}
        )

        headers = [_("Date From"), _("Date To"), _("Company")]
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, bold_format)

        row = 1
        worksheet.write(row, 0, str(wizard.date_from))
        worksheet.write(row, 1, str(wizard.date_to))
        worksheet.write(row, 2, wizard.company_id.name)
        row += 2
        if wizard.account_ids:
            worksheet.write(row, 0, _("Accounts:"), bold_format)
            row += 1
            row_count = 0
            for account_num, account in enumerate(wizard.account_ids):
                if account_num > 6:
                    if account_num == 7:
                        account_num -= 7
                    else:
                        account_num -= 7 * row_count
                        if account_num == 7:
                            account_num -= 7
                    if account_num == 0:
                        row_count += 1
                        row += 1
                worksheet.write(row, account_num, account.code)

        row += 2
        accounts = wizard.get_accounts()
        if accounts:
            line_headers = [
                _("Account"),
                _("Group By"),
                _("Initial Balance"),
                _("Debit"),
                _("Credit"),
                _("Period Balance"),
                _("Final Balance"),
            ]
            for col_num, header in enumerate(line_headers):
                worksheet.write(row, col_num, header, bold_format)
            row += 1
            for account in accounts:
                group_by_header, group_by_field = self.get_group_by_header_and_field(
                    account.user_type_id.group_by
                )

                # Escribir encabezados de las cuentas
                # header = [_('Account'), group_by_header, _('Initial Balance'),
                #           _('Debit'), _('Credit'), _('Period Balance'),
                #           _('Final Balance')]
                # line_headers = [_('Account'), group_by_header]

                items = wizard.get_item_ids(account, wizard.date_from, wizard.date_to)
                if items or not items and wizard.show_account_zero:
                    total_initial_balance = sum(
                        item["initial_balance"] for item in items
                    )
                    total_debit = sum(item["debit"] for item in items)
                    total_credit = sum(item["credit"] for item in items)
                    total_period_balance = sum(item["balance"] for item in items)
                    total_final_balance = sum(item["final_balance"] for item in items)
                    header_line = [
                        _("Account") + " - " + account.code,
                        group_by_header,
                        total_initial_balance,
                        total_debit,
                        total_credit,
                        total_period_balance,
                        total_final_balance,
                    ]
                    row += 2
                    for col_num, header in enumerate(header_line):
                        worksheet.write(row, col_num, header, bold_decimal_format)
                    # row += 2
                    # for col_num, header in enumerate(line_headers):
                    #     worksheet.write(row, col_num, header, bold_format)
                    row += 1

                    account_code_name = account.code + " - " + account.name
                    for item in items:
                        group_by_value = item.get(group_by_field)
                        if isinstance(group_by_value, tuple):
                            group_by_value = str(group_by_value[1])
                        worksheet.write(row, 0, account_code_name)
                        worksheet.write(row, 1, group_by_value or "N/A")
                        worksheet.write(
                            row, 2, item["initial_balance"] or 0, decimal_format
                        )
                        worksheet.write(row, 3, item["debit"] or 0, decimal_format)
                        worksheet.write(row, 4, item["credit"] or 0, decimal_format)
                        worksheet.write(row, 5, item["balance"] or 0, decimal_format)
                        worksheet.write(
                            row, 6, item["final_balance"] or 0, decimal_format
                        )
                        row += 1

        workbook.close()

        # Devolver el archivo Excel como respuesta
        excel_content = output.getvalue()
        output.close()

        return request.make_response(
            excel_content,
            headers=[
                (
                    "Content-Type",
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet",
                ),
                (
                    "Content-Disposition",
                    content_disposition("trial_balance_report.xlsx"),
                ),
            ],
        )
