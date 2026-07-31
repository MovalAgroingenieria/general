# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, models
from odoo.exceptions import UserError


class VoteType(models.Model):
    _inherit = "vote.type"

    @api.model
    def _assembly_vote_type_ids_used_in_domain(self, vote_type_ids):
        """Return ``vote.type`` ids (subset) linked to any assembly data."""
        vt_set = frozenset(int(x) for x in vote_type_ids if x)
        if not vt_set:
            return frozenset()
        used = set()
        for rec in self.env["assembly.assembly"].search(
            [("vote_type_ids", "in", list(vt_set))]
        ):
            used.update(rec.vote_type_ids.ids)
        for rec in self.env["assembly.type"].search(
            [("vote_type_ids", "in", list(vt_set))]
        ):
            used.update(rec.vote_type_ids.ids)
        for rec in self.env["assembly.agenda"].search(
            [("vote_type_id", "in", list(vt_set))]
        ):
            if rec.vote_type_id:
                used.add(rec.vote_type_id.id)
        for rec in self.env["assembly.voting"].search(
            [("vote_type_id", "in", list(vt_set))]
        ):
            if rec.vote_type_id:
                used.add(rec.vote_type_id.id)
        for rec in self.env["assembly.delegation"].search(
            [("vote_type_ids", "in", list(vt_set))]
        ):
            used.update(rec.vote_type_ids.ids)
        for rec in self.env["assembly.attendee.vote"].search(
            [("vote_type_id", "in", list(vt_set))]
        ):
            if rec.vote_type_id:
                used.add(rec.vote_type_id.id)
        return frozenset(used & vt_set)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_assembly_usage(self):
        used_ids = self._assembly_vote_type_ids_used_in_domain(self.ids)
        if used_ids:
            used = self.browse(sorted(used_ids))
            raise UserError(
                self.env._(
                    "You cannot delete vote type(s) already used in assemblies: "
                    "%(names)s. Remove them from assemblies, assembly types, agenda "
                    "items, votings, delegations, or attendee vote lines first.",
                    names=", ".join(used.mapped("display_name")),
                )
            )
