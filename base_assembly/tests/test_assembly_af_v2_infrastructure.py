# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""AF v2.0 infrastructure: chatter, company defaults, name uniqueness, date coherence."""

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from .common import AssemblyTestMixin


class TestAssemblyAfV2Infrastructure(AssemblyTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Assembly = cls.env["assembly.assembly"]
        cls.Agenda = cls.env["assembly.agenda"]
        cls.AssemblyType = cls.env["assembly.type"]

    def test_assembly_inherits_mail_thread(self):
        self.assertIn("mail.thread", self.Assembly._inherit)

    def test_agenda_inherits_mail_thread(self):
        self.assertIn("mail.thread", self.Agenda._inherit)

    def test_agenda_and_option_title_fields_are_translatable(self):
        """AF v2: publishable labels on agenda lines and ballot options must be translatable."""
        Option = self.env["assembly.agenda.option"]
        self.assertTrue(
            self.Agenda._fields["name"].translate,
            "assembly.agenda.name must have translate=True",
        )
        self.assertTrue(
            Option._fields["name"].translate,
            "assembly.agenda.option.name must have translate=True",
        )

    def test_assembly_has_message_post(self):
        self.assertTrue(callable(getattr(self.Assembly, "message_post", None)))

    def test_company_defaults_from_env_on_assembly(self):
        assembly = self._create_assembly(name="Co default asm")
        self.assertEqual(assembly.company_id, self.env.company)

    def test_company_propagates_from_type_on_create_when_default_company(self):
        c2 = self._secondary_company()
        atype = self.AssemblyType.with_company(c2).create(
            {
                "name": "Type in C2",
                "code": "TYC2_%s" % c2.id,
                "company_id": c2.id,
            }
        )
        asm = self.Assembly.with_company(c2).create(
            {
                "name": "Asm in C2",
                "assembly_type_id": atype.id,
            }
        )
        self.assertEqual(asm.company_id, c2)

    def test_assembly_type_must_match_assembly_company(self):
        """Type's company is applied on create when env/default company would mismatch."""
        c2 = self._secondary_company()
        atype = self.AssemblyType.with_company(c2).create(
            {
                "name": "C2 only type",
                "code": "C2ONLY_%s" % c2.id,
                "company_id": c2.id,
            }
        )
        asm = self.Assembly.create(
            {
                "name": "Cross-company assembly",
                "assembly_type_id": atype.id,
            }
        )
        self.assertEqual(asm.company_id, c2)

    def test_assembly_name_unique_per_company(self):
        self._create_assembly(name="UniqueNameDup")
        with mute_logger("odoo.sql_db"):
            with self.assertRaises(Exception):
                self._create_assembly(name="UniqueNameDup")

    def test_same_assembly_name_allowed_in_different_companies(self):
        c2 = self._secondary_company()
        a1 = self._create_assembly(name="Shared title")
        at2 = self.AssemblyType.with_company(c2).create(
            {
                "name": "T2",
                "code": "T2_%s" % c2.id,
                "company_id": c2.id,
            }
        )
        a2 = self.Assembly.with_company(c2).create(
            {
                "name": "Shared title",
                "assembly_type_id": at2.id,
            }
        )
        self.assertEqual(a1.name, a2.name)
        self.assertNotEqual(a1.company_id, a2.company_id)

    def test_temporal_second_call_must_be_after_first(self):
        assembly = self._create_assembly(name="Temporal 1")
        with self.assertRaises(ValidationError):
            assembly.write(
                {
                    "date_first_call": "2026-06-10 10:00:00",
                    "date_second_call": "2026-06-10 09:00:00",
                }
            )

    def test_temporal_second_call_after_first_enforced_on_create(self):
        """Same as ``test_temporal_second_call_must_be_after_first`` but on ``create``."""
        with self.assertRaises(ValidationError):
            self.Assembly.create(
                {
                    "name": "Bad second call on create",
                    "date_first_call": "2026-06-10 10:00:00",
                    "date_second_call": "2026-06-10 09:00:00",
                }
            )

    def test_temporal_announcement_not_after_first_call_day(self):
        assembly = self._create_assembly(name="Temporal 2")
        with self.assertRaises(ValidationError):
            assembly.write(
                {
                    "date_first_call": "2026-06-05 12:00:00",
                    "date_announcement": "2026-06-10",
                }
            )

    def test_temporal_session_start_not_before_first_call(self):
        assembly = self._create_assembly(name="Temporal 3")
        with self.assertRaises(ValidationError):
            assembly.write(
                {
                    "date_first_call": "2026-06-10 12:00:00",
                    "date_start": "2026-06-10 10:00:00",
                }
            )

    def test_temporal_session_end_not_before_start(self):
        assembly = self._create_assembly(name="Temporal 4")
        with self.assertRaises(ValidationError):
            assembly.write(
                {
                    "date_start": "2026-06-10 14:00:00",
                    "date_end": "2026-06-10 12:00:00",
                }
            )

    def test_temporal_valid_combination_accepted(self):
        assembly = self._create_assembly(name="Temporal OK")
        assembly.write(
            {
                "date_announcement": "2026-06-01",
                "date_first_call": "2026-06-10 10:00:00",
                "date_second_call": "2026-06-10 11:00:00",
                "date_start": "2026-06-10 12:00:00",
                "date_end": "2026-06-10 18:00:00",
            }
        )

    def _secondary_company(self):
        return self.env["res.company"].create(
            {
                "name": "Assembly Test Company B",
                "currency_id": self.env.company.currency_id.id,
            }
        )
