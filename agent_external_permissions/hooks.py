# Copyright 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def post_init_sync_agent_user_group(env_or_cr, _registry=None):
    """On install: add group_agent_user and Ventas/Usuario to agent users; remove See Employees menu."""
    if _registry is not None:
        env = api.Environment(env_or_cr, SUPERUSER_ID, {})
    else:
        env = env_or_cr
    group = env.ref(
        "agent_external_permissions.group_agent_user",
        raise_if_not_found=False,
    )
    group_sale = env.ref(
        "sales_team.group_sale_salesman",
        raise_if_not_found=False,
    )
    group_see_employees = env.ref(
        "agent_external_permissions.group_see_employees_menu",
        raise_if_not_found=False,
    )
    if not group:
        return
    partners = env["res.partner"].search([("agent", "=", True)])
    users = partners.mapped("user_ids").filtered(lambda u: u and group not in u.groups_id)
    if not users:
        return
    for user in users:
        cmd = [(4, group.id)]
        vals = {"groups_id": cmd}
        if group_sale and group_sale not in user.groups_id:
            cmd.append((4, group_sale.id))
            vals["share"] = False
        if group_see_employees and group_see_employees in user.groups_id:
            cmd.append((3, group_see_employees.id))
        user.sudo().write(vals)
