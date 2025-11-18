# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class IrModel(models.Model):
    _inherit = 'ir.model'

    available_on_app = fields.Boolean(
        string='Available on App',
        default=False,)

    def action_mark_available_on_app(self):
        self.env.cr.execute("""
            UPDATE ir_model
            SET available_on_app = TRUE
            WHERE id IN %s
        """, [tuple(self.ids)])

    def action_unmark_available_on_app(self):
        self.env.cr.execute("""
            UPDATE ir_model
            SET available_on_app = FALSE
            WHERE id IN %s
        """, [tuple(self.ids)])


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    available_on_app = fields.Boolean(
        string='Available on App',
        default=False,)

    def action_mark_available_on_app(self):
        self.env.cr.execute("""
            UPDATE ir_model_fields
            SET available_on_app = TRUE
            WHERE id IN %s
        """, [tuple(self.ids)])

    def action_unmark_available_on_app(self):
        self.env.cr.execute("""
            UPDATE ir_model_fields
            SET available_on_app = FALSE
            WHERE id IN %s
        """, [tuple(self.ids)])
