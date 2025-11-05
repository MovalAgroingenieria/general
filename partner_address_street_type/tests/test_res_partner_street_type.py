# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestResPartnerStreetType(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.StreetType = cls.env["res.street.type"]
        cls.IrConfig = cls.env["ir.config_parameter"].sudo()

        # Default config: show long name
        cls.param_key = "partner_address_street_type.street_type_shown"
        cls.IrConfig.set_param(cls.param_key, "long")

        # Two sample street types
        cls.type_long = cls.StreetType.create({
            "name": "Avenida",
            "abbreviation": "Av.",
            "show_in_list": True,
            "is_default": True,
            "active": True,
        })
        cls.type_short = cls.StreetType.create({
            "name": "Calle",
            "abbreviation": "C/",
            "show_in_list": True,
            "is_default": False,
            "active": True,
        })

    # ------------------------
    # Defaults & address fields
    # ------------------------

    def test_default_street_type_id_picks_default_and_visible(self):
        """_default_street_type_id should pick is_default=True & show_in_list=True."""
        default_id = self.Partner._default_street_type_id()
        self.assertEqual(default_id, self.type_long.id)

    def test_default_street_type_id_returns_zero_when_no_match(self):
        """If no street type matches (is_default & show_in_list), return 0."""
        # Make sure no record matches the default criteria
        self.type_long.write({"is_default": False})
        self.type_short.write({"is_default": False})
        # Also ensure show_in_list off for safety
        self.type_long.write({"show_in_list": False})
        self.type_short.write({"show_in_list": False})

        default_id = self.Partner._default_street_type_id()
        self.assertEqual(default_id, 0)

        # Restore for other tests
        self.type_long.write({"is_default": True, "show_in_list": True})

    def test_address_fields_contains_custom_fields(self):
        """_address_fields must include street_type_id and street_type_shown."""
        fields = self.Partner._address_fields()
        self.assertIn("street_type_id", fields)
        self.assertIn("street_type_shown", fields)

    # ------------------------
    # Compute: street_type_shown
    # ------------------------

    def _force_param(self, value):
        self.IrConfig.set_param(self.param_key, value)

    def _recompute(self, record):
        # Invalidate cache so the non-stored compute is re-evaluated on read
        record.invalidate_recordset(["street_type_shown"])

    def test_compute_street_type_shown_long(self):
        """When param=long, show the street type full name."""
        self._force_param("long")
        p = self.Partner.create({"name": "P1", "street_type_id": self.type_short.id})
        self._recompute(p)
        self.assertEqual(p.street_type_shown, "Calle")

    def test_compute_street_type_shown_short(self):
        """When param=short, show the abbreviation."""
        self._force_param("short")
        p = self.Partner.create({"name": "P2", "street_type_id": self.type_short.id})
        self._recompute(p)
        self.assertEqual(p.street_type_shown, "C/")

    def test_compute_street_type_shown_not_show(self):
        """When param=not_show (or other), show empty string."""
        self._force_param("not_show")
        p = self.Partner.create({"name": "P3", "street_type_id": self.type_short.id})
        self._recompute(p)
        self.assertEqual(p.street_type_shown, "")

    def test_compute_street_type_shown_empty_if_no_street_type(self):
        """If partner has no street_type_id, computed value must be empty."""
        self._force_param("long")
        p = self.Partner.create({"name": "NoStreetType"})
        self._recompute(p)
        self.assertEqual(p.street_type_shown, "Avenida")

    # ------------------------
    # Create / Write behavior
    # ------------------------

    def test_create_sets_street_type_shown_respecting_param(self):
        """create() should set street_type_shown (even if compute is non-stored)."""
        # long
        self._force_param("long")
        p_long = self.Partner.create({
            "name": "CLong",
            "street_type_id": self.type_short.id,
        })
        self.assertEqual(p_long.street_type_shown, "Calle")

        # short
        self._force_param("short")
        p_short = self.Partner.create({
            "name": "CShort",
            "street_type_id": self.type_long.id,
        })
        self.assertEqual(p_short.street_type_shown, "Av.")

        # not_show
        self._force_param("not_show")
        p_none = self.Partner.create({
            "name": "CNone",
            "street_type_id": self.type_long.id,
        })
        self.assertEqual(p_none.street_type_shown, "")

    def test_write_updates_street_type_shown_when_street_type_changes(self):
        """
        write() should update street_type_shown when street_type_id is changed,
        according to the current config parameter.
        """
        self._force_param("long")
        partner = self.Partner.create({
            "name": "W1",
            "street_type_id": self.type_long.id,
        })
        self.assertEqual(partner.street_type_shown, "Avenida")

        # Change to another type with param=short
        self._force_param("short")
        partner.write({"street_type_id": self.type_short.id})
        self.assertEqual(partner.street_type_shown, "C/")

        # Change with param=not_show
        self._force_param("not_show")
        partner.write({"street_type_id": self.type_long.id})
        self.assertEqual(partner.street_type_shown, "")

    def test_write_does_not_fail_if_street_type_cleared(self):
        """
        If street_type_id is set to False, write() should not crash and
        street_type_shown should become empty on next compute.
        """
        self._force_param("long")
        partner = self.Partner.create({
            "name": "W2",
            "street_type_id": self.type_long.id,
        })
        # Clear the m2o
        partner.write({"street_type_id": False})
        # Compute method sets empty when no street_type_id
        self._recompute(partner)
        self.assertEqual(partner.street_type_shown, "")
