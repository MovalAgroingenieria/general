# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import unittest

from odoo.tests.common import TransactionCase


class TestSimpleModel(TransactionCase):
    """Test cases for SimpleModel functionality."""

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        """Set up test data and environment."""
        super().setUpClass()
        cls.model = cls.env["simple.model"]
        # Get the actual Python class for patching constants/flags
        # pylint: disable=protected-access
        cls.model_class = cls.env.registry[
            cls.model._name
        ]  # pylint: disable=protected-access
        cls.is_abstract = getattr(cls.model_class, "_abstract", False) or not getattr(
            cls.model_class, "_auto", True
        )

    # -------------------------
    # Helper methods (always available)
    # -------------------------

    def test_process_alphanum_code_trim_and_case(self):
        """Test alphanum code processing with trim, clip, and case flags."""
        model_class = self.model_class
        # pylint: disable=protected-access
        old_lower = (
            model_class._set_alphanum_code_to_lowercase
        )  # pylint: disable=protected-access
        # pylint: disable=protected-access
        old_upper = (
            model_class._set_alphanum_code_to_uppercase
        )  # pylint: disable=protected-access
        old_size = model_class._size_name  # pylint: disable=protected-access

        try:
            # Force predictable settings via class, not recordset
            model_class._size_name = 5  # pylint: disable=protected-access

            # No case transform
            model_class._set_alphanum_code_to_lowercase = (
                False  # pylint: disable=protected-access
            )
            model_class._set_alphanum_code_to_uppercase = (
                False  # pylint: disable=protected-access
            )
            self.assertEqual(
                self.model._process_alphanum_code(
                    "  AbCdEf  "
                ),  # pylint: disable=protected-access
                "AbCdE",
            )

            # Lowercase
            model_class._set_alphanum_code_to_lowercase = (
                True  # pylint: disable=protected-access
            )
            model_class._set_alphanum_code_to_uppercase = (
                False  # pylint: disable=protected-access
            )
            self.assertEqual(
                self.model._process_alphanum_code(
                    "  AbCdE  "
                ),  # pylint: disable=protected-access
                "abcde",
            )

            # Uppercase
            model_class._set_alphanum_code_to_lowercase = (
                False  # pylint: disable=protected-access
            )
            model_class._set_alphanum_code_to_uppercase = (
                True  # pylint: disable=protected-access
            )
            self.assertEqual(
                self.model._process_alphanum_code(
                    "  AbCdE  "
                ),  # pylint: disable=protected-access
                "ABCDE",
            )
        finally:
            model_class._set_alphanum_code_to_lowercase = (
                old_lower  # pylint: disable=protected-access
            )
            model_class._set_alphanum_code_to_uppercase = (
                old_upper  # pylint: disable=protected-access
            )
            model_class._size_name = old_size  # pylint: disable=protected-access

    def test_process_description_trim_and_clip(self):
        """Test description processing with trim and clip functionality."""
        model_class = self.model_class
        old_size = model_class._size_description  # pylint: disable=protected-access
        try:
            model_class._size_description = 7  # pylint: disable=protected-access
            # pylint: disable=protected-access
            self.assertEqual(
                self.model._process_description(
                    "  hello  "
                ),  # pylint: disable=protected-access
                "hello",
            )
            # pylint: disable=protected-access
            self.assertEqual(
                self.model._process_description(
                    "  1234567890  "
                ),  # pylint: disable=protected-access
                "1234567",
            )
        finally:
            # pylint: disable=protected-access
            model_class._size_description = old_size  # pylint: disable=protected-access

    def test_get_sequence_from_param_valid_and_invalid(self):
        """Test sequence retrieval for valid and invalid parameters."""
        # Invalid / missing parameter
        # pylint: disable=protected-access
        self.assertIsNone(
            self.model._get_sequence(
                "non.existent.param.key"
            )  # pylint: disable=protected-access
        )

        # Create a real sequence and store its id in a param
        sequence = self.env["ir.sequence"].create(
            {
                "name": "TEST SimpleModel",
                "implementation": "no_gap",
                "prefix": "TST",
                "padding": 3,
            }
        )
        param_key = "test.simple_model.sequence_id"
        self.env["ir.config_parameter"].sudo().set_param(param_key, str(sequence.id))
        found = self.model._get_sequence(param_key)  # pylint: disable=protected-access
        self.assertTrue(found and found.id == sequence.id)

    # -------------------------
    # Record-level behavior (skipped if 'simple.model' is abstract)
    # -------------------------

    def test_compute_name_and_name_get_alphanum_mode(self):
        """Test name computation in alphanumeric mode."""
        if self.is_abstract:
            raise unittest.SkipTest(
                "simple.model is abstract; record-level tests skipped."
            )

        model_class = self.model_class
        old_num_flag = model_class._set_num_code  # pylint: disable=protected-access
        try:
            model_class._set_num_code = False  # pylint: disable=protected-access
            record = self.model.create(
                {"alphanum_code": "ABC123", "description": "Item A"}
            )
            self.assertEqual(record.name, "ABC123")
            self.assertEqual(record.name_get()[0][1], "ABC123")
        finally:
            model_class._set_num_code = old_num_flag  # pylint: disable=protected-access

    def test_compute_name_and_name_get_numeric_mode(self):
        """Test name computation in numeric mode."""
        if self.is_abstract:
            raise unittest.SkipTest(
                "simple.model is abstract; record-level tests skipped."
            )

        model_class = self.model_class
        old_num_flag = model_class._set_num_code  # pylint: disable=protected-access
        old_size_name = model_class._size_name  # pylint: disable=protected-access
        try:
            model_class._set_num_code = True  # pylint: disable=protected-access
            model_class._size_name = 5  # pylint: disable=protected-access
            record = self.model.create({"num_code": 42, "description": "Gadget"})
            self.assertEqual(record.name, "00042")
            self.assertEqual(record.name_get()[0][1], "Gadget [42]")
        finally:
            model_class._set_num_code = old_num_flag  # pylint: disable=protected-access
            model_class._size_name = old_size_name  # pylint: disable=protected-access

    def test_name_search_respects_operator(self):
        """Test name search respects operator and mode."""
        if self.is_abstract:
            raise unittest.SkipTest(
                "simple.model is abstract; record-level tests skipped."
            )

        model_class = self.model_class
        old_num_flag = model_class._set_num_code  # pylint: disable=protected-access

        # Alphanum mode
        try:
            model_class._set_num_code = False  # pylint: disable=protected-access
            record1 = self.model.create(
                {"alphanum_code": "ZX-100", "description": "Alpha"}
            )
            record2 = self.model.create(
                {"alphanum_code": "ZX-200", "description": "Beta"}
            )
            result = self.model.name_search(name="ZX-1", operator="ilike", limit=10)
            ids_found = [record_id for record_id, _ in result]
            self.assertIn(record1.id, ids_found)
            self.assertNotIn(record2.id, ids_found)
        finally:
            model_class._set_num_code = old_num_flag  # pylint: disable=protected-access

        # Numeric mode (searches by description)
        old_num_flag = model_class._set_num_code  # pylint: disable=protected-access
        try:
            model_class._set_num_code = True  # pylint: disable=protected-access
            record3 = self.model.create({"num_code": 7, "description": "Widget X"})
            record4 = self.model.create({"num_code": 8, "description": "Gizmo Y"})
            result = self.model.name_search(name="Widget", operator="ilike", limit=10)
            ids_found = [record_id for record_id, _ in result]
            self.assertIn(record3.id, ids_found)
            self.assertNotIn(record4.id, ids_found)
        finally:
            model_class._set_num_code = old_num_flag  # pylint: disable=protected-access

    def test_sequence_alignment_on_create_with_manual_code_and_auto_consume(self):
        """Test sequence alignment with manual codes and auto-consumption."""
        if self.is_abstract:
            raise unittest.SkipTest(
                "simple.model is abstract; record-level tests skipped."
            )

        sequence = self.env["ir.sequence"].create(
            {
                "name": "TEST Align",
                "implementation": "no_gap",
                "prefix": "AA",
                "padding": 4,
            }
        )
        param_key = "test.simple_model.sequence_id"
        self.env["ir.config_parameter"].sudo().set_param(param_key, str(sequence.id))

        model_class = self.model_class
        # pylint: disable=protected-access
        old_param_key = (
            model_class._sequence_for_codes
        )  # pylint: disable=protected-access
        try:
            model_class._sequence_for_codes = (
                param_key  # pylint: disable=protected-access
            )

            # pylint: disable=protected-access
            current = (
                sequence._get_current_sequence()
            )  # pylint: disable=protected-access
            next_char = sequence.get_next_char(current.number_next_actual)

            record1 = self.model.create(
                {"alphanum_code": next_char, "description": "Manual match"}
            )
            self.assertTrue(record1)

            current_after_1 = (
                sequence._get_current_sequence()
            )  # pylint: disable=protected-access
            next_char_2 = sequence.get_next_char(current_after_1.number_next_actual)
            self.assertNotEqual(
                next_char,
                next_char_2,
                "Sequence did not advance after manual code alignment",
            )

            self.model.create({"description": "Auto consume"})
            current_after_2 = (
                sequence._get_current_sequence()
            )  # pylint: disable=protected-access
            next_char_3 = sequence.get_next_char(current_after_2.number_next_actual)
            self.assertNotEqual(
                next_char_2,
                next_char_3,
                "Sequence did not consume for missing alphanum_code",
            )
        finally:
            model_class._sequence_for_codes = (
                old_param_key  # pylint: disable=protected-access
            )


if __name__ == "__main__":
    unittest.main()
