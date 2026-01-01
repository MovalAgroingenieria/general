# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import SUPERUSER_ID, api


def post_init_sync_agents(cr, registry):
    """Post-init hook.

    On install, propagate ``res.partner.external_agent_ids`` to
    ``crm.lead.external_agent_ids`` for existing opportunities where:

    - type == 'opportunity'
    - partner_id is set
    - external_agent_ids is empty
    """
    env = api.Environment(cr, SUPERUSER_ID, {"active_test": False})

    Partner = env["res.partner"].sudo()
    Lead = env["crm.lead"].sudo()

    partners = Partner.search([("external_agent_ids", "!=", False)])
    if not partners:
        return

    for partner in partners:
        leads = Lead.search(
            [
                ("type", "=", "opportunity"),
                ("partner_id", "=", partner.id),
                ("external_agent_ids", "=", False),
            ]
        )
        if leads:
            leads.with_context(skip_external_agent_propagation=True).write(
                {"external_agent_ids": [(6, 0, partner.external_agent_ids.ids)]}
            )
