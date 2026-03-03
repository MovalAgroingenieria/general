# Copyright 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def post_init_sync_agent_user_group(env_or_cr, _registry=None):
    """On install: add group_agent_user to all users whose partner is an agent."""
    if _registry is not None:
        env = api.Environment(env_or_cr, SUPERUSER_ID, {})
    else:
        env = env_or_cr
    group = env.ref(
        "agent_external_permissions.group_agent_user",
        raise_if_not_found=False,
    )
    if not group:
        return
    partners = env["res.partner"].search([("agent", "=", True)])
    users = partners.mapped("user_ids").filtered(lambda u: u and group not in u.groups_id)
    if users:
        users.sudo().write({"groups_id": [(4, group.id)]})
