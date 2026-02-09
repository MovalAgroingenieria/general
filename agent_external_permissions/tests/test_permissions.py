# Copyright 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAgentExternalPermissions(TransactionCase):
    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.company = cls.env.company

        # Groups
        cls.group_external = cls.env.ref(
            "agent_external_permissions.group_external_agent"
        )
        cls.group_internal = cls.env.ref(
            "agent_external_permissions.group_internal_salesperson"
        )

        # Sale groups can vary by build
        cls.group_sale_user = cls.env.ref(
            "sales_team.group_sale_salesman", raise_if_not_found=False
        ) or cls.env.ref("sale.group_sale_salesman", raise_if_not_found=False)
        cls.group_sale_all = cls.env.ref(
            "sales_team.group_sale_salesman_all_leads", raise_if_not_found=False
        ) or cls.env.ref("sale.group_sale_salesman_all_leads", raise_if_not_found=False)

        # Models
        cls.Partner = cls.env["res.partner"]
        cls.Users = cls.env["res.users"]
        cls.Lead = cls.env["crm.lead"]
        cls.SaleOrder = cls.env["sale.order"]
        cls.IrRule = cls.env["ir.rule"]

        # Users
        cls.user_external = cls._create_user(
            name="External Agent User",
            login="ext_agent",
            groups=[cls.group_external],
            extra_vals={
                "is_external_agent": True,
                "is_internal_salesperson": False,
            },
        )

        internal_groups = [cls.group_internal]
        if cls.group_sale_user:
            internal_groups.append(cls.group_sale_user)
        if cls.group_sale_all:
            internal_groups.append(cls.group_sale_all)

        cls.user_internal = cls._create_user(
            name="Internal Sales User",
            login="int_sales",
            groups=internal_groups,
            extra_vals={
                "is_external_agent": False,
                "is_internal_salesperson": True,
            },
        )

        cls.user_other_sales = cls._create_user(
            name="Other Sales User",
            login="other_sales",
            groups=([cls.group_sale_user] if cls.group_sale_user else []),
            extra_vals={
                "is_external_agent": False,
                "is_internal_salesperson": False,
            },
        )

        # Partners
        cls.partner_allowed = cls.Partner.create(
            {
                "name": "Partner Allowed for External",
                "external_agent_ids": [(6, 0, [cls.user_external.id])],
            }
        )
        cls.partner_denied = cls.Partner.create({"name": "Partner Denied for External"})

        # Opportunities
        cls.opp_ext_assigned = cls.Lead.create(
            {
                "name": "Opp (partner has external agent) / user = external",
                "type": "opportunity",
                "partner_id": cls.partner_allowed.id,
                "user_id": cls.user_external.id,
            }
        )
        cls.opp_other = cls.Lead.create(
            {
                "name": "Opp (partner has external agent) / user = other",
                "type": "opportunity",
                "partner_id": cls.partner_allowed.id,
                "user_id": cls.user_other_sales.id,
            }
        )
        cls.opp_internal_assigned = cls.Lead.create(
            {
                "name": "Opp (partner NOT allowed) / user = internal",
                "type": "opportunity",
                "partner_id": cls.partner_denied.id,
                "user_id": cls.user_internal.id,
            }
        )

        # Sale orders
        cls.customer = cls.Partner.create({"name": "Customer"})
        cls.sale_order_1 = cls.SaleOrder.create(
            {
                "partner_id": cls.customer.id,
                "company_id": cls.company.id,
                "user_id": cls.user_internal.id,
            }
        )
        cls.sale_order_2 = cls.SaleOrder.create(
            {
                "partner_id": cls.customer.id,
                "company_id": cls.company.id,
                "user_id": cls.user_other_sales.id,
            }
        )

    @classmethod
    def _create_user(cls, name, login, groups=None, extra_vals=None):
        groups = groups or []
        extra_vals = extra_vals or {}
        vals = {
            "name": name,
            "login": login,
            "email": f"{login}@example.com",
            "company_id": cls.env.company.id,
            "company_ids": [(6, 0, [cls.env.company.id])],
            "groups_id": [(6, 0, [g.id for g in groups if g])],
        }
        vals.update(extra_vals)
        return cls.env["res.users"].with_context(no_reset_password=True).create(vals)

    # -------------------------
    # CONTACTS (External Agents)
    # -------------------------
    def test_external_agent_sees_only_assigned_contacts(self):
        partner_env = self.Partner.with_user(self.user_external)
        partners = partner_env.search([])
        partner_ids = set(partners.ids)

        self.assertIn(self.partner_allowed.id, partner_ids)
        self.assertNotIn(self.partner_denied.id, partner_ids)
        self.assertIn(self.user_external.partner_id.id, partner_ids)

    # -------------------------
    # CRM (External Agents)
    # -------------------------
    def test_external_agent_sees_only_opportunities_of_assigned_contacts(self):
        lead_env = self.Lead.with_user(self.user_external)
        opps = lead_env.search([("type", "=", "opportunity")])
        opp_ids = set(opps.ids)

        # Both opportunities linked to partner_allowed must be visible
        self.assertIn(self.opp_ext_assigned.id, opp_ids)
        self.assertIn(self.opp_other.id, opp_ids)

        # Opportunity with partner without the agent must not be visible
        self.assertNotIn(self.opp_internal_assigned.id, opp_ids)

    # -------------------------
    # SALES (External Agents)
    # -------------------------
    def test_external_agent_has_no_sales_order_access(self):
        so_env = self.SaleOrder.with_user(self.user_external)

        with self.assertRaises(AccessError):
            so_env.browse(self.sale_order_1.id).read(["name"])

    # -------------------------
    # CRM (Internal Salespeople)
    # -------------------------
    def test_internal_salesperson_rule_is_installed(self):
        """
        Validate the internal salesperson crm.lead ir.rule exists, is attached to the
        internal group, and enforces own opportunities only.
        """
        rule = self.env.ref(
            "agent_external_permissions.rule_crm_lead_internal_salesperson"
        )
        self.assertTrue(rule)
        self.assertIn(self.group_internal, rule.groups)

        # tolerant compare (ignore whitespace)
        normalized = "".join((rule.domain_force or "").split())
        expected = "".join(
            "[('type','=','opportunity'),('user_id','=',user.id)]".split()
        )
        self.assertEqual(normalized, expected)

    def test_internal_salesperson_can_read_own_opportunity(self):
        lead_env = self.Lead.with_user(self.user_internal)
        lead_env.browse(self.opp_internal_assigned.id).read(["name"])

    # -------------------------
    # SALES (Internal Salespeople)
    # -------------------------
    def test_internal_salesperson_sales_not_restricted_by_this_module(self):
        rules = self.IrRule.search(
            [
                ("model_id.model", "=", "sale.order"),
                ("groups", "in", self.group_internal.id),
            ]
        )
        self.assertFalse(rules)

        so_env = self.SaleOrder.with_user(self.user_internal)
        order_ids = set(so_env.search([]).ids)

        self.assertIn(self.sale_order_1.id, order_ids)

        if self.group_sale_all and self.group_sale_all in self.user_internal.groups_id:
            self.assertIn(self.sale_order_2.id, order_ids)

    # -------------------------
    # WIZARD
    # -------------------------
    def test_update_agents_wizard_updates_existing_opportunities(self):
        self.partner_allowed.write(
            {"external_agent_ids": [(6, 0, [self.user_external.id])]}
        )

        self.opp_ext_assigned.write({"external_agent_ids": [(5, 0, 0)]})
        self.assertFalse(self.opp_ext_assigned.external_agent_ids)

        wizard = self.env["update.agents.wizard"].create(
            {
                "partner_id": self.partner_allowed.id,
                "update_existing": True,
                "create_new_opportunities": False,
            }
        )
        wizard.action_update_agents()

        self.opp_ext_assigned.invalidate_recordset()
        self.assertEqual(
            set(self.opp_ext_assigned.external_agent_ids.ids), {self.user_external.id}
        )

    def test_update_agents_wizard_raises_if_no_agents_on_contact(self):
        self.partner_denied.write({"external_agent_ids": [(5, 0, 0)]})

        wizard = self.env["update.agents.wizard"].create(
            {
                "partner_id": self.partner_denied.id,
                "update_existing": True,
                "create_new_opportunities": False,
            }
        )
        with self.assertRaises(Exception):
            wizard.action_update_agents()
