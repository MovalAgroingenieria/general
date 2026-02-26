# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=invalid-name

from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TimesheetComplianceCase(TransactionCase):
    @classmethod
    def setUpClass(cls):  # noqa: N805
        super().setUpClass()

        cls._patchers = [
            patch(
                "odoo.addons.mail.models.mail_mail.MailMail.send",
                autospec=True,
                return_value=True,
            ),
            patch(
                "odoo.addons.mail.models.mail_template.MailTemplate.send_mail",
                autospec=True,
                return_value=True,
            ),
        ]
        for p in cls._patchers:
            p.start()

    @classmethod
    def tearDownClass(cls):  # noqa: N805
        for p in cls._patchers:
            p.stop()
        super().tearDownClass()
