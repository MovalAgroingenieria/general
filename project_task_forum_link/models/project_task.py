# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models, fields, _


class ProjectTask(models.Model):
    _inherit = 'project.task'

    forum_post_id = fields.Many2one(
        string='Forum Post',
        comodel_name='forum.post',
        readonly=True,
        ondelete='set null',
    )

    def action_open_wizard_create_forum_from_task(self):
        self.ensure_one()
        default_content = ''
        message = self.message_ids.filtered(
            lambda m: not m.subtype_id.internal).sorted(key=lambda m: m.date)
        if (message and message[0].body):
            default_content = message[0].body
        act_window = {
            'type': 'ir.actions.act_window',
            'name': _('Create forum post from ') + self.name,
            'res_model': 'wizard.create.forum.post.from.task',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_title': self.name,
                'default_content': default_content,
                'default_task_id': self.id,
                'default_tag_ids': self.tag_ids.ids,
            },
        }
        return act_window
