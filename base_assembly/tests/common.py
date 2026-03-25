# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Small shared factories for ``base_assembly`` tests (no fixture framework).

Quorum stored fields depend on ``assembly.assembly_state`` (e.g. cancelled → no present).
"""

import uuid


class AssemblyTestMixin:
    """Explicit ORM helpers for partners, votes, assemblies, attendees, delegations."""

    # --- Partners (1) ---

    @classmethod
    def _create_partners(cls, env, count=3, prefix="Partner"):
        """Several ``res.partner`` rows (natural persons by default)."""
        return env["res.partner"].create(
            [
                {"name": f"{prefix} {i}", "is_company": False}
                for i in range(1, count + 1)
            ]
        )

    # --- Vote types (2) ---

    @classmethod
    def _create_vote_type(cls, env, name="Test vote type", code=None):
        """One ``vote.type``; ``code`` is unique if omitted."""
        if code is None:
            base = name.replace(" ", "_").upper()[:12]
            code = f"{base}_{uuid.uuid4().hex[:10]}"
        return env["vote.type"].create(
            {
                "name": name,
                "code": code,
                "vote_value_type": "integer",
            }
        )

    # --- Partner vote amounts (3) ---

    def _give_partner_votes(self, partner, vote_type, count=1):
        """Set ``partner.vote`` for one partner and vote type (create or write)."""
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

    # --- Assembly type (4) ---

    @classmethod
    def _create_assembly_type(cls, env, name="Test assembly type", vote_type=None):
        """One ``assembly.type``; creates a vote type if none passed."""
        if vote_type is None:
            vote_type = cls._create_vote_type(env, name="VT " + name)
        return env["assembly.type"].create(
            {
                "name": name,
                "code": "T" + name.replace(" ", "")[:6] + uuid.uuid4().hex[:8],
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "default_quorum_type": "percentage",
                "default_quorum_value": 50.0,
                "partner_domain": "[]",
            }
        )

    # --- Assembly (5), optional first agenda line (8) ---

    def _create_assembly(
        self,
        name="Test assembly",
        assembly_type=None,
        partner_domain=None,
    ):
        """``assembly.assembly`` in draft, ``vote_type_ids`` synced from type; no agenda."""
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
        if assembly.assembly_type_id.vote_type_ids and not assembly.vote_type_ids:
            assembly.write(
                {"vote_type_ids": [(6, 0, assembly.assembly_type_id.vote_type_ids.ids)]}
            )
        return assembly

    def _create_assembly_with_agenda(  # pylint: disable=too-many-arguments,R0917
        self,
        name="Test assembly",
        assembly_type=None,
        partner_domain=None,
        agenda_title="Point 1",
        requires_vote=True,
    ):
        """Assembly plus one ``assembly.agenda`` (typical model-test entry point)."""
        assembly = self._create_assembly(
            name=name,
            assembly_type=assembly_type,
            partner_domain=partner_domain,
        )
        assembly_type = assembly.assembly_type_id
        env = self.env
        agenda_vals = {
            "assembly_id": assembly.id,
            "name": agenda_title,
            "requires_vote": requires_vote,
        }
        if requires_vote and assembly_type.vote_type_ids:
            agenda_vals["vote_type_id"] = assembly_type.vote_type_ids[0].id
        agenda = env["assembly.agenda"].create(agenda_vals)
        return assembly, agenda

    def _next_agenda_sequence(self, assembly):
        """Next sequence for another agenda line on this assembly."""
        agendas = assembly.agenda_ids
        if not agendas:
            return 10
        return max(agendas.mapped("sequence")) + 10

    # --- Attendees (6) ---

    def _confirm_attendees(self, attendees, *, vote_type=None, votes_each=1):
        """Optional ``partner.vote`` per row, then ``action_confirm`` (no other side effects)."""
        if vote_type is not None:
            for att in attendees:
                self._give_partner_votes(att.partner_id, vote_type, votes_each)
        attendees.action_confirm()
        return attendees

    # --- Delegations (7) ---

    def _create_delegation(
        self,
        assembly,
        delegator_partner,
        delegate_partner,
        vote_type_ids_command,
        delegation_state="confirmed",
    ):
        """One ``assembly.delegation``; caller must satisfy confirm/attendee rules."""
        return self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator_partner.id,
                "delegate_partner_id": delegate_partner.id,
                "vote_type_ids": vote_type_ids_command,
                "delegation_state": delegation_state,
            }
        )

    # --- Agenda / voting shortcut (8) ---

    def _open_voting_on_agenda(self, assembly, agenda):
        """Lifecycle through session and ``action_start_voting``; returns ``assembly.voting``."""
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        return self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
