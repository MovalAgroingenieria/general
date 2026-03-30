# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "base_assembly")
class TestAssemblyAgendaListViewArch(TransactionCase):
    def test_no_agenda_vote_mode_in_list_column_invisible(self):
        for xmlid in (
            "base_assembly.assembly_assembly_view_form",
            "base_assembly.assembly_agenda_view_tree",
        ):
            view = self.env.ref(xmlid)
            arch = view._get_combined_arch()
            bad = arch.xpath(
                "//list//field[@column_invisible]"
                "[contains(@column_invisible, 'agenda_vote_mode')]"
            )
            self.assertFalse(
                bad,
                (
                    f"{xmlid}: list column_invisible is evaluated without row context; "
                    f"do not reference agenda_vote_mode there. Offending fields: "
                    f"{[el.get('name') for el in bad]}"
                ),
            )
