# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import uuid
from datetime import date

from odoo.tests.common import TransactionCase

try:
    from odoo.tests.common import SavepointCase as BaseCase
except ImportError:
    BaseCase = TransactionCase
from odoo.exceptions import UserError


def _ensure_file_prefix(env, value="TST"):
    """Seed both the company field and the config param your model uses."""
    env.company.file_prefix = value
    params = env["ir.config_parameter"].sudo()
    params.set_param(
        f"crm_filemgmt.file_prefix_{env.company.id}", value
    )  # company-scoped
    # harmless fallbacks if code ever looked these up
    params.set_param("crm_filemgmt.file_prefix", value)
    params.set_param("res.file.prefix", value)


class TestResFile(BaseCase):
    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.File = cls.env["res.file"]
        cls.Stage = cls.env["res.file.stage"]
        cls.Cat = cls.env["res.file.category"]
        cls.Att = cls.env["ir.attachment"]
        cls.Partner = cls.env["res.partner"]

        # Ensure the prefix the defaults/validations expect
        _ensure_file_prefix(cls.env, "TST")

        uniq = uuid.uuid4().hex[:6]

        # Re-use existing stages if present; otherwise create unique ones
        cls.stage_draft = cls.Stage.search(
            [("name", "=", "Draft")], limit=1
        ) or cls.Stage.create(
            {
                "name": f"Draft [{uniq}]",
                "sequence": 10,
                "fold": False,
                "is_closing_stage": False,
            }
        )
        cls.stage_closed = cls.Stage.search(
            [("name", "=", "Closed")], limit=1
        ) or cls.Stage.create(
            {
                "name": f"Closed [{uniq}]",
                "sequence": 30,
                "fold": True,
                "is_closing_stage": True,
            }
        )

        # Re-use existing Internal category if present; otherwise create unique one
        cls.cat_internal = cls.Cat.search(
            [("name", "=", "Internal")], limit=1
        ) or cls.Cat.create({"name": f"Internal [{uniq}]", "is_readonly": True})

        # Two partners
        cls.partner_a = cls.Partner.create({"name": f"Partner A [{uniq}]"})
        cls.partner_b = cls.Partner.create({"name": f"Partner B [{uniq}]"})

    # -------------------------
    # Helpers
    # -------------------------

    def _new_file(self, **kwargs):
        """Create a minimal file in 'Draft' with a category."""
        vals = {
            "subject": kwargs.get("subject", "Subject X"),
            "stage_id": kwargs.get("stage_id", self.stage_draft.id),
            "category_id": kwargs.get("category_id", self.cat_internal.id),
        }
        if "alphanum_code" in kwargs:
            vals["alphanum_code"] = kwargs["alphanum_code"]
        return self.File.create(vals)

    # -------------------------
    # Defaults & display
    # -------------------------

    def test_default_code_and_increment(self):
        f1 = self._new_file()
        year = date.today().year
        self.assertRegex(f1.alphanum_code, rf"^TST-{year:04d}/\d{{4}}$")
        self.assertTrue(f1.alphanum_code.endswith("/0001"))

        f2 = self._new_file()
        self.assertTrue(f2.alphanum_code.endswith("/0002"))

    # -------------------------
    # Computes & flags
    # -------------------------

    def test_is_closing_and_closing_date(self):
        f = self._new_file()
        self.assertFalse(f.is_closing_stage)
        self.assertFalse(f.closing_date)

        f.stage_id = self.stage_closed.id
        f.flush_recordset()
        self.assertTrue(f.is_closing_stage)
        self.assertEqual(f.closing_date, date.today())

    def test_with_technician_flag(self):
        f = self._new_file()
        self.assertFalse(f.with_technician)
        f.technician_id = self.partner_a.id
        self.assertTrue(f.with_technician)

    def test_has_filelinks_and_has_attachments(self):
        f1 = self._new_file(subject="S1")
        f2 = self._new_file(subject="S2")

        self.assertFalse(f1.has_filelinks)
        self.assertFalse(f1.has_attachments)

        f1.write({"filelink_ids": [(0, 0, {"related_file_id": f2.id})]})
        f1.invalidate_recordset()
        self.assertTrue(f1.has_filelinks)

        self.Att.create(
            {
                "name": "a.txt",
                "res_model": "res.file",
                "res_id": f1.id,
                "datas": "Zm9v",
                "mimetype": "text/plain",
            }
        )
        # pylint: disable=protected-access
        f1._compute_attachments_ids()
        f1._compute_has_attachments()
        self.assertTrue(f1.has_attachments)

    # -------------------------
    # Partnerlink constraints
    # -------------------------

    def test_partnerlinks_require_exactly_one_main_when_present(self):
        f = self._new_file()

        with self.assertRaises(UserError):
            f.write(
                {
                    "partnerlink_ids": [
                        (0, 0, {"partner_id": self.partner_a.id, "is_main": False}),
                        (0, 0, {"partner_id": self.partner_b.id, "is_main": False}),
                    ]
                }
            )

        with self.assertRaises(UserError):
            f.write(
                {
                    "partnerlink_ids": [
                        (5, 0, 0),
                        (0, 0, {"partner_id": self.partner_a.id, "is_main": True}),
                        (0, 0, {"partner_id": self.partner_b.id, "is_main": True}),
                    ]
                }
            )

        with self.assertRaises(UserError):
            f.write(
                {
                    "partnerlink_ids": [
                        (5, 0, 0),
                        (0, 0, {"partner_id": self.partner_a.id, "is_main": True}),
                        (0, 0, {"partner_id": self.partner_a.id, "is_main": False}),
                    ]
                }
            )

        f.write(
            {
                "partnerlink_ids": [
                    (5, 0, 0),
                    (0, 0, {"partner_id": self.partner_a.id, "is_main": True}),
                    (0, 0, {"partner_id": self.partner_b.id, "is_main": False}),
                ]
            }
        )
        self.assertEqual(f.partner_id, self.partner_a)

    # -------------------------
    # Filelink constraints
    # -------------------------

    def test_filelinks_no_self_reference_and_no_duplicates(self):
        f1 = self._new_file(subject="S1")
        f2 = self._new_file(subject="S2")

        with self.assertRaises(UserError):
            f1.write({"filelink_ids": [(0, 0, {"related_file_id": f1.id})]})

        with self.assertRaises(UserError):
            f1.write(
                {
                    "filelink_ids": [
                        (5, 0, 0),
                        (0, 0, {"related_file_id": f2.id}),
                        (0, 0, {"related_file_id": f2.id}),
                    ]
                }
            )

        f1.write({"filelink_ids": [(5, 0, 0), (0, 0, {"related_file_id": f2.id})]})
        self.assertEqual(f1.filelink_ids.related_file_id, f2)

    # -------------------------
    # Templates rendering
    # -------------------------

    def test_template_start_render_ok_and_error(self):
        f = self._new_file(subject="Hello")
        f.template_start = "Hi {{ record.subject }}"
        # pylint: disable=protected-access
        f._compute_template_start_rendered()
        self.assertIn("Hi Hello", f.template_start_rendered)

        f.template_start = "{{ invalid["
        # pylint: disable=protected-access
        f._compute_template_start_rendered()
        self.assertIn("ERROR IN START TEMPLATE", f.template_start_rendered)

    def test_template_end_render_ok_and_error(self):
        f = self._new_file(subject="Bye")
        f.template_end = "Bye {{ record.subject }}"
        # pylint: disable=protected-access
        f._compute_template_end_rendered()
        self.assertIn("Bye Bye", f.template_end_rendered)

        f.template_end = "{{ invalid["
        # pylint: disable=protected-access
        f._compute_template_end_rendered()
        self.assertIn("ERROR IN END TEMPLATE", f.template_end_rendered)
