# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from collections import defaultdict

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class DecaDocument(models.Model):
    _inherit = "deca.document"

    picking_id = fields.Many2one(
        "stock.picking",
        string="Transfer",
        copy=False,
        index=True,
        tracking=True,
    )

    def _check_issue_values(self):
        result = super()._check_issue_values()
        self._check_deca_quantities()
        return result

    def _deca_product_quantities(self):
        self.ensure_one()
        quantities = defaultdict(float)
        for line in self.line_ids.filtered("product_id"):
            quantities[line.product_id] += line.quantity
        return quantities

    def _check_deca_quantities(self):
        self.ensure_one()
        picking = self.picking_id
        if not picking:
            return
        declared = self._deca_product_quantities()
        if not declared:
            return
        other_decas = self.search(
            [
                ("picking_id", "=", picking.id),
                ("state", "=", "issued"),
                ("id", "!=", self.id),
            ]
        )
        already = defaultdict(float)
        for other in other_decas:
            # pylint: disable=protected-access
            for product, qty in other._deca_product_quantities().items():
                already[product] += qty
        available = defaultdict(float)
        for move in picking.move_ids:
            available[move.product_id] += max(
                move.product_uom_qty, move.quantity
            )
        self._raise_quantity_overflow(declared, already, available)

    def _raise_quantity_overflow(self, declared, already, available):
        self.ensure_one()
        precision = self.env["decimal.precision"].precision_get(
            "Product Unit of Measure"
        )
        errors = []
        for product, qty in declared.items():
            total = qty + already.get(product, 0.0)
            avail = available.get(product, 0.0)
            if float_compare(total, avail, precision_digits=precision) > 0:
                errors.append(
                    self.env._(
                        "%(product)s: %(total)s declared (incl. other "
                        "issued DECAs) exceeds %(avail)s available in the "
                        "transfer.",
                        product=product.display_name,
                        total=total,
                        avail=avail,
                    )
                )
        if not errors:
            return
        raise UserError(
            self.env._(
                "This DECA would over-declare goods from transfer "
                "%(picking)s:\n%(details)s",
                picking=self.picking_id.name,
                details="\n".join(errors),
            )
        )
