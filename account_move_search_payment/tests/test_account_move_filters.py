# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestAccountMoveFilters(TransactionCase):
    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()

    def test_search_view_contains_paid_filter(self):
        view = self.env.ref(
            "account_move_search_payment.view_account_move_filter_inherit_paid_unpaid"
        )
        arch = view.arch_db or ""
        self.assertIn('name="filter_paid"', arch)
        self.assertIn("('payment_state', '=', 'paid')", arch)

    def test_search_view_contains_not_paid_filter(self):
        view = self.env.ref(
            "account_move_search_payment.view_account_move_filter_inherit_paid_unpaid"
        )
        arch = view.arch_db or ""
        self.assertIn('name="filter_not_paid"', arch)
        self.assertIn(
            "('payment_state', 'in', ('not_paid', 'partial', 'in_payment'))", arch
        )

    def test_search_account_invoice_filter_view_contains_paid_filter(self):
        view = self.env.ref(
            "account_move_search_payment."
            "view_account_invoice_filter_inherit_paid_unpaid"
        )
        arch = view.arch_db or ""
        self.assertIn('name="filter_paid"', arch)
        self.assertIn("('payment_state', '=', 'paid')", arch)

    def test_search_account_invoice_filter_view_contains_not_paid_filter(self):
        view = self.env.ref(
            "account_move_search_payment."
            "view_account_invoice_filter_inherit_paid_unpaid"
        )
        arch = view.arch_db or ""
        self.assertIn('name="filter_not_paid"', arch)
        self.assertIn(
            "('payment_state', 'in', ('not_paid', 'partial', 'in_payment'))", arch
        )
