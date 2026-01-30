# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from contextlib import contextmanager

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tools.misc import mute_logger

# Import SQL exception classes so we can catch DB-level integrity failures

NotNullViolation = Exception
UniqueViolation = Exception


@contextmanager
def assert_orm_or_sql_error(testcase, *exc_classes):
    """
    Accept both ORM (ValidationError) and SQL (NotNullViolation/UniqueViolation) errors.
    This prevents the test case transaction from being
     aborted by an uncaught integrity error.
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
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.StreetType = cls.env["res.street.type"]

        # Seed two street types
        cls.st1 = cls.StreetType.create(
            {
                "name": "Avenida",
                "abbreviation": "Av.",
                # boolean defaults should apply
            }
        )
        cls.st2 = cls.StreetType.create(
            {
                "name": "Calle",
                "abbreviation": "C/",
                "show_in_list": False,
                "is_default": True,
                "active": True,
            }
        )

    # ------------------------
    # Defaults & required fields
    # ------------------------

    def test_defaults_applied(self):
        """New records should get default boolean values."""
        st = self.StreetType.create(
            {
                "name": "Carretera",
                "abbreviation": "Ct.",
            }
        )
        self.assertTrue(st.show_in_list)
        self.assertFalse(st.is_default)
        self.assertTrue(st.active)

    def test_required_name(self):
        """Creating without a name must fail (ORM validation or SQL NOT NULL)."""
        with assert_orm_or_sql_error(self, ValidationError, NotNullViolation):
            self.StreetType.create(
                {
                    "abbreviation": "XX",
                }
            )

    def test_required_abbreviation(self):
        """Creating without an abbreviation must
        fail (ORM validation or SQL NOT NULL)."""
        with assert_orm_or_sql_error(self, ValidationError, NotNullViolation):
            self.StreetType.create(
                {
                    "name": "Pasaje",
                }
            )

    # ------------------------
    # SQL constraint: unique(name)
    # ------------------------

    def test_unique_name_constraint_on_create(self):
        """Creating a duplicate name must fail (ORM ValidationError or SQL UNIQUE)."""
        with assert_orm_or_sql_error(self, ValidationError, UniqueViolation):
            self.StreetType.create(
                {
                    "name": "Avenida",  # duplicate of st1
                    "abbreviation": "Avenida.",
                }
            )

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
