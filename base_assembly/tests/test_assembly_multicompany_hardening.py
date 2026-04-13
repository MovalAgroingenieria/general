# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Multi-company hardening: stored ``company_id``, record rules, ORM isolation."""

import unittest

from odoo.addons.base_assembly.controllers import attendance as attendance_controller
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin

_ASSEMBLY_MULTICOMPANY_GLOBAL_RULE_XMLIDS = (
    "base_assembly.assembly_type_rule_multicompany",
    "base_assembly.assembly_assembly_rule_multicompany",
    "base_assembly.assembly_agenda_rule_multicompany",
    "base_assembly.assembly_agenda_option_rule_multicompany",
    "base_assembly.assembly_attendee_rule_multicompany",
    "base_assembly.assembly_delegation_rule_multicompany",
    "base_assembly.assembly_representation_rule_multicompany",
    "base_assembly.assembly_voting_rule_multicompany",
    "base_assembly.assembly_voting_line_rule_multicompany",
    "base_assembly.assembly_voting_result_rule_multicompany",
    "base_assembly.assembly_attendee_vote_rule_multicompany",
)


class TestAssemblyMulticompanyHardening(AssemblyTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_manager = cls.env.ref("base_assembly.assembly_group_manager")
        cls.base_user = cls.env.ref("base.group_user")

    def _secondary_company(self):
        return self.env["res.company"].create(
            {
                "name": "Assembly MC Company B",
                "currency_id": self.env.company.currency_id.id,
            }
        )

    def _user_manager_single_company(self, company):
        try:
            return self.env["res.users"].create(
                {
                    "name": "MC Manager %s" % company.id,
                    "login": "assembly_mc_mgr_%s" % company.id,
                    "password": "assembly_mc_mgr_%s" % company.id,
                    "company_id": company.id,
                    "company_ids": [(6, 0, [company.id])],
                    "groups_id": [(6, 0, [self.base_user.id, self.group_manager.id])],
                }
            )
        except Exception as e:
            if "calendar_default_privacy" in str(e) or "not null" in str(e).lower():
                raise unittest.SkipTest(
                    "res.users.settings requires calendar_default_privacy"
                ) from e
            raise

    def test_representation_stored_company_id_matches_assembly(self):
        partners = self._create_partners(self.env, 2, prefix="MCRep")
        domain = "[('id', 'in', %s)]" % partners.ids
        assembly, _agenda = self._create_assembly_with_agenda(
            name="MC rep asm",
            partner_domain=domain,
        )
        rep = self.env["assembly.representation"].create(
            {
                "assembly_id": assembly.id,
                "owner_partner_id": partners[0].id,
                "agent_partner_id": partners[1].id,
            }
        )
        self.assertEqual(rep.company_id, assembly.company_id)

    def test_agenda_option_stored_company_id_matches_agenda(self):
        assembly = self._create_assembly(name="MC opt asm")
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "MC multi line",
                "agenda_vote_mode": "manual_multi",
                "sequence": 10,
                "option_ids": [(0, 0, {"name": "Choice A", "sequence": 10})],
            }
        )
        opt = agenda.option_ids[0]
        self.assertEqual(opt.company_id, agenda.company_id)
        self.assertEqual(opt.company_id, assembly.company_id)

    def test_manager_in_company_b_cannot_search_representation_in_company_a(self):
        c_a = self.env.company
        c_b = self._secondary_company()
        partners = self._create_partners(self.env, 2, prefix="MCIsoRep")
        domain = "[('id', 'in', %s)]" % partners.ids
        assembly, _agenda = self._create_assembly_with_agenda(
            name="MC iso rep A",
            partner_domain=domain,
        )
        self.assertEqual(assembly.company_id, c_a)
        rep = self.env["assembly.representation"].create(
            {
                "assembly_id": assembly.id,
                "owner_partner_id": partners[0].id,
                "agent_partner_id": partners[1].id,
            }
        )
        user_b = self._user_manager_single_company(c_b)
        env_b = self.env(user=user_b)
        found = env_b["assembly.representation"].search([("id", "=", rep.id)])
        self.assertFalse(found)

    def test_manager_in_company_b_cannot_search_agenda_option_in_company_a(self):
        c_b = self._secondary_company()
        assembly = self._create_assembly(name="MC iso opt A")
        self.assertEqual(assembly.company_id, self.env.company)
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "MC iso multi",
                "agenda_vote_mode": "manual_multi",
                "sequence": 10,
                "option_ids": [(0, 0, {"name": "Opt iso", "sequence": 10})],
            }
        )
        opt = agenda.option_ids[0]
        user_b = self._user_manager_single_company(c_b)
        env_b = self.env(user=user_b)
        found = env_b["assembly.agenda.option"].search([("id", "=", opt.id)])
        self.assertFalse(found)

    def test_multicompany_rule_domains_use_direct_company_id(self):
        """Global assembly ir.rule domains must filter on stored company_id (no deep paths)."""
        for xid in _ASSEMBLY_MULTICOMPANY_GLOBAL_RULE_XMLIDS:
            rule = self.env.ref(xid)
            df = rule.domain_force or ""
            self.assertIn(
                "company_id",
                df,
                "%s must reference company_id" % xid,
            )
            self.assertNotIn(
                "assembly_id.company_id",
                df,
                "%s must not use assembly_id.company_id" % xid,
            )
            self.assertNotIn(
                "agenda_id.company_id",
                df,
                "%s must not use agenda_id.company_id" % xid,
            )

    def test_multicompany_rules_target_models_have_stored_company_id(self):
        """Each global multi-company rule must apply to a model with stored company_id."""
        Field = self.env["ir.model.fields"].sudo()
        for xid in _ASSEMBLY_MULTICOMPANY_GLOBAL_RULE_XMLIDS:
            rule = self.env.ref(xid)
            model_name = rule.model_id.model
            company_f = Field.search(
                [
                    ("model", "=", model_name),
                    ("name", "=", "company_id"),
                ],
                limit=1,
            )
            self.assertTrue(
                company_f,
                "%s: model %s must define company_id" % (xid, model_name),
            )
            self.assertTrue(
                company_f.store,
                "%s: %s.company_id must be stored" % (xid, model_name),
            )

    def test_attendance_deep_link_domain_scopes_by_session_companies(self):
        env = self.env
        base = [("assembly_id", "=", 1), ("partner_id", "=", 2)]
        dom = attendance_controller._attendance_domain_scoped_to_session_companies(
            base, env
        )
        if env.companies.ids:
            self.assertNotEqual(dom, base)
        else:
            self.assertEqual(dom, base)
