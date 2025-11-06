# 2025 Alquiber / Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SimpleModel(models.AbstractModel):
    _name = "simple.model"
    _description = "Simple Model"
    _order = "name"

    # -------------------------
    # Model constants
    # -------------------------
    # Logical lengths (DB does not enforce in v18; we trim programmatically)
    MAX_SIZE_NAME_FIELD = 50
    MAX_SIZE_CHAR_FIELD = 255

    # Visual/label trimming widths
    _size_name = 30
    _size_description = 75

    # Code behavior
    _set_num_code = False
    _set_alphanum_code_to_lowercase = False
    _set_alphanum_code_to_uppercase = False

    # Alphanumeric code length rules (0 = ignore)
    _minlength = 0
    _maxlength = 0

    # ir.config_parameter key holding the sequence ID used to propose/consume codes
    _sequence_for_codes = ""

    # Whether spaces are allowed in alphanumeric codes
    _allowed_blanks_in_code = True

    # -------------------------
    # Defaults
    # -------------------------

    def _default_alphanum_code(self):
        """Return the NEXT *predicted* sequence value (do not consume)."""
        if not self._sequence_for_codes:
            return ""
        sequence = self._get_sequence(self._sequence_for_codes)
        if sequence:
            current_sequence = self._get_current_sequence(sequence)
            if current_sequence:
                number_next_actual = current_sequence.number_next_actual
                return sequence.get_next_char(number_next_actual)
        return ""

    def _default_num_code(self):
        """Simple auto-increment (max + 1) if _set_num_code is enabled."""
        if not self._set_num_code:
            return 0
        last = self.search([], limit=1, order="num_code desc")
        return (last.num_code + 1) if last else 1

    # -------------------------
    # Fields
    # -------------------------
    # pylint: disable=protected-access
    alphanum_code = fields.Char(
        index=True,
        default=lambda self: self._default_alphanum_code(),
    )
    # pylint: disable=protected-access
    num_code = fields.Integer(
        index=True,
        default=lambda self: self._default_num_code(),
    )

    description = fields.Char(
        index=True,
    )

    name = fields.Char(
        store=True,
        index=True,
        compute="_compute_name",
    )
    # pylint: disable=protected-access
    display_name = fields.Char(
        compute="_compute_display_name",
        store=False,  # Typically not stored for performance
    )

    notes = fields.Html()

    _sql_constraints = [
        ("name_unique", "UNIQUE (name)", "Existing Code."),
        (
            "name_not_null",
            "CHECK (alphanum_code IS NOT NULL OR num_code > 0)",
            "A valid code is required.",
        ),
        (
            "description_not_null",
            "CHECK (description IS NOT NULL OR alphanum_code IS NOT NULL)",
            "The description is required.",
        ),
    ]

    # -------------------------
    # Computes / Constraints
    # -------------------------

    @api.depends("alphanum_code", "num_code")
    def _compute_name(self):
        """
        name = alphanum_code, or zero-padded num_code when numeric codes are enabled.
        """
        for rec in self:
            if self._set_num_code:
                rec.name = (
                    (str(rec.num_code).zfill(self._size_name))
                    if rec.num_code
                    else "0".zfill(self._size_name)
                )
            else:
                rec.name = rec.alphanum_code or ""

    @api.constrains("alphanum_code")
    def _check_alphanum_code(self):
        for rec in self:
            code = rec.alphanum_code or ""
            if not code:
                # If numeric mode is enabled, empty alphanum_code can be fine;
                # otherwise DB constraint will guard. Skip here.
                continue

            if (not self._allowed_blanks_in_code) and (" " in code):
                raise ValidationError(
                    rec.env["ir.translation"]._gettext(
                        "It is not possible to insert blank spaces in the code."
                    )
                )

            if self._minlength and len(code) < self._minlength:
                raise ValidationError(
                    rec.env["ir.translation"]._gettext(
                        "Minimum number of characters allowed for the code: %s."
                    )
                    % self._minlength
                )

            if self._maxlength and len(code) > self._maxlength:
                raise ValidationError(
                    rec.env["ir.translation"]._gettext(
                        "Maximum number of characters allowed for the code: %s."
                    )
                    % self._maxlength
                )

    # -------------------------
    # Display name & search
    # -------------------------

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        """
        Search by alphanum_code (default) or description (when numeric codes are used).
        Respects the operator passed by the caller.
        """
        args = args or []
        domain = []
        if self._set_num_code:
            if name:
                domain = [("description", operator, name)]
        else:
            if name:
                domain = [("alphanum_code", operator, name)]
        recs = self.search(domain + args, limit=limit)
        return [(rec.id, rec.display_name) for rec in recs]

    @api.depends("alphanum_code", "num_code", "description")
    def _compute_display_name(self):
        """
        Compute display name - replacement for deprecated name_get.
        If numeric codes are enabled: label = "Description [num]".
        Otherwise: label = alphanum_code.
        """
        for rec in self:
            if self._set_num_code:
                desc = rec.description or ""
                rec.display_name = f"{desc} [{rec.num_code or 0}]"
            else:
                rec.display_name = rec.alphanum_code or ""

    # -------------------------
    # Create / Write
    # -------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """
        - Normalize/trim alphanum_code and description.
        - If incoming alphanum_code equals the next sequence value,
        advance the sequence once.
        - If alphanum_code is absent (likely RO), consume sequence
        *after* create for each missing code.
        """
        sequence = (
            self._get_sequence(self._sequence_for_codes)
            if self._sequence_for_codes
            else None
        )
        to_consume = 0

        for i, vals in enumerate(vals_list):
            vals = dict(vals)  # ensure mutability

            # alphanum_code normalization and sequence sync
            if vals.get("alphanum_code"):
                if sequence:
                    current_sequence = self._get_current_sequence(sequence)
                    if current_sequence:
                        number_next_actual = current_sequence.number_next_actual
                        next_code = sequence.get_next_char(number_next_actual)
                        if next_code == vals["alphanum_code"]:
                            sequence.next_by_id()  # keep sequence aligned with
                            # manual input
                vals["alphanum_code"] = self._process_alphanum_code(
                    vals["alphanum_code"]
                )
            else:
                if sequence:
                    to_consume += 1  # will consume after create()

            # description normalization
            if vals.get("description"):
                vals["description"] = self._process_description(vals["description"])

            # hook
            vals = self._process_vals(vals)

            vals_list[i] = vals  # write back

        records = super().create(vals_list)

        # Consume the sequence for records where code wasn't provided
        if sequence and to_consume > 0:
            for _ in range(to_consume):
                sequence.next_by_id()

        return records

    def write(self, vals):
        vals = dict(vals)
        if vals.get("alphanum_code"):
            vals["alphanum_code"] = self._process_alphanum_code(vals["alphanum_code"])
        if vals.get("description"):
            vals["description"] = self._process_description(vals["description"])
        vals = self._process_vals(vals)
        return super().write(vals)

    # -------------------------
    # Internals / Hooks
    # -------------------------

    def _get_sequence(self, param_name):
        """
        Read a sequence ID from ir.config_parameter[param_name] and
        return a valid record or None.
        """
        sequence_id = self.env["ir.config_parameter"].sudo().get_param(param_name)
        if not sequence_id:
            return None
        try:
            seq_id = int(sequence_id)
        except (ValueError, TypeError):
            return None
        if seq_id <= 0:
            return None
        return self.env["ir.sequence"].browse(seq_id).exists() or None

    def _get_current_sequence(self, sequence):
        """
        Get current sequence information safely.
        This wraps the protected method to avoid direct access.
        """
        # This is a wrapper around the protected method we need to use
        return sequence._get_current_sequence()  # pylint: disable=protected-access

    def _process_alphanum_code(self, value: str) -> str:
        """Trim and normalize case according to flags; clip to _size_name."""
        resp = (value or "").strip()
        if len(resp) > self._size_name:
            resp = resp[: self._size_name]
        if self._set_alphanum_code_to_lowercase:
            resp = resp.lower()
        if self._set_alphanum_code_to_uppercase:
            resp = resp.upper()
        return resp

    def _process_description(self, value: str) -> str:
        """Trim and clip to _size_description for consistent labels/views."""
        resp = (value or "").strip()
        if len(resp) > self._size_description:
            resp = resp[: self._size_description]
        return resp

    def _process_vals(self, vals: dict) -> dict:
        """Hook: override in subclasses to adjust vals before create/write."""
        return vals
