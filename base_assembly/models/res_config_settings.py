# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    assembly_default_use_qr = fields.Boolean(
        related="company_id.assembly_default_use_qr",
        readonly=False,
    )
    assembly_allow_edit_closed_assembly = fields.Boolean(
        related="company_id.assembly_allow_edit_closed_assembly",
        readonly=False,
    )
    assembly_sequence_id = fields.Many2one(
        related="company_id.assembly_sequence_id",
        readonly=False,
    )
    assembly_attendance_landing_qweb_id = fields.Many2one(
        related="company_id.assembly_attendance_landing_qweb_id",
        readonly=False,
    )
    assembly_attendance_error_qweb_id = fields.Many2one(
        related="company_id.assembly_attendance_error_qweb_id",
        readonly=False,
    )
