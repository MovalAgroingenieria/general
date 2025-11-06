# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import datetime as dt
import re
import unittest
import uuid

from odoo.tests import TransactionCase


def _ensure_file_prefix(env, value="TST"):
    """Ensure company-scoped and legacy keys exist to satisfy defaults."""
    env.company.file_prefix = value
    params = env["ir.config_parameter"].sudo()
    # Key used by _default_file_code in your model (company-specific)
    params.set_param(f"crm_filemgmt.file_prefix_{env.company.id}", value)
    # Legacy fallbacks (harmless if not used)
    params.set_param("crm_filemgmt.file_prefix", value)
    params.set_param("res.file.prefix", value)


class TestResFileBaseReport(TransactionCase):
    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        _ensure_file_prefix(cls.env, "TST")

        # Models
        cls.Stage = cls.env["res.file.stage"]
        cls.Cat = cls.env["res.file.category"]
        cls.File = cls.env["res.file"]
        cls.ReportCfg = cls.env["res.file.report"]

        # Base ir.actions.report (must exist in the module)
        cls.ir_report = cls.env.ref(
            "crm_filemgmt.res_file_report_base", raise_if_not_found=False
        )
        assert (
            cls.ir_report
        ), "Missing ir.actions.report 'crm_filemgmt.res_file_report_base'"
        cls.report_ref = (
            cls.ir_report.report_name
        )  # e.g. 'crm_filemgmt.file_report_base_document'

        # Unique suffix for fixture records
        cls.sfx = uuid.uuid4().hex[:6]

        # Reuse "Draft" if it exists, otherwise create a unique one
        draft = cls.Stage.search([("name", "=", "Draft")], limit=1)
        cls.stage = draft or cls.Stage.create(
            {"name": f"Draft [{cls.sfx}]", "sequence": 10}
        )

        # Use a unique category to avoid cross-suite collisions
        cls.cat = cls.Cat.create({"name": f"Internal [{cls.sfx}]", "is_readonly": True})

        # Report configuration used by res.file
        cls.report_cfg = cls.ReportCfg.create(
            {
                "name": f"Base Report [{cls.sfx}]",
                "report_template_start": "<div>TOP BLOCK</div><div>"
                "START {{ record.subject }}</div>",
                "report_template_end": "<div>BOTTOM BLOCK</div><div>END</div>",
            }
        )

        # Simple counter to build explicit, valid codes
        cls._seq = 0

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def _next_alphanum_code(self):
        """Build a valid code matching <PREFIX>-<YYYY>/<NNNN> to bypass defaults."""
        self.__class__._seq += 1
        prefix = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(f"crm_filemgmt.file_prefix_{self.env.company.id}")
            or "TST"
        )
        year = dt.date.today().year
        return f"{prefix}-{year:04d}/{self._seq:04d}"

    def _new_file(self, subject="Alpha"):
        """Create res.file while bypassing internal default generation."""
        return self.File.create(
            {
                "alphanum_code": self._next_alphanum_code(),
                "subject": subject,
                "stage_id": self.stage.id,
                "category_id": self.cat.id,
                "file_report_id": self.report_cfg.id,
            }
        )

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------
    def test_report_action_and_template_registered(self):
        """The base ir.actions.report is present and points to the expected template."""
        self.assertEqual(self.ir_report.model, "res.file")
        self.assertEqual(self.report_ref, "crm_filemgmt.file_report_base_document")

    def test_render_qweb_html_includes_blocks(self):
        """Render HTML via ir.actions.report using
        report_ref + docids; verify template blocks."""
        f = self._new_file(subject="Alpha")

        # Onchange methods don't run in tests; populate templates explicitly
        f.action_get_start_template()
        f.action_get_end_template()

        # pylint: disable=protected-access
        html, fmt = self.env["ir.actions.report"]._render_qweb_html(
            self.report_ref, f.ids, None
        )
        html_text = "".join(html) if isinstance(html, (list, tuple)) else str(html)
        norm = re.sub(r"\s+", " ", html_text)

        self.assertEqual(fmt, "html")
        self.assertIn("TOP BLOCK", norm)
        self.assertIn("BOTTOM BLOCK", norm)
        self.assertIn("START Alpha", norm)
        self.assertIn(">END<", norm)

    def test_render_qweb_pdf_returns_bytes(self):
        """Render PDF via ir.actions.report; sanity-check non-trivial payload."""
        f = self._new_file()
        f.action_get_start_template()
        f.action_get_end_template()

        # pylint: disable=protected-access
        pdf, fmt = self.env["ir.actions.report"]._render_qweb_pdf(
            self.report_ref, f.ids, None
        )
        self.assertEqual(fmt, "html")
        self.assertIsInstance(pdf, (bytes, bytearray))
        self.assertGreater(len(pdf), 100)

    def test_print_action_from_record(self):
        """Use the model wrapper; accept either a direct
        report or an act_window wrapper."""
        f = self._new_file()
        f.action_get_start_template()
        f.action_get_end_template()

        act = f.action_print_selected_report()
        self.assertIsInstance(act, dict)
        # Some setups may wrap the report call; accept both.
        self.assertIn(act.get("type"), {"ir.actions.report", "ir.actions.act_window"})
        if act.get("type") == "ir.actions.report":
            self.assertEqual(act.get("report_name"), self.report_ref)


if __name__ == "__main__":
    unittest.main()
