# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class FileConfiguration(models.TransientModel):
    _inherit = "res.config.settings"
    _description = "Configuration of File Management"

    # Expose the company-dependent field via related; editable in settings
    file_prefix = fields.Char(
        string="File Prefix",
        related="company_id.file_prefix",
        readonly=False,
        help="Company-dependent prefix for Files. Maximum 10 characters.",
    )