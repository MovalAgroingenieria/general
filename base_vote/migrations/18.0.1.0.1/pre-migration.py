# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade

XMLID_RENAMES = [
    (
        "base_vote.res_partner_view_form_vote",
        "base_vote.view_partner_form",
    ),
    (
        "base_vote.partner_vote_view_tree",
        "base_vote.partner_vote_view_list",
    ),
]


@openupgrade.migrate()
def migrate(cr, version):
    if not version:
        return
    cursor = cr.cr if hasattr(cr, "cr") else cr
    openupgrade.rename_xmlids(cursor, XMLID_RENAMES)
