# pylint: disable=duplicate-code
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import datetime as dt
import unittest
import uuid

from odoo.tests import TransactionCase  # Odoo 18

BaseCase = TransactionCase


def _ensure_file_prefix(env, value="TST"):
    """Ensure the required file prefix (company + system parameter) is set.
    Keep both generic keys and the company-scoped key used by _default_file_code.
    """
    # Company field (in case your model ever reads it)
    env.company.file_prefix = value

    # ir.config_parameter keys
    params = env["ir.config_parameter"].sudo()
    params.set_param("crm_filemgmt.file_prefix", value)
    params.set_param("res.file.prefix", value)
    # IMPORTANT: ResFile._default_file_code() uses this company-scoped key:
    params.set_param(f"crm_filemgmt.file_prefix_{env.company.id}", value)


class TestResPartnerFileLinks(BaseCase):
    """Tests for res.partner extension with file links."""

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        _ensure_file_prefix(cls.env, "TST")
        cls.uniq = uuid.uuid4().hex[:8]

        cls.Partner = cls.env["res.partner"]
        cls.File = cls.env["res.file"]
        cls.Link = cls.env["res.file.partnerlink"]
        cls.Stage = cls.env["res.file.stage"]
        cls.Cat = cls.env["res.file.category"]
        cls.View = cls.env["ir.ui.view"]

        # Unique fixtures to avoid collisions across the suite
        cls.stage = cls.Stage.create(
            {
                "name": f"Draft [TEST {cls.uniq}]",
                "sequence": 10,
                "fold": False,
                "is_closing_stage": False,
            }
        )
        cls.cat = cls.Cat.create(
            {"name": f"Internal [TEST {cls.uniq}]", "is_readonly": True}
        )

        cls.partner_a = cls.Partner.create({"name": f"Partner A [{cls.uniq}]"})
        cls.partner_b = cls.Partner.create({"name": f"Partner B [{cls.uniq}]"})

        cls._seq = 0  # explicit code counter

    # -------------------------
    # Helpers
    # -------------------------

    def _next_code(self) -> str:
        """Return code matching <PREFIX>-<YYYY>/<NNNN> expected by the model."""
        self.__class__._seq += 1
        year = dt.date.today().year
        return f"TST-{year:04d}/{self._seq:04d}"

    def _new_file(self, subject="Subj"):
        """Create a minimal res.file without triggering default code generation.
        Use the correct field name 'alphanum_code' and also seed the context default.
        """
        code = self._next_code()
        # pylint: disable=invalid-name
        FileCtx = self.File.with_context(default_alphanum_code=code)
        return FileCtx.create(
            {
                "alphanum_code": code,
                "subject": subject,
                "stage_id": self.stage.id,
                "category_id": self.cat.id,
            }
        )

    # -------------------------
    # action_get_files
    # -------------------------

    def test_action_get_files_returns_false_when_empty(self):
        p = self.Partner.create({"name": f"No Links [{self.uniq}]"})
        result = p.action_get_files()
        # Should return False when no files
        self.assertFalse(result)

    def test_action_get_files_with_links(self):
        f1 = self._new_file("L1")
        f2 = self._new_file("L2")
        l1 = self.Link.create(
            {"file_id": f1.id, "partner_id": self.partner_b.id, "is_main": True}
        )
        l2 = self.Link.create(
            {"file_id": f2.id, "partner_id": self.partner_b.id, "is_main": False}
        )

        act = self.partner_b.action_get_files()
        self.assertIsInstance(act, dict)
        self.assertEqual(act.get("type"), "ir.actions.act_window")
        self.assertEqual(act.get("res_model"), "res.file.partnerlink")
        self.assertIn("list", act.get("view_mode", ""))

        # Domain should include the two link ids
        domain = act.get("domain") or []
        ids_in_domain = set(domain[0][2]) if domain and domain[0][0] == "id" else set()
        self.assertTrue({l1.id, l2.id}.issubset(ids_in_domain))


if __name__ == "__main__":
    unittest.main()
