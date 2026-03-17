# Copyright 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import re

from odoo import fields, models


class VoteType(models.Model):
    _inherit = "vote.type"

    formula_type = fields.Selection(
        [
            ("fixed", "Valor fijo"),
            ("count_relation", "Cantidad de registros"),
            ("sum_relation", "Suma de un campo"),
            ("blockly", "Blockly (bloques)"),
            ("custom", "Fórmula avanzada (Jinja2)"),
        ],
        string="Tipo de fórmula",
        default="custom",
        help="Formas sencillas: valor fijo, cantidad, suma. Blockly: bloques. Custom: Jinja2.",
    )
    formula_fixed_value = fields.Float(
        string="Votos",
        default=1.0,
        help="Cada socio recibe este número de votos.",
    )
    formula_relation_name = fields.Char(
        string="Lista del contacto",
        help="Nombre técnico del campo (ej. ter_parcel_ids).",
    )
    formula_attribute = fields.Char(
        string="Campo a sumar",
        help="Campo numérico en cada registro (ej. surface).",
    )
    formula_divisor = fields.Float(
        string="Dividir entre",
        default=1.0,
        help="Ej. 10 para «1 voto cada 10 unidades».",
    )
    formula_blockly_xml = fields.Text(
        string="Blockly (XML)",
        help="Contenido del workspace Blockly (se usa cuando el tipo es Blockly).",
    )

    _SAFE_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

    def _get_effective_formula(self):
        """Return the Jinja2 expression (from type + structured fields or custom)."""
        self.ensure_one()
        if self.formula_type == "custom":
            return (self.formula or "").strip()
        if self.formula_type == "blockly":
            return (self.formula or "").strip()
        if self.formula_type == "fixed":
            return "{{ %s }}" % self.formula_fixed_value
        if self.formula_type == "count_relation":
            rel = (self.formula_relation_name or "").strip()
            if not rel or not self._SAFE_IDENTIFIER.match(rel):
                return ""
            return "{{ partner.%s | length }}" % rel
        if self.formula_type == "sum_relation":
            rel = (self.formula_relation_name or "").strip()
            attr = (self.formula_attribute or "").strip()
            if not rel or not self._SAFE_IDENTIFIER.match(rel):
                return ""
            if not attr or not self._SAFE_IDENTIFIER.match(attr):
                return ""
            divisor = self.formula_divisor or 1.0
            return "{{ (partner.%s | map(attribute='%s') | sum) / %s }}" % (
                rel,
                attr,
                divisor,
            )
        return (self.formula or "").strip()
