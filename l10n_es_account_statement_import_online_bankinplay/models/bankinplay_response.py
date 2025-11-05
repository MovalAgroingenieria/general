# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, api
from datetime import datetime, timedelta


class BankinplayResponse(models.Model):
    _name = 'bankinplay.response'
    _description = 'Intermediate table to store bankinplay responses when ' + \
        'being used as remote endpoint'

    # TO be checked by later callbacks
    bankinplay_signature = fields.Char(
        string="Bankinplay signature",
        readonly=True,
        copy=False,
    )

    bankinplay_responseid = fields.Char(
        string="Bankinplay response id",
        readonly=True,
        copy=False,
    )

    bankinplay_response = fields.Char(
        string="Bankinplay Response",
        readonly=True,
        copy=False,
    )

    endpoint_return_url = fields.Char(
        string="URL of client database",
        readonly=True,
        copy=False,
    )

    @api.model
    def delete_old_responses(self):
        limit_date = datetime.now() - timedelta(weeks=1)
        old_responses = self.search([('create_date', '<', limit_date)])
        old_responses.unlink()
