# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""AF v2.0 contract smoke: VAT + representation uniqueness (non-duplicated contracts).

Rendering, tracked links, and ``manual_multi`` options are fully covered in
``test_assembly_html_rendering``, ``test_assembly_attendance_link_tracker`` +
``test_http_attendance``, and ``test_assembly_agenda_vote_modes`` respectively.
"""

import uuid

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from .common import AssemblyTestMixin


class TestAssemblyAfV2Contracts(AssemblyTestMixin, TransactionCase):
    """VAT gates and SQL uniqueness for representation — keep unique scenarios here only."""

    @classmethod
    def _es_partner_vals(cls, env, vat="ESA12345674"):
        """Spanish country + VAT that passes ``base_vat`` checks (AF v2.0 / Odoo standard)."""
        return {
            "country_id": env.ref("base.es").id,
            "vat": vat,
        }

    def test_vat_validation_on_confirm(self):
        """Assembly TIN requirement and ``assembly.type.require_vat`` block invalid TIN."""
        assembly = self._create_assembly(name="Contract VAT asm")
        assembly.write({"attendance_require_partner_vat_confirm": True})
        assembly.action_generate_attendees()
        att = assembly.attendee_ids[0]
        for bad in (False, "/"):
            with self.subTest(tin=bad):
                att.partner_id.write({"vat": bad or False})
                with self.assertRaises(ValidationError):
                    att.action_confirm()
        att.partner_id.write(self._es_partner_vals(self.env, "ESA12345674"))
        att.action_confirm()
        self.assertEqual(att.attendee_state, "confirmed")

        assembly.write({"attendance_partner_vat_format_strict": True})
        att_b = assembly.attendee_ids.filtered(
            lambda a: a.attendee_state != "confirmed"
        )[0]
        att_b.partner_id.with_context(no_vat_validation=True).write({"vat": "NO"})
        with self.assertRaises(ValidationError):
            att_b.action_confirm()
        att_b.partner_id.write(self._es_partner_vals(self.env, "ESA12345674"))
        att_b.action_confirm()

        vt = self._create_vote_type(self.env, name="VT contract type vat")
        atype = self.env["assembly.type"].create(
            {
                "name": "Type contract vat",
                "code": "TCVAT_%s" % uuid.uuid4().hex[:10],
                "vote_type_ids": [(6, 0, vt.ids)],
                "partner_domain": "[]",
                "require_vat": True,
            }
        )
        partners = self._create_partners(self.env, 2, prefix="ContractTypeVat")
        domain = "[('id', 'in', %s)]" % partners.ids
        asm2 = self.env["assembly.assembly"].create(
            {
                "name": "Contract type VAT asm",
                "assembly_type_id": atype.id,
                "partner_domain": domain,
                "vote_type_ids": [(6, 0, vt.ids)],
            }
        )
        asm2.action_generate_attendees()
        att2 = asm2.attendee_ids[0]
        att2.partner_id.write({"vat": False})
        with self.assertRaises(ValidationError):
            att2.action_confirm()
        att2.partner_id.write(self._es_partner_vals(self.env, "ESA12345674"))
        att2.action_confirm()
        self.assertEqual(att2.attendee_state, "confirmed")

    def test_type_require_vat_applies_assembly_strict_format_when_flag_set(self):
        """``require_vat`` on type + ``attendance_partner_vat_format_strict`` on assembly."""
        vt = self._create_vote_type(self.env, name="VT strict type path")
        atype = self.env["assembly.type"].create(
            {
                "name": "Type strict path",
                "code": "TCSTP_%s" % uuid.uuid4().hex[:10],
                "vote_type_ids": [(6, 0, vt.ids)],
                "partner_domain": "[]",
                "require_vat": True,
            }
        )
        partners = self._create_partners(self.env, 1, prefix="StrictTypePath")
        domain = "[('id', 'in', %s)]" % partners.ids
        asm = self.env["assembly.assembly"].create(
            {
                "name": "Strict type-path asm",
                "assembly_type_id": atype.id,
                "partner_domain": domain,
                "vote_type_ids": [(6, 0, vt.ids)],
                "attendance_require_partner_vat_confirm": False,
                "attendance_partner_vat_format_strict": True,
            }
        )
        asm.action_generate_attendees()
        att = asm.attendee_ids[0]
        att.partner_id.with_context(no_vat_validation=True).write({"vat": "NO"})
        with self.assertRaises(ValidationError):
            att.action_confirm()
        att.partner_id.write(self._es_partner_vals(self.env, "ESA12345674"))
        att.action_confirm()
        self.assertEqual(att.attendee_state, "confirmed")

    def test_attendee_confirm_without_vat_when_assembly_type_require_vat_false(self):
        """If ``assembly.type.require_vat`` is false and assembly TIN flag is off, confirm needs no VAT."""
        assembly = self._create_assembly(name="Contract no type VAT asm")
        self.assertFalse(assembly.assembly_type_id.require_vat)
        self.assertFalse(assembly.attendance_require_partner_vat_confirm)
        assembly.action_generate_attendees()
        att = assembly.attendee_ids[0]
        att.partner_id.write({"vat": False})
        att.action_confirm()
        self.assertEqual(att.attendee_state, "confirmed")

    def test_strict_format_flag_alone_does_not_require_vat(self):
        """``attendance_partner_vat_format_strict`` only runs when a VAT requirement is active."""
        assembly = self._create_assembly(name="Strict alone asm")
        self.assertFalse(assembly.assembly_type_id.require_vat)
        assembly.write(
            {
                "attendance_require_partner_vat_confirm": False,
                "attendance_partner_vat_format_strict": True,
            }
        )
        assembly.action_generate_attendees()
        att = assembly.attendee_ids[0]
        att.partner_id.write({"vat": False})
        att.action_confirm()
        self.assertEqual(att.attendee_state, "confirmed")

    def test_representation_owner_unique_per_assembly(self):
        partners = self._create_partners(self.env, 3, prefix="ContractRep")
        domain = "[('id', 'in', %s)]" % partners.ids
        assembly, _agenda = self._create_assembly_with_agenda(
            name="Contract rep asm",
            partner_domain=domain,
        )
        Representation = self.env["assembly.representation"]
        Representation.create(
            {
                "assembly_id": assembly.id,
                "owner_partner_id": partners[0].id,
                "agent_partner_id": partners[1].id,
            }
        )
        with mute_logger("odoo.sql_db"):
            with self.assertRaises(Exception) as ctx:
                Representation.create(
                    {
                        "assembly_id": assembly.id,
                        "owner_partner_id": partners[0].id,
                        "agent_partner_id": partners[2].id,
                    }
                )
        err = str(ctx.exception).lower()
        self.assertTrue(
            "unique" in err or "duplicate" in err or "assembly_representation" in err,
            err,
        )

    def test_base_vat_invalid_rejected_on_confirm_when_tin_required(self):
        """AF v2.0: ``base_vat`` algorithms apply once TIN is required."""
        assembly = self._create_assembly(name="VAT std invalid asm")
        assembly.write({"attendance_require_partner_vat_confirm": True})
        assembly.action_generate_attendees()
        att = assembly.attendee_ids[0]
        att.partner_id.with_context(no_vat_validation=True).write(
            self._es_partner_vals(self.env, "ESA11111111")
        )
        with self.assertRaises(ValidationError):
            att.action_confirm()
