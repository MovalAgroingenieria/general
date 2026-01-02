# -*- coding: utf-8 -*-
# Copyright 2025-2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0.html).
# pylint: disable=protected-access

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import tagged, users

from .common import MockSmsWauSms


@tagged("post_install", "-at_install", "wausms")
class TestSmsWauSms(MockSmsWauSms):
    """Minimal WauSMS provider tests (stable, OCA-friendly)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_sms_wausms(cls.company_admin)

        mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            country_id=cls.env.ref("base.es").id,
            groups="base.group_user",
            login="employee",
        )

        cls.number_ok = cls.wausms_valid_phone_number

    @users("employee")
    def test_numbers_success(self):
        """202/207 accepted -> sms pending + to_delete."""
        for code in (202, 207):
            with self.subTest(code=code):
                with self.mock_sms_wausms_gateway(http_code=code):
                    body = "Send SMS to %s" % self.number_ok
                    composer = self.env["sms.composer"].create(
                        {
                            "body": body,
                            "composition_mode": "numbers",
                            "numbers": self.number_ok,
                        }
                    )
                    # Use public method or call action_send_sms
                    if hasattr(composer, "action_send_sms"):
                        composer.action_send_sms()
                    else:
                        # Fallback to protected method if public doesn't exist
                        composer._action_send_sms()

                    self.assertSMS(
                        self.env["res.partner"],
                        self.number_ok,
                        "pending",
                        content=body,
                        failure_type=False,
                        fields_values={"to_delete": True},
                    )

    @users("employee")
    def test_numbers_401_unregistered(self):
        """401 -> sms_acc."""
        with self.mock_sms_wausms_gateway(http_code=401):
            body = "Send SMS to %s" % self.number_ok
            composer = self.env["sms.composer"].create(
                {"body": body, "composition_mode": "numbers", "numbers": self.number_ok}
            )
            # Use public method or call action_send_sms
            if hasattr(composer, "action_send_sms"):
                composer.action_send_sms()
            else:
                # Fallback to protected method if public doesn't exist
                composer._action_send_sms()

            self.assertSMS(
                self.env["res.partner"],
                self.number_ok,
                "error",
                content=body,
                failure_type="sms_acc",
                fields_values={"to_delete": False},
            )

    @users("employee")
    def test_numbers_402_insufficient_credit(self):
        """402 -> sms_credit."""
        with self.mock_sms_wausms_gateway(http_code=402):
            body = "Send SMS to %s" % self.number_ok
            composer = self.env["sms.composer"].create(
                {"body": body, "composition_mode": "numbers", "numbers": self.number_ok}
            )
            # Use public method or call action_send_sms
            if hasattr(composer, "action_send_sms"):
                composer.action_send_sms()
            else:
                # Fallback to protected method if public doesn't exist
                composer._action_send_sms()

            self.assertSMS(
                self.env["res.partner"],
                self.number_ok,
                "error",
                content=body,
                failure_type="sms_credit",
                fields_values={"to_delete": False},
            )

    @users("employee")
    def test_numbers_500_server_error(self):
        """5xx -> sms_server."""
        with self.mock_sms_wausms_gateway(http_code=500):
            body = "Send SMS to %s" % self.number_ok
            composer = self.env["sms.composer"].create(
                {"body": body, "composition_mode": "numbers", "numbers": self.number_ok}
            )
            # Use public method or call action_send_sms
            if hasattr(composer, "action_send_sms"):
                composer.action_send_sms()
            else:
                # Fallback to protected method if public doesn't exist
                composer._action_send_sms()

            self.assertSMS(
                self.env["res.partner"],
                self.number_ok,
                "error",
                content=body,
                failure_type="sms_server",
                fields_values={"to_delete": False},
            )
