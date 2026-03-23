# -*- coding: utf-8 -*-
# 2021 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class CreditControlLine(models.Model):
    _inherit = "credit.control.line"

    invoice_date = fields.Date(
        string="Invoice date",
        compute="_compute_invoice_date",
        store=True,
    )

    tracking_ref = fields.Char(
        string="Tracking Reference")

    delivered_letter = fields.Boolean(
        string="Delivered letter")

    delivery_date = fields.Date(
        string="Delivery date")

    returned_letter = fields.Boolean(
        string="Returned letter")

    return_reason = fields.Selection([
        ('unknown', 'Unknown'),
        ('absent', 'Absent'),
        ('incorrect_address', 'Incorrect address'),
        ('refused', 'Refused'),
        ('deceased', 'Deceased'),
        ('not_retired', 'Not retired'),
        ('no_one_takes_responsibility', 'No one takes responsibility')],
        string="Return reason")

    description_html = fields.Html(
        string="Description",
        translate=True,
    )

    notes = fields.Html(
        string="Notes")

    has_notes = fields.Boolean(
        string="Has notes",
        store=True,
        compute="_compute_has_notes")

    newsletter_publication = fields.Boolean(
        string='Newsletter Publication',
        index=True,
        default=False,
    )

    newsletter_publication_date = fields.Date(
        string='Newsletter Publication Date',
        index=True,
    )

    notification_tracking_notes = fields.Html(
        string='Notification Tracking Notes',
    )

    @api.multi
    @api.depends('invoice_id', 'invoice_id.date')
    def _compute_invoice_date(self):
        for record in self:
            if record.invoice_id:
                record.invoice_date = record.invoice_id.date

    @api.multi
    def _compute_has_notes(self):
        for record in self:
            if record.notes:
                record.has_notes = True
