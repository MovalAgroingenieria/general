# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo import api, fields, models


class WizardCreateForumPostFromTask(models.TransientModel):
    _name = 'wizard.create.forum.post.from.task'
    _description = 'Wizard to Create Forum Post from Task'

    title = fields.Char(
        string='Post Title',
        required=True,
        default=lambda self: self._default_title(),
    )

    content = fields.Html(
        string='Content',
        required=True,
        default=lambda self: self._default_content(),
    )

    forum_id = fields.Many2one(
        string='Forum',
        comodel_name='forum.forum',
        required=True,
        domain=[('visible_from_tasks', '=', True)],
        default=lambda self: self._default_forum_id(),
    )

    task_id = fields.Many2one(
        string='Related Task',
        comodel_name='project.task',
        required=True,
    )

    tag_ids = fields.Many2many(
        string='Related Task Tags',
        comodel_name='project.tags',
        required=True,
        default=lambda self: self._default_tag_ids(),
    )

    publication_date = fields.Datetime(
        string='Publication Date',
        required=True,
        default=fields.Datetime.now,
    )

    @api.model
    def _default_title(self):
        return self.env.context.get('default_title', '')

    @api.model
    def _default_tag_ids(self):
        task_id = self.env.context.get('default_task_id')
        if task_id:
            task = self.env['project.task'].browse(task_id)
            return task.tag_ids.ids
        return []

    @api.model
    def _default_content(self):
        return self.env.context.get('default_content', '')

    @api.model
    def _default_forum_id(self):
        return self.env['forum.forum'].search(
            [('visible_from_tasks', '=', True)], limit=1).id

    def _check_tag_to_avoid(self, tag, tags_to_avoid):
        tag_lower = tag.lower()
        for tag_to_avoid in tags_to_avoid:
            if tag_to_avoid.lower() in tag_lower:
                return True
        return False

    def _remove_tag_prefixes(self, prefixes, tag):
        tag_lower = tag.lower()
        for prefix in prefixes:
            if tag_lower.startswith(prefix.lower()):
                return tag[len(prefix):]
        return tag

    def action_confirm(self):
        tags = []
        if self.tag_ids:
            tags_to_avoid = self.forum_id.tags_to_avoid.split(',')
            tags_prefix = self.forum_id.tags_prefix.split(',')
            for tag in self.tag_ids:
                name_tag = tag.name
                # Check if we should avoid this tag
                if (not self._check_tag_to_avoid(name_tag, tags_to_avoid)):
                    name_tag = self._remove_tag_prefixes(
                        tags_prefix, name_tag)
                    forum_tag = self.env['forum.tag'].search(
                        [('name', '=', name_tag)], limit=1)
                    if not forum_tag:
                        forum_tag = self.env['forum.tag'].create(
                            {
                                'name': name_tag,
                                'forum_id': self.forum_id.id,
                            })
                    tags.append(forum_tag.id)
        forum_vals = {
            'name': self.title,
            'content': self.content,
            'task_id': self.task_id.id,
            'forum_id': self.forum_id.id,
            'publication_date': self.publication_date,
            'tag_ids': [(6, 0, tags)],
        }
        if (self.forum_id.default_user_from_tasks):
            forum_post = self.env['forum.post'].sudo(
                self.forum_id.default_user_from_tasks).create(forum_vals)
        else:
            forum_post = self.env['forum.post'].create(forum_vals)
        self.task_id.forum_post_id = forum_post
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'forum.post',
            'res_id': forum_post.id,
            'view_mode': 'form',
            'target': 'current',
        }
