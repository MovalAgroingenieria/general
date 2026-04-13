# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import unittest

from odoo.tests import TransactionCase, tagged


@tagged("at_install")
class TestVoteRecomputeStaleCleanup(TransactionCase):
    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        partners = cls.env["res.partner"].search([], limit=2, order="id")
        if len(partners) < 2:
            raise unittest.SkipTest(
                "base_vote stale-cleanup tests need at least two res.partner rows"
            )
        cls.partner_a = partners[0]
        cls.partner_b = partners[1]

    def test_recompute_unlinks_partner_votes_outside_current_domain(self):
        code = "bv_st_%s_%s" % (self.partner_a.id, self.partner_b.id)
        vt = self.env["vote.type"].create(
            {
                "name": "BV stale recompute",
                "code": code,
                "formula": "1",
                "vote_value_type": "integer",
                "partner_domain": repr(
                    [("id", "in", (self.partner_a | self.partner_b).ids)]
                ),
            }
        )
        vt.action_recompute_votes()
        votes = self.env["partner.vote"].search([("vote_type_id", "=", vt.id)])
        self.assertEqual(len(votes), 2)
        vt.write({"partner_domain": repr([("id", "=", self.partner_a.id)])})
        vt.action_recompute_votes()
        votes_after = self.env["partner.vote"].search([("vote_type_id", "=", vt.id)])
        self.assertEqual(len(votes_after), 1)
        self.assertEqual(votes_after.partner_id, self.partner_a)

    def test_recompute_with_empty_domain_unlinks_all_partner_votes(self):
        code = "bv_empty_%s" % self.partner_a.id
        vt = self.env["vote.type"].create(
            {
                "name": "BV empty domain",
                "code": code,
                "formula": "1",
                "vote_value_type": "integer",
                "partner_domain": repr([("id", "=", self.partner_a.id)]),
            }
        )
        vt.action_recompute_votes()
        self.assertTrue(self.env["partner.vote"].search([("vote_type_id", "=", vt.id)]))
        vt.write({"partner_domain": repr([("id", "in", [])])})
        vt.action_recompute_votes()
        self.assertFalse(
            self.env["partner.vote"].search([("vote_type_id", "=", vt.id)])
        )
