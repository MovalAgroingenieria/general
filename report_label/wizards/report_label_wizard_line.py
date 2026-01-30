# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class ReportLabelWizardLine(models.TransientModel):
    _name = "report.label.wizard.line"
    _description = "Report Label Wizard Line"
    _order = "sequence"

    wizard_id = fields.Many2one(
        "report.label.wizard",
        "Wizard",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    res_id = fields.Integer("Resource ID", required=True)
    res_name = fields.Char(compute="_compute_res_name")
    quantity = fields.Integer(default=1, required=True)

    @api.depends("wizard_id.model_id", "res_id")
    def _compute_res_name(self):
        for rec in self:
            rec.res_name = False

        recs = self.filtered(
            lambda r: r.wizard_id and r.wizard_id.model_id and r.res_id
        )
        if not recs:
            return

        grouped = {}
        for rec in recs:
            model_name = rec.wizard_id.model_id.sudo().model
            grouped.setdefault(model_name, set()).add(rec.res_id)

        names_by_model = {}
        for model_name, ids in grouped.items():
            data = self.env[model_name].browse(list(ids)).sudo().read(["display_name"])
            names_by_model[model_name] = {d["id"]: d["display_name"] for d in data}

        for rec in recs:
            model_name = rec.wizard_id.model_id.sudo().model
            rec.res_name = names_by_model.get(model_name, {}).get(rec.res_id) or False
