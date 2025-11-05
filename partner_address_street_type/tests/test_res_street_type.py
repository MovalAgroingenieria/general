# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from contextlib import contextmanager

from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError
from odoo.tools.misc import mute_logger

# Import SQL exception classes so we can catch DB-level integrity failures
try:
    from psycopg2.errors import NotNullViolation, UniqueViolation
except Exception:  # Fallback if driver changes
    NotNullViolation = Exception
    UniqueViolation = Exception


@contextmanager
def assert_orm_or_sql_error(testcase, *exc_classes):
    """
    Accept both ORM (ValidationError) and SQL (NotNullViolation/UniqueViolation) errors.
    This prevents the test case transaction from being aborted by an uncaught integrity error.
    """
    with mute_logger("odoo.sql_db"):
        try:
            yield
        except exc_classes:
            return
    testcase.fail(f"Expected one of: {', '.join(e.__name__ for e in exc_classes)}")


@tagged("post_install", "-at_install")
class TestResStreetType(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.StreetType = cls.env["res.street.type"]

        # Seed two street types
        cls.st1 = cls.StreetType.create({
            "name": "Avenida",
            "abbreviation": "Av.",
            # boolean defaults should apply
        })
        cls.st2 = cls.StreetType.create({
            "name": "Calle",
            "abbreviation": "C/",
            "show_in_list": False,
            "is_default": True,
            "active": True,
        })

    # ------------------------
    # Defaults & required fields
    # ------------------------

    def test_defaults_applied(self):
        """New records should get default boolean values."""
        st = self.StreetType.create({
            "name": "Carretera",
            "abbreviation": "Ct.",
        })
        self.assertTrue(st.show_in_list)
        self.assertFalse(st.is_default)
        self.assertTrue(st.active)

    def test_required_name(self):
        """Creating without a name must fail (ORM validation or SQL NOT NULL)."""
        with assert_orm_or_sql_error(self, ValidationError, NotNullViolation):
            self.StreetType.create({
                "abbreviation": "XX",
            })

    def test_required_abbreviation(self):
        """Creating without an abbreviation must fail (ORM validation or SQL NOT NULL)."""
        with assert_orm_or_sql_error(self, ValidationError, NotNullViolation):
            self.StreetType.create({
                "name": "Pasaje",
            })

    # ------------------------
    # SQL constraint: unique(name)
    # ------------------------

    def test_unique_name_constraint_on_create(self):
        """Creating a duplicate name must fail (ORM ValidationError or SQL UNIQUE)."""
        with assert_orm_or_sql_error(self, ValidationError, UniqueViolation):
            self.StreetType.create({
                "name": "Avenida",            # duplicate of st1
                "abbreviation": "Avenida.",
            })

    def test_unique_name_constraint_on_write(self):
        """
        Renaming to an existing name must fail (ORM ValidationError or SQL UNIQUE).
        We wrap the write + flush in a DB savepoint so the outer transaction
        remains usable after the integrity error is raised.
        """
        with assert_orm_or_sql_error(self, ValidationError, UniqueViolation):
            # The uniqueness violation happens here; the savepoint will roll back
            # only these statements, keeping the main transaction valid.
            with self.env.cr.savepoint():
                self.st2.write({"name": "Avenida"})  # already used by st1
                self.env.cr.flush()

        # Extra safety: verify no duplicates remained (outer tx is still clean)
        cnt = self.StreetType.search_count([("name", "=", "Avenida")])
        self.assertEqual(cnt, 1)

    # ------------------------
    # name_get behavior
    # ------------------------

    def test_name_get_without_context_in_combo(self):
        """When 'in_combo' is False, name_get must return only the abbreviation."""
        ng1 = self.st1.name_get()
        self.assertEqual(ng1, [(self.st1.id, "Av.")])

        ng2 = (self.st1 | self.st2).name_get()
        self.assertEqual(ng2, [
            (self.st1.id, "Av."),
            (self.st2.id, "C/"),
        ])

    def test_name_get_with_context_in_combo_true(self):
        """When context['in_combo']=True, name_get must return 'abbr - name'."""
        st_ctx = self.StreetType.with_context(in_combo=True)
        ng1 = st_ctx.browse(self.st1.id).name_get()
        self.assertEqual(ng1, [(self.st1.id, "Av. - Avenida")])

        ng2 = st_ctx.browse((self.st1 | self.st2).ids).name_get()
        self.assertEqual(ng2, [
            (self.st1.id, "Av. - Avenida"),
            (self.st2.id, "C/ - Calle"),
        ])

    def test_name_get_works_with_inactive_records_if_browsed(self):
        """
        Even if a record is inactive, name_get should work if the record is explicitly browsed.
        (Combo domains may exclude inactive, but name_get itself must not crash.)
        """
        self.st2.active = False
        ng = self.st2.name_get()
        self.assertEqual(ng, [(self.st2.id, "C/")])

        ng_combo = self.StreetType.with_context(in_combo=True).browse(self.st2.id).name_get()
        self.assertEqual(ng_combo, [(self.st2.id, "C/ - Calle")])
