# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Common helpers and base case for base_assembly model tests."""

from odoo.tests import TransactionCase


class AssemblyTestMixin:
    """Mixin with factory helpers for assembly, vote type, partners, agenda.

    Use with TransactionCase. Creates minimal data to avoid fragile tests
    (no hardcoded IDs; search by name or relation when needed).
    """

    @classmethod
    def _create_vote_type(cls, env, name="Test vote type", code=None):
        """Create a vote.type. code defaults to unique from name."""
        if code is None:
            code = name.replace(" ", "_").upper()[:20]
        return env["vote.type"].create(
            {
                "name": name,
                "code": code,
                "vote_value_type": "integer",
            }
        )

    @classmethod
    def _create_assembly_type(cls, env, name="Test assembly type", vote_type=None):
        """Create assembly.type. If vote_type not given, creates one."""
        if vote_type is None:
            vote_type = cls._create_vote_type(env, name="VT " + name)
        return env["assembly.type"].create(
            {
                "name": name,
                "code": "T" + name.replace(" ", "")[:8],
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "default_quorum_type": "percentage",
                "default_quorum_value": 50.0,
                "partner_domain": "[]",
            }
        )

    @classmethod
    def _create_partners(cls, env, count=3, prefix="Partner"):
        """Create res.partner records. Returns recordset."""
        return env["res.partner"].create(
            [
                {"name": f"{prefix} {i}", "is_company": False}
                for i in range(1, count + 1)
            ]
        )

    def _create_assembly_with_agenda(
        self,
        name="Test assembly",
        assembly_type=None,
        partner_domain=None,
        agenda_title="Point 1",
        requires_vote=True,
    ):
        """Create assembly in draft with one agenda item. Returns (assembly, agenda)."""
        env = self.env
        if assembly_type is None:
            vote_type = self._create_vote_type(env, name="VT Assembly")
            assembly_type = self._create_assembly_type(
                env, name="Type " + name, vote_type=vote_type
            )
        if partner_domain is None:
            partners = self._create_partners(env, 3)
            partner_domain = "[('id', 'in', %s)]" % partners.ids
        assembly = env["assembly.assembly"].create(
            {
                "name": name,
                "assembly_type_id": assembly_type.id,
                "partner_domain": partner_domain,
                "quorum_type": "percentage",
                "quorum_value": 50.0,
            }
        )
        # onchange does not run on create: ensure vote_type_ids for quorum/recompute
        if assembly.assembly_type_id.vote_type_ids and not assembly.vote_type_ids:
            assembly.write(
                {"vote_type_ids": [(6, 0, assembly.assembly_type_id.vote_type_ids.ids)]}
            )
        agenda_vals = {
            "assembly_id": assembly.id,
            "name": agenda_title,
            "requires_vote": requires_vote,
        }
        if requires_vote and assembly_type.vote_type_ids:
            agenda_vals["vote_type_id"] = assembly_type.vote_type_ids[0].id
        agenda = env["assembly.agenda"].create(agenda_vals)
        return assembly, agenda

    def _give_partner_votes(self, partner, vote_type, count=1):
        """Create or update partner.vote for partner and vote_type."""
        pv = self.env["partner.vote"].search(
            [
                ("partner_id", "=", partner.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        if pv:
            pv.vote_count_integer = count
        else:
            self.env["partner.vote"].create(
                {
                    "partner_id": partner.id,
                    "vote_type_id": vote_type.id,
                    "vote_count_integer": count,
                }
            )
