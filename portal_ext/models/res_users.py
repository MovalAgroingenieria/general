# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.multi
    def write(self, vals):
        # The user 'email' field is a related/inherited field of the partner
        # (res.users.email -> res.partner.email). When the configuration flag
        # 'keep_partner_email_on_user_change' is enabled, changing the email of
        # a portal user must not overwrite the real email stored on the linked
        # partner (socio). We drop the 'email' key for those users so the
        # partner email is preserved.
        keep_partner_email = self.env['ir.values'].sudo().get_default(
            'base.config.settings', 'keep_partner_email_on_user_change')
        propagate_email = self.env.context.get(
            'allow_user_email_propagation')
        result = True
        if keep_partner_email and 'email' in vals and not propagate_email:
            portal_users = self.filtered(
                lambda user: user.has_group('base.group_portal'))
            other_users = self - portal_users
            vals_without_email = dict(vals)
            vals_without_email.pop('email')
            if portal_users:
                result = super(ResUsers, portal_users).write(
                    vals_without_email)
            if other_users:
                result = super(ResUsers, other_users).write(vals) and result
        else:
            result = super(ResUsers, self).write(vals)
        return result
