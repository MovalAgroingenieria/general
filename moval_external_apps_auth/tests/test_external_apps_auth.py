# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestExternalAppsAuth(TransactionCase):

    def setUp(self):
        super(TestExternalAppsAuth, self).setUp()
        self.app = self.env["moval.external.app"].create({
            "name": "Auth Test",
            "slug": "auth-test",
            "app_url": "https://example.invalid/path?existing=yes",
            "keycloak_client_id": "auth-test",
            "keycloak_client_secret": "client-secret",
            "app_shared_secret": "shared-secret",
        })

    def test_ticket_is_single_use_and_bound_to_app(self):
        tickets = self.env["moval.service.ticket"].sudo()
        ticket = tickets.issue("jwt-value", "admin", self.app.slug)

        self.assertFalse(tickets.redeem(ticket, "another-app"))
        payload = tickets.redeem(ticket, self.app.slug)
        self.assertEqual(payload["jwt"], "jwt-value")
        self.assertFalse(tickets.redeem(ticket, self.app.slug))

    def test_query_parameters_are_encoded(self):
        mixin = self.env["moval.auth.mixin"]
        url = mixin._append_query_params(
            self.app.app_url,
            [("ticket", "a+b&c"), ("label", "área de riego")])

        self.assertIn("existing=yes", url)
        self.assertIn("ticket=a%2Bb%26c", url)
        self.assertNotIn("a+b&c", url)

    def test_regular_user_cannot_read_app_secrets(self):
        user = self.env["res.users"].create({
            "name": "External App Employee",
            "login": "external-app-employee",
            "partner_id": self.env.user.partner_id.id,
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
        })

        with self.assertRaises(AccessError):
            self.app.sudo(user).read(["app_shared_secret"])
