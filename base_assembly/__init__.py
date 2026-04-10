# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from . import controllers, models, wizards


def post_init_hook(env):
    companies = env["res.company"].search([])
    companies._assembly_ensure_numbering_sequence()
    companies._assembly_ensure_default_template_configuration()
    env["assembly.delegation"]._assembly_cleanup_delegation_state_in_views()
