# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import datetime as dt
import unittest
import uuid

from odoo.exceptions import UserError
from odoo.tests import TransactionCase  # Odoo 18

BaseCase = TransactionCase


def _ensure_company_prefix(env, value="TST"):
    """Set the exact config parameter key used by _default_file_code:
    crm_filemgmt.file_prefix_<company_id>
    """
    company_id = env.company.id
    key = f"crm_filemgmt.file_prefix_{company_id}"
    env["ir.config_parameter"].sudo().set_param(key, value)


def _make_valid_code(prefix="TST", seq=1, year=None):
    """Build a code in the expected shape: <PREFIX>-<YYYY>/<NNNN>."""
    if year is None:
        year = dt.date.today().year
    return f"{prefix}-{str(year).zfill(4)}/{str(seq).zfill(4)}"


class TestResFileTemplateActions(BaseCase):
    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()

        # Ensure the exact prefix parameter the model reads is present
        _ensure_company_prefix(cls.env, "TST")

        cls.File = cls.env["res.file"]
        cls.Stage = cls.env["res.file.stage"]
        cls.Cat = cls.env["res.file.category"]
        cls.Report = cls.env["res.file.report"]

        # Unique suffix to avoid collisions with other tests
        cls.sfx = uuid.uuid4().hex[:6]

        # Minimal fixtures for res.file
        cls.stage = cls.Stage.create({"name": f"Draft [{cls.sfx}]", "sequence": 10})
        cls.cat = cls.Cat.create({"name": f"Internal [{cls.sfx}]", "is_readonly": True})

        cls.rep = cls.Report.create(
            {
                "name": f"Base [{cls.sfx}]",
                "report_template_start": "<div>START {{ record.subject }}</div>",
                "report_template_end": "<div>END</div>",
            }
        )

        # Local sequence for generating valid alphanum_code values
        cls._seq = 0

    def _next_seq(self):
        self.__class__._seq += 1
        return self._seq

    def _new_file(self, subject="Alpha", report_id=None):
        """Create res.file providing a valid alphanum_code so the default
        is not used."""
        seq = self._next_seq()
        code = _make_valid_code(prefix="TST", seq=seq)
        # pylint: disable=invalid-name
        FileCtx = self.File.with_context(default_alphanum_code=code)
        return FileCtx.create(
            {
                "alphanum_code": code,  # <-- correct field name
                "subject": subject,
                "stage_id": self.stage.id,
                "category_id": self.cat.id,
                "file_report_id": report_id or self.rep.id,
            }
        )

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_action_get_start_template_sets_field(self):
        f = self._new_file()
        f.template_start = False
        f.action_get_start_template()
        self.assertTrue(f.template_start and "START" in f.template_start)

    def test_action_get_end_template_sets_field(self):
        f = self._new_file()
        f.template_end = False
        f.action_get_end_template()
        self.assertTrue(f.template_end and "END" in f.template_end)

    def test_action_get_templates_errors_without_report_or_content(self):
        # No report -> expect UserError
        seq = self._next_seq()
        code = _make_valid_code(prefix="TST", seq=seq)
        f = self.File.with_context(default_alphanum_code=code).create(
            {
                "alphanum_code": code,
                "subject": f"NoReport [{self.sfx}]",
                "stage_id": self.stage.id,
                "category_id": self.cat.id,
            }
        )
        with self.assertRaises(UserError):
            f.action_get_start_template()
        with self.assertRaises(UserError):
            f.action_get_end_template()

        # Report without templates -> expect UserError
        rep2 = self.Report.create({"name": f"Empty [{self.sfx}]"})
        f2 = self._new_file(subject=f"EmptyRep [{self.sfx}]", report_id=rep2.id)
        with self.assertRaises(UserError):
            f2.action_get_start_template()
        with self.assertRaises(UserError):
            f2.action_get_end_template()


if __name__ == "__main__":
    unittest.main()
