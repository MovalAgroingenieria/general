# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase, tagged
from psycopg2 import sql


@tagged("post_install", "-at_install")
class TestResPartnerBankConstraint(TransactionCase):
    """Validate that the customization disables the unique
    constraint on bank accounts."""

    def setUp(self):  # pylint: disable=invalid-name
        super().setUp()
        self.partner = self.env["res.partner"]
        self.bank = self.env["res.partner.bank"]

        # Create two partners to associate bank accounts to.
        self.partner_1 = self.partner.create({"name": "Partner A"})
        self.partner_2 = self.partner.create({"name": "Partner B"})

        # Use the same account number for both records to check duplicates.
        self.same_acc_number = "ES7620770024003102575766"

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------

    def _get_constraint_type(self, table_name, constraint_name):
        """
        Return the PostgreSQL constraint type for the given table/constraint.
        Expected values: 'c' (CHECK), 'u' (UNIQUE), 'p' (PRIMARY KEY), etc.
        """
        query = sql.SQL(
            """
            SELECT c.contype
              FROM pg_constraint c
              JOIN pg_class r ON r.oid = c.conrelid
              JOIN pg_namespace n ON n.oid = r.relnamespace
             WHERE r.relname = %s
               AND c.conname = %s
            """
        )
        self.env.cr.execute(query, (table_name, constraint_name))
        row = self.env.cr.fetchone()
        return row[0] if row else None

    # ---------------------------------------------------------------------
    # Tests
    # ---------------------------------------------------------------------

    def test_no_unique_constraint_on_acc_number_and_optional_check(self):
        """
        Robust check:
        - Ensure there is NO UNIQUE constraint on res_partner_bank(acc_number).
        - If a constraint named 'unique_number' exists, ensure it's a CHECK.
        """
        # 1) NO UNIQUE on acc_number
        self.env.cr.execute(
            """
            SELECT c.conname,
                   array_agg(a.attname ORDER BY a.attnum) AS cols
            FROM pg_constraint c
                     JOIN pg_class r ON r.oid = c.conrelid
                     JOIN pg_namespace n ON n.oid = r.relnamespace
                     JOIN unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord) ON TRUE
                     JOIN pg_attribute a ON a.attrelid = r.oid AND a.attnum = k.attnum
            WHERE r.relname = 'res_partner_bank'
              AND c.contype = 'u'              -- UNIQUE constraints
            GROUP BY c.conname
            """
        )
        uniques = self.env.cr.fetchall()  # [(conname, [col1, col2, ...]), ...]
        has_unique_on_acc_number = any(
            "acc_number" in cols for (_name, cols) in uniques
        )

        self.assertFalse(
            has_unique_on_acc_number,
            f"Found UNIQUE constraint on res_partner_bank(acc_number): {uniques}",
        )

        # 2) OPTIONAL: if our override exists with name 'unique_number',
        # it must be CHECK
        self.env.cr.execute(
            """
            SELECT c.contype
            FROM pg_constraint c
                     JOIN pg_class r ON r.oid = c.conrelid
                     JOIN pg_namespace n ON n.oid = r.relnamespace
            WHERE r.relname = 'res_partner_bank'
              AND c.conname = 'unique_number'
            """
        )
        row = self.env.cr.fetchone()
        if row:
            contype = row[0]
            self.assertEqual(
                contype,
                "c",
                "Constraint 'unique_number' should be a CHECK ('c'), not UNIQUE ('u').",
            )
