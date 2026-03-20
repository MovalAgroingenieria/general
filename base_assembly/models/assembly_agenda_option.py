# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AssemblyAgendaOption(models.Model):
    _name = "assembly.agenda.option"
    _description = "Agenda item option (for multiple choice vote)"
    _order = "agenda_id, sequence, id"

    agenda_id = fields.Many2one(
        "assembly.agenda",
        string="Agenda item",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Option", required=True)
