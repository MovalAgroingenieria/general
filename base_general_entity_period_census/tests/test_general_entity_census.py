# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from datetime import date

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestGeneralEntityCensus(TransactionCase):
    """Tests for the census model, state machine, and constraints."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Census = cls.env["general.entity.census"]
        cls.CensusLine = cls.env["general.entity.census.line"]
        cls.Additional = cls.env["general.entity.census.additional"]

        # Create primary entity
        cls.primary = cls.env["res.partner"].create(
            {
                "name": "Test Entity Primary",
                "is_primary_entity": True,
                "company_type": "company",
                "entity_global_code": 1001,
            }
        )

        # Create secondary members
        cls.member_a = cls.env["res.partner"].create(
            {
                "name": "Member A",
                "is_secondary_entity": True,
                "entity_global_code": 2001,
            }
        )
        cls.member_b = cls.env["res.partner"].create(
            {
                "name": "Member B",
                "is_secondary_entity": True,
                "entity_global_code": 2002,
            }
        )
        cls.member_c = cls.env["res.partner"].create(
            {
                "name": "Member C",
                "is_secondary_entity": True,
                "entity_global_code": 2003,
            }
        )

        # Create entity members (for generate wizard)
        cls.entity_member_a = cls.env["general.entity.member"].create(
            {
                "primary_partner_id": cls.primary.id,
                "member_partner_id": cls.member_a.id,
                "member_code_in_entity": "T-M01",
            }
        )
        cls.entity_member_b = cls.env["general.entity.member"].create(
            {
                "primary_partner_id": cls.primary.id,
                "member_partner_id": cls.member_b.id,
                "member_code_in_entity": "T-M02",
            }
        )
        cls.entity_member_c = cls.env["general.entity.member"].create(
            {
                "primary_partner_id": cls.primary.id,
                "member_partner_id": cls.member_c.id,
                "member_code_in_entity": "T-M03",
            }
        )

        # Create a product for distribution
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Water",
                "type": "service",
            }
        )

        # Create base census
        cls.census = cls.Census.create(
            {
                "primary_partner_id": cls.primary.id,
                "period_date": date(2026, 1, 1),
                "period_type": "monthly",
                "distribution_product_id": cls.product.id,
                "distribution_amount_day": 0.5,
            }
        )

    # ===== Constraint Tests =====

    def test_period_date_must_be_first_of_month(self):
        """Period date must be the first day of the month."""
        with self.assertRaises(ValidationError):
            self.Census.create(
                {
                    "primary_partner_id": self.primary.id,
                    "period_date": date(2026, 3, 15),
                    "period_type": "monthly",
                }
            )

    def test_unique_entity_period(self):
        """Cannot create two censuses for same entity + period."""
        with self.assertRaises(Exception):
            self.Census.create(
                {
                    "primary_partner_id": self.primary.id,
                    "period_date": date(2026, 1, 1),
                    "period_type": "monthly",
                }
            )

    def test_unique_member_per_census(self):
        """A member can only appear once per census."""
        self.CensusLine.create(
            {
                "census_id": self.census.id,
                "member_partner_id": self.member_a.id,
                "shares": 10.0,
            }
        )
        with self.assertRaises(Exception):
            self.CensusLine.create(
                {
                    "census_id": self.census.id,
                    "member_partner_id": self.member_a.id,
                    "shares": 5.0,
                }
            )

    def test_custom_period_dates_constraint(self):
        """Custom periods must have end_date >= start_date."""
        with self.assertRaises(ValidationError):
            self.Census.create(
                {
                    "primary_partner_id": self.primary.id,
                    "period_date": date(2026, 6, 1),
                    "period_type": "custom",
                    "period_start_date": date(2026, 6, 15),
                    "period_end_date": date(2026, 6, 10),
                }
            )

    def test_custom_period_dates_valid(self):
        """Custom periods with valid dates should work."""
        census = self.Census.create(
            {
                "primary_partner_id": self.primary.id,
                "period_date": date(2026, 6, 1),
                "period_type": "custom",
                "period_start_date": date(2026, 6, 1),
                "period_end_date": date(2026, 6, 20),
            }
        )
        self.assertEqual(census.period_days, 20)

    # ===== Period Days Calculation =====

    def test_period_days_monthly(self):
        """Monthly census should calculate real days in month."""
        self.assertEqual(self.census.period_days, 31)  # January

    def test_period_days_daily(self):
        """Daily period = 1 day."""
        census = self.Census.create(
            {
                "primary_partner_id": self.primary.id,
                "period_date": date(2026, 3, 1),
                "period_type": "daily",
            }
        )
        self.assertEqual(census.period_days, 1)

    def test_period_days_quarterly(self):
        """Quarterly = 90 days."""
        census = self.Census.create(
            {
                "primary_partner_id": self.primary.id,
                "period_date": date(2026, 4, 1),
                "period_type": "quarterly",
            }
        )
        self.assertEqual(census.period_days, 90)

    def test_period_days_annual(self):
        """Annual = 365 (or 366 for leap year)."""
        census = self.Census.create(
            {
                "primary_partner_id": self.primary.id,
                "period_date": date(2026, 7, 1),
                "period_type": "annual",
            }
        )
        self.assertEqual(census.period_days, 365)

    # ===== State Machine =====

    def test_lock_draft_census(self):
        """Can lock a draft census."""
        self.census.action_lock()
        self.assertEqual(self.census.state, "locked")

    def test_unlock_locked_census(self):
        """Can unlock a locked census."""
        self.census.action_lock()
        self.census.action_unlock()
        self.assertEqual(self.census.state, "draft")

    def test_cannot_lock_already_locked(self):
        """Cannot lock an already locked census."""
        self.census.action_lock()
        with self.assertRaises(UserError):
            self.census.action_lock()

    def test_cannot_unlock_draft(self):
        """Cannot unlock a draft census."""
        with self.assertRaises(UserError):
            self.census.action_unlock()

    # ===== Active / Archive =====

    def test_active_field_default(self):
        """Census is active by default."""
        self.assertTrue(self.census.active)

    def test_archive_census(self):
        """Can archive a census."""
        self.census.active = False
        self.assertFalse(self.census.active)
        # Archived census not found in default search
        found = self.Census.search([("id", "=", self.census.id)])
        self.assertFalse(found)

    # ===== Distribution Calculations =====

    def test_distribution_amount_period(self):
        """amount_period = amount_day × period_days."""
        # January: 31 days, amount_day = 0.5
        self.assertAlmostEqual(self.census.distribution_amount_period, 15.5, places=4)

    def test_distribution_inverse_period(self):
        """Setting amount_period should calculate amount_day."""
        self.census.distribution_amount_period = 31.0
        self.assertAlmostEqual(self.census.distribution_amount_day, 1.0, places=4)

    def test_line_base_distributed_qty(self):
        """base_distributed_qty = shares × amount_day × period_days."""
        line = self.CensusLine.create(
            {
                "census_id": self.census.id,
                "member_partner_id": self.member_a.id,
                "shares": 10.0,
            }
        )
        # 10 × 0.5 × 31 = 155.0
        self.assertAlmostEqual(line.base_distributed_qty, 155.0, places=4)

    def test_line_distributed_qty_with_additional(self):
        """distributed_qty = base + additional."""
        line = self.CensusLine.create(
            {
                "census_id": self.census.id,
                "member_partner_id": self.member_a.id,
                "shares": 10.0,
            }
        )
        self.Additional.create(
            {
                "census_line_id": line.id,
                "qty": 3.0,
                "note": "Extra",
            }
        )
        self.Additional.create(
            {
                "census_line_id": line.id,
                "qty": -1.0,
                "note": "Correction",
            }
        )
        line.invalidate_recordset()
        # base: 155.0, additional: 3.0 - 1.0 = 2.0
        self.assertAlmostEqual(line.distributed_qty, 157.0, places=4)

    def test_distribution_total(self):
        """Census total = sum of line distributed_qty."""
        self.CensusLine.create(
            {
                "census_id": self.census.id,
                "member_partner_id": self.member_a.id,
                "shares": 10.0,
            }
        )
        self.CensusLine.create(
            {
                "census_id": self.census.id,
                "member_partner_id": self.member_b.id,
                "shares": 5.0,
            }
        )
        self.census.invalidate_recordset()
        # A: 10×0.5×31=155, B: 5×0.5×31=77.5 → total=232.5
        self.assertAlmostEqual(self.census.distribution_total, 232.5, places=4)

    def test_total_shares(self):
        """Census total_shares = sum of line shares."""
        self.CensusLine.create(
            {
                "census_id": self.census.id,
                "member_partner_id": self.member_a.id,
                "shares": 10.0,
            }
        )
        self.CensusLine.create(
            {
                "census_id": self.census.id,
                "member_partner_id": self.member_b.id,
                "shares": 5.0,
            }
        )
        self.census.invalidate_recordset()
        self.assertAlmostEqual(self.census.total_shares, 15.0, places=4)


class TestCensusLineProtections(TransactionCase):
    """Tests for write/delete protections on census lines."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Census = cls.env["general.entity.census"]
        cls.CensusLine = cls.env["general.entity.census.line"]
        cls.Additional = cls.env["general.entity.census.additional"]

        cls.primary = cls.env["res.partner"].create(
            {
                "name": "Test Entity Write",
                "is_primary_entity": True,
                "entity_global_code": 3001,
            }
        )
        cls.member = cls.env["res.partner"].create(
            {
                "name": "Member Write",
                "is_secondary_entity": True,
                "entity_global_code": 3101,
            }
        )

        cls.census = cls.Census.create(
            {
                "primary_partner_id": cls.primary.id,
                "period_date": date(2026, 1, 1),
                "period_type": "monthly",
            }
        )
        cls.line = cls.CensusLine.create(
            {
                "census_id": cls.census.id,
                "member_partner_id": cls.member.id,
                "shares": 10.0,
            }
        )

    # ===== Line State Protections =====

    def test_validated_line_cannot_modify_shares(self):
        """Cannot modify shares on a validated line."""
        self.line.action_validate()
        with self.assertRaises(UserError):
            self.line.write({"shares": 20.0})

    def test_validated_line_can_modify_note(self):
        """Can modify note on a validated line."""
        self.line.action_validate()
        self.line.write({"note": "Updated note"})
        self.assertEqual(self.line.note, "Updated note")

    def test_validated_line_cannot_delete(self):
        """Cannot delete a validated line."""
        self.line.action_validate()
        with self.assertRaises(UserError):
            self.line.unlink()

    def test_validate_unvalidate_cycle(self):
        """Can validate and then unvalidate a line."""
        self.line.action_validate()
        self.assertEqual(self.line.state, "validated")
        self.line.action_unvalidate()
        self.assertEqual(self.line.state, "draft")

    # ===== Locked Census Protections =====

    def test_locked_census_cannot_modify_shares(self):
        """Cannot modify shares when census is locked."""
        self.census.action_lock()
        with self.assertRaises(UserError):
            self.line.write({"shares": 20.0})

    def test_locked_census_can_modify_note(self):
        """Can modify note when census is locked."""
        self.census.action_lock()
        self.line.write({"note": "Note on locked"})
        self.assertEqual(self.line.note, "Note on locked")

    def test_locked_census_cannot_delete_line(self):
        """Cannot delete a line from a locked census."""
        self.census.action_lock()
        with self.assertRaises(UserError):
            self.line.unlink()

    def test_locked_census_cannot_validate(self):
        """Cannot validate lines when census is locked."""
        self.census.action_lock()
        with self.assertRaises(UserError):
            self.line.action_validate()

    # ===== Additional Movement Protections =====

    def test_additional_blocked_when_line_validated(self):
        """Cannot create additional when line is validated."""
        self.line.action_validate()
        with self.assertRaises(UserError):
            self.Additional.create(
                {
                    "census_line_id": self.line.id,
                    "qty": 5.0,
                }
            )

    def test_additional_blocked_when_census_locked(self):
        """Cannot create additional when census is locked."""
        self.census.action_lock()
        with self.assertRaises(UserError):
            self.Additional.create(
                {
                    "census_line_id": self.line.id,
                    "qty": 5.0,
                }
            )

    def test_additional_delete_blocked_when_validated(self):
        """Cannot delete additional when line is validated."""
        addtnl = self.Additional.create(
            {
                "census_line_id": self.line.id,
                "qty": 5.0,
            }
        )
        self.line.action_validate()
        with self.assertRaises(UserError):
            addtnl.unlink()

    # ===== Mass Validate / Unvalidate =====

    def test_mass_validate_all_lines(self):
        """Validate all draft lines at once."""
        member_b = self.env["res.partner"].create(
            {
                "name": "Member Mass B",
                "is_secondary_entity": True,
                "entity_global_code": 4001,
            }
        )
        line_b = self.CensusLine.create(
            {
                "census_id": self.census.id,
                "member_partner_id": member_b.id,
                "shares": 5.0,
            }
        )
        self.census.action_validate_all_lines()
        self.assertEqual(self.line.state, "validated")
        self.assertEqual(line_b.state, "validated")

    def test_mass_unvalidate_all_lines(self):
        """Unvalidate all validated lines at once."""
        self.line.action_validate()
        self.census.action_unvalidate_all_lines()
        self.assertEqual(self.line.state, "draft")

    def test_mass_validate_blocked_when_locked(self):
        """Cannot mass validate when census is locked."""
        self.census.action_lock()
        with self.assertRaises(UserError):
            self.census.action_validate_all_lines()


class TestCensusSharesChanged(TransactionCase):
    """Tests for shares_changed detection."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Census = cls.env["general.entity.census"]
        cls.CensusLine = cls.env["general.entity.census.line"]

        cls.primary = cls.env["res.partner"].create(
            {
                "name": "Test Entity SC",
                "is_primary_entity": True,
                "entity_global_code": 5001,
            }
        )
        cls.member = cls.env["res.partner"].create(
            {
                "name": "Member SC",
                "is_secondary_entity": True,
                "entity_global_code": 5101,
            }
        )

    def test_shares_changed_detection(self):
        """shares_changed is True when different from previous line."""
        census_jan = self.Census.create(
            {
                "primary_partner_id": self.primary.id,
                "period_date": date(2026, 1, 1),
                "period_type": "monthly",
            }
        )
        line_jan = self.CensusLine.create(
            {
                "census_id": census_jan.id,
                "member_partner_id": self.member.id,
                "shares": 10.0,
            }
        )

        census_feb = self.Census.create(
            {
                "primary_partner_id": self.primary.id,
                "period_date": date(2026, 2, 1),
                "period_type": "monthly",
            }
        )
        line_feb = self.CensusLine.create(
            {
                "census_id": census_feb.id,
                "member_partner_id": self.member.id,
                "shares": 15.0,
                "previous_line_id": line_jan.id,
            }
        )
        self.assertTrue(line_feb.shares_changed)

    def test_shares_not_changed(self):
        """shares_changed is False when same as previous."""
        census_jan = self.Census.create(
            {
                "primary_partner_id": self.primary.id,
                "period_date": date(2026, 3, 1),
                "period_type": "monthly",
            }
        )
        line_jan = self.CensusLine.create(
            {
                "census_id": census_jan.id,
                "member_partner_id": self.member.id,
                "shares": 10.0,
            }
        )

        census_feb = self.Census.create(
            {
                "primary_partner_id": self.primary.id,
                "period_date": date(2026, 4, 1),
                "period_type": "monthly",
            }
        )
        line_feb = self.CensusLine.create(
            {
                "census_id": census_feb.id,
                "member_partner_id": self.member.id,
                "shares": 10.0,
                "previous_line_id": line_jan.id,
            }
        )
        self.assertFalse(line_feb.shares_changed)


class TestCopyToNextPeriod(TransactionCase):
    """Tests for the copy_to_next_period action."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Census = cls.env["general.entity.census"]
        cls.CensusLine = cls.env["general.entity.census.line"]
        cls.Additional = cls.env["general.entity.census.additional"]

        cls.primary = cls.env["res.partner"].create(
            {
                "name": "Test Entity Copy",
                "is_primary_entity": True,
                "entity_global_code": 6001,
            }
        )
        cls.member_a = cls.env["res.partner"].create(
            {
                "name": "Member Copy A",
                "is_secondary_entity": True,
                "entity_global_code": 6101,
            }
        )
        cls.member_b = cls.env["res.partner"].create(
            {
                "name": "Member Copy B",
                "is_secondary_entity": True,
                "entity_global_code": 6102,
            }
        )

    def test_copy_monthly(self):
        """Copy monthly census advances by 1 month."""
        census = self.Census.create(
            {
                "primary_partner_id": self.primary.id,
                "period_date": date(2026, 1, 1),
                "period_type": "monthly",
                "distribution_amount_day": 1.0,
            }
        )
        self.CensusLine.create(
            {
                "census_id": census.id,
                "member_partner_id": self.member_a.id,
                "shares": 10.0,
            }
        )

        result = census.action_copy_to_next_period()
        new_census = self.Census.browse(result["res_id"])

        self.assertEqual(new_census.period_date, date(2026, 2, 1))
        self.assertEqual(len(new_census.line_ids), 1)
        self.assertEqual(new_census.line_ids.shares, 10.0)
        self.assertEqual(
            new_census.line_ids.previous_line_id.id,
            census.line_ids.id,
        )
        self.assertAlmostEqual(new_census.distribution_amount_day, 1.0, places=4)

    def test_copy_with_additional(self):
        """Copy includes additional movements."""
        census = self.Census.create(
            {
                "primary_partner_id": self.primary.id,
                "period_date": date(2026, 5, 1),
                "period_type": "monthly",
            }
        )
        line = self.CensusLine.create(
            {
                "census_id": census.id,
                "member_partner_id": self.member_a.id,
                "shares": 5.0,
            }
        )
        self.Additional.create(
            {
                "census_line_id": line.id,
                "qty": 2.0,
                "note": "Extra",
            }
        )

        result = census.action_copy_to_next_period()
        new_census = self.Census.browse(result["res_id"])
        new_line = new_census.line_ids

        self.assertEqual(len(new_line.additional_ids), 1)
        self.assertAlmostEqual(new_line.additional_ids.qty, 2.0, places=4)

    def test_copy_fails_if_target_exists(self):
        """Cannot copy if census already exists in target period."""
        self.Census.create(
            {
                "primary_partner_id": self.primary.id,
                "period_date": date(2026, 8, 1),
                "period_type": "monthly",
            }
        )
        census = self.Census.create(
            {
                "primary_partner_id": self.primary.id,
                "period_date": date(2026, 7, 1),
                "period_type": "monthly",
            }
        )
        self.CensusLine.create(
            {
                "census_id": census.id,
                "member_partner_id": self.member_a.id,
                "shares": 1.0,
            }
        )
        with self.assertRaises(UserError):
            census.action_copy_to_next_period()


class TestCensusWizards(TransactionCase):
    """Tests for the generate lines and partial copy wizards."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Census = cls.env["general.entity.census"]
        cls.CensusLine = cls.env["general.entity.census.line"]
        cls.GenerateWiz = cls.env["census.generate.lines.wizard"]
        cls.PartialCopyWiz = cls.env["census.partial.copy.wizard"]

        cls.primary = cls.env["res.partner"].create(
            {
                "name": "Test Entity Wizard",
                "is_primary_entity": True,
                "entity_global_code": 7001,
            }
        )
        cls.member_a = cls.env["res.partner"].create(
            {
                "name": "Wizard Member A",
                "is_secondary_entity": True,
                "entity_global_code": 7101,
            }
        )
        cls.member_b = cls.env["res.partner"].create(
            {
                "name": "Wizard Member B",
                "is_secondary_entity": True,
                "entity_global_code": 7102,
            }
        )
        cls.member_c = cls.env["res.partner"].create(
            {
                "name": "Wizard Member C",
                "is_secondary_entity": True,
                "entity_global_code": 7103,
            }
        )

        # Create entity memberships
        cls.env["general.entity.member"].create(
            {
                "primary_partner_id": cls.primary.id,
                "member_partner_id": cls.member_a.id,
                "member_code_in_entity": "WZ-M01",
            }
        )
        cls.env["general.entity.member"].create(
            {
                "primary_partner_id": cls.primary.id,
                "member_partner_id": cls.member_b.id,
                "member_code_in_entity": "WZ-M02",
            }
        )
        cls.env["general.entity.member"].create(
            {
                "primary_partner_id": cls.primary.id,
                "member_partner_id": cls.member_c.id,
                "member_code_in_entity": "WZ-M03",
            }
        )

        cls.census = cls.Census.create(
            {
                "primary_partner_id": cls.primary.id,
                "period_date": date(2026, 1, 1),
                "period_type": "monthly",
            }
        )

    def test_generate_lines_creates_all_members(self):
        """Generate wizard creates lines for all active members."""
        wizard = self.GenerateWiz.with_context(active_id=self.census.id).create({})
        wizard.action_generate()

        self.assertEqual(len(self.census.line_ids), 3)
        member_ids = self.census.line_ids.mapped("member_partner_id").ids
        self.assertIn(self.member_a.id, member_ids)
        self.assertIn(self.member_b.id, member_ids)
        self.assertIn(self.member_c.id, member_ids)

    def test_generate_lines_skips_existing(self):
        """Generate wizard skips members already in census."""
        # Add member A manually first
        self.CensusLine.create(
            {
                "census_id": self.census.id,
                "member_partner_id": self.member_a.id,
                "shares": 10.0,
            }
        )

        wizard = self.GenerateWiz.with_context(active_id=self.census.id).create({})
        wizard.action_generate()

        # Should be 3 total (1 existing + 2 new)
        self.assertEqual(len(self.census.line_ids), 3)

    def test_generate_lines_blocked_when_locked(self):
        """Cannot generate lines when census is locked."""
        self.census.action_lock()
        wizard = self.GenerateWiz.with_context(active_id=self.census.id).create({})
        with self.assertRaises(UserError):
            wizard.action_generate()

    def test_partial_copy_selected_members(self):
        """Partial copy only copies selected lines."""
        line_a = self.CensusLine.create(
            {
                "census_id": self.census.id,
                "member_partner_id": self.member_a.id,
                "shares": 10.0,
            }
        )
        self.CensusLine.create(
            {
                "census_id": self.census.id,
                "member_partner_id": self.member_b.id,
                "shares": 5.0,
            }
        )

        wizard = self.PartialCopyWiz.with_context(active_id=self.census.id).create(
            {
                "census_id": self.census.id,
                "line_ids": [(6, 0, [line_a.id])],
            }
        )
        result = wizard.action_copy()

        new_census = self.Census.browse(result["res_id"])
        self.assertEqual(len(new_census.line_ids), 1)
        self.assertEqual(
            new_census.line_ids.member_partner_id.id,
            self.member_a.id,
        )

    def test_partial_copy_no_lines_error(self):
        """Partial copy with no lines selected raises error."""
        wizard = self.PartialCopyWiz.with_context(active_id=self.census.id).create(
            {
                "census_id": self.census.id,
                "line_ids": [(6, 0, [])],
            }
        )
        with self.assertRaises(UserError):
            wizard.action_copy()


class TestCensusPartnerExtension(TransactionCase):
    """Tests for res.partner census fields and actions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Census = cls.env["general.entity.census"]
        cls.CensusLine = cls.env["general.entity.census.line"]

        cls.primary = cls.env["res.partner"].create(
            {
                "name": "Test Entity Partner",
                "is_primary_entity": True,
                "entity_global_code": 8001,
            }
        )
        cls.member = cls.env["res.partner"].create(
            {
                "name": "Member Partner",
                "is_secondary_entity": True,
                "entity_global_code": 8101,
            }
        )

        cls.census = cls.Census.create(
            {
                "primary_partner_id": cls.primary.id,
                "period_date": date(2026, 1, 1),
                "period_type": "monthly",
            }
        )
        cls.CensusLine.create(
            {
                "census_id": cls.census.id,
                "member_partner_id": cls.member.id,
                "shares": 10.0,
            }
        )

    def test_primary_census_count(self):
        """Primary entity shows correct census count."""
        self.assertEqual(self.primary.census_count, 1)

    def test_primary_census_line_count(self):
        """Primary entity shows correct census line count."""
        self.assertEqual(self.primary.primary_census_line_count, 1)

    def test_secondary_census_line_count(self):
        """Secondary member shows correct census line count."""
        self.assertEqual(self.member.census_line_count, 1)

    def test_action_view_censuses(self):
        """Action returns correct domain for primary entity."""
        action = self.primary.action_view_censuses()
        self.assertEqual(
            action["domain"],
            [("primary_partner_id", "=", self.primary.id)],
        )

    def test_cascade_delete_primary(self):
        """Deleting primary entity cascades to censuses."""
        census_id = self.census.id
        self.primary.unlink()
        found = self.Census.search([("id", "=", census_id)])
        self.assertFalse(found)
