# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import unittest

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("at_install")
class TestVoteTypeCore(TransactionCase):
    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        partners = cls.env["res.partner"].search([], limit=2, order="id")
        if len(partners) < 2:
            raise unittest.SkipTest(
                "base_vote core tests need at least two res.partner rows"
            )
        cls.partner_a = partners[0]
        cls.partner_b = partners[1]

    def test_recompute_archived_vote_type_raises(self):
        vt = self.env["vote.type"].create(
            {
                "name": "BV archived recompute",
                "code": "bv_arch_%s" % self.partner_a.id,
                "formula": "1",
                "vote_value_type": "integer",
                "partner_domain": repr([("id", "=", self.partner_a.id)]),
            }
        )
        vt.write({"active": False})
        with self.assertRaises(UserError):
            vt.action_recompute_votes()

    def test_evaluate_formula_empty_returns_zero(self):
        vt = self.env["vote.type"].create(
            {
                "name": "BV empty formula",
                "code": "bv_emptyf_%s" % self.partner_a.id,
                "formula": "",
                "vote_value_type": "integer",
            }
        )
        value, detail = vt.evaluate_formula(self.partner_a)
        self.assertEqual(value, 0.0)
        self.assertEqual(detail, "")

    def test_evaluate_formula_integer_truncates(self):
        vt = self.env["vote.type"].create(
            {
                "name": "BV int trunc",
                "code": "bv_int_%s" % self.partner_a.id,
                "formula": "3.9",
                "vote_value_type": "integer",
            }
        )
        value, _detail = vt.evaluate_formula(self.partner_a)
        self.assertEqual(value, 3)

    def test_test_formula_missing_partner(self):
        vt = self.env["vote.type"].create(
            {
                "name": "BV test formula",
                "code": "bv_tf_%s" % self.partner_a.id,
                "formula": "1",
                "vote_value_type": "integer",
            }
        )
        bad_id = (
            self.env["res.partner"].search([], order="id desc", limit=1).id + 999999
        )
        out = vt.test_formula("1", bad_id)
        self.assertIn("error", out)

    def test_recompute_my_votes_respects_domain_and_unlinks_stale(self):
        code = "bv_my_%s_%s" % (self.partner_a.id, self.partner_b.id)
        vt = self.env["vote.type"].create(
            {
                "name": "BV partner recompute domain",
                "code": code,
                "formula": "7",
                "vote_value_type": "integer",
                "partner_domain": repr(
                    [("id", "in", (self.partner_a | self.partner_b).ids)]
                ),
            }
        )
        vt.action_recompute_votes()
        self.assertTrue(
            self.env["partner.vote"].search(
                [
                    ("partner_id", "=", self.partner_a.id),
                    ("vote_type_id", "=", vt.id),
                ]
            )
        )
        vt.write({"partner_domain": repr([("id", "=", self.partner_b.id)])})
        self.partner_a.action_recompute_my_votes()
        row_a = self.env["partner.vote"].search(
            [
                ("partner_id", "=", self.partner_a.id),
                ("vote_type_id", "=", vt.id),
            ]
        )
        self.assertFalse(row_a)
        row_b = self.env["partner.vote"].search(
            [
                ("partner_id", "=", self.partner_b.id),
                ("vote_type_id", "=", vt.id),
            ]
        )
        self.assertTrue(row_b)
        self.assertEqual(row_b.vote_count_integer, 7)
