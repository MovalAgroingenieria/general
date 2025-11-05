# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class ResPartner(models.Model):
    """
    Extend partners with an extra address component: `street_num`.

    Why these overrides?
      - `_address_fields()` controls which fields are copied/propagated
        by Odoo when computing/completing addresses (e.g., commercial
        entity / contacts). We add `street_num` so it behaves like
        native address fields.
      - `_formatting_address_fields()` (v17+) lists placeholders allowed
        in `res.country.address_format`. Adding `street_num` here lets
        you use `%(street_num)s` in country address formats without
        warnings or drops during formatting.
    """
    _inherit = "res.partner"

    # New address field, stored as plain text because formats vary widely per country.
    street_num = fields.Char(string="Street number")

    # --- Internal helper -----------------------------------------------------

    def _add_field_name(self, names, field_name):
        """
        Safely insert `field_name` into the collection returned by super(),
        preserving the original container type when reasonable.

        super() may return list/tuple/set depending on Odoo version/override.
        - If tuple: convert to list to allow append (immutable otherwise).
        - If set: insert directly and return the set.
        - If list (common case): append if missing.
        """
        if isinstance(names, tuple):
            names = list(names)
        elif isinstance(names, set):
            names.add(field_name)
            return names

        # Treat as a list / sequence
        if field_name not in names:
            names.append(field_name)
        return names


    @api.model
    def _address_fields(self):
        """
        Ensure `street_num` is handled like other address components
        (street, city, zip, state, country...). This affects copy/propagation
        in commercial fields and various address computations.
        """
        res = super()._address_fields()
        return self._add_field_name(res, "street_num")

    @api.model
    def _formatting_address_fields(self):
        """
        Allow `%(street_num)s` token inside `res.country.address_format`.

        On v17+ this method exists upstream. For older versions or custom
        stacks where it may be missing, we gracefully fall back to `[]`.
        """
        parent = getattr(super(), "_formatting_address_fields", None)
        res = parent() if parent else []
        return self._add_field_name(res, "street_num")
