# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, exceptions, api, _


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    stage_new = fields.Boolean(
        string="Stage: New",
        related='stage_id.is_new',
        readonly=True,
        store=False,
    )

    @api.depends('user_id', 'type')
    def _compute_team_id(self):
        """ When changing the user, also set a team_id or restrict team id
        to the ones user_id is member of.
        Override to remove type-based restriction on team selection. """
        for lead in self:
            if not lead.user_id:
                continue
            user = lead.user_id
            if (lead.team_id and
                    user in lead.team_id.member_ids | lead.team_id.user_id):
                continue
            team_domain = []
            team = self.env['crm.team']._get_default_team_id(
                user_id=user.id, domain=team_domain)
            lead.team_id = team.id

    def write(self, vals):
        vals = vals or {}
        if 'stage_id' in vals:
            if not self.tag_ids and not self.source_id:
                raise exceptions.UserError(
                    _('You must indicate Category and Origin to the lead '
                      'before changing the stage.')
                )
        return super(CrmLead, self).write(vals)
