# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class ResFiletag(models.Model):
    _name = 'res.filetag'
    _description = 'Tags for files'

    name = fields.Char(
        string='File Tag',
        size=25,
        translate=True)

    color = fields.Integer(
        string='Color Index',
        help='0:grey, 1:green, 2:yellow, ' +
        '3:orange, 4:red, 5:purple, 6:blue, ' +
        '7:cyan, 8:light-green, 9:magenta')

    notes = fields.Html(
        string="Notes")
