# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
# Large delegation + vote-recompute surface kept in one module for cohesion.
# pylint: disable=too-many-lines

import logging
import re
from collections import defaultdict, deque

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .assembly_mixin import assembly_safe_report_filename

_logger = logging.getLogger(__name__)


class AssemblyDelegation(models.Model):
    """Vote delegation between assembly attendees."""

    _name = "assembly.delegation"
    _inherit = ["assembly.mixin.open.assembly"]
    _description = "Vote delegation"
    _order = "assembly_id, partner_id"

    def _get_report_base_filename(self):
        self.ensure_one()
        delegator = assembly_safe_report_filename(
            self.partner_id.display_name, default=self.env._("Delegator")
        )
        delegate = assembly_safe_report_filename(
            self.delegate_partner_id.display_name, default=self.env._("Delegate")
        )
        asm = assembly_safe_report_filename(
            self.assembly_id.display_name, default=self.env._("Assembly")
        )
        return f"{asm} - {delegator} - {delegate}"

    assembly_id = fields.Many2one(
        "assembly.assembly",
        string="Assembly",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="assembly_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Delegator",
        required=True,
        ondelete="cascade",
        index=True,
        help=(
            "Member who transfers voting units. Saving this row registers the delegation; "
            "units move only after the delegate is Attended (confirmed present) (see vote "
            "transfer status). Delete the row to stop delegating."
        ),
    )
    delegate_partner_id = fields.Many2one(
        "res.partner",
        string="Delegate",
        required=True,
        ondelete="cascade",
        index=True,
        help=(
            "Must already be listed as an assembly attendee. Vote transfer for the covered "
            "types becomes active when they are recorded as Attended (confirmed present); "
            "until then the delegation is waiting."
        ),
    )
    vote_type_ids = fields.Many2many(
        "vote.type",
        "assembly_delegation_vote_type_rel",
        "delegation_id",
        "vote_type_id",
        string="Vote types",
        domain="[('active', '=', True)]",
        help=(
            "Vote types covered by this delegation. Leave empty to delegate every vote "
            "type configured on the assembly. Totals and roll-call use the stored "
            "snapshot on each attendee row (delegated out / delegated in)."
        ),
    )
    date_delegation = fields.Datetime(default=fields.Datetime.now)
    delegation_vote_transfer_state = fields.Selection(
        [
            ("waiting_delegate", "Waiting (delegate not attended yet)"),
            ("active", "Active (votes transfer to delegate)"),
        ],
        string="Vote transfer",
        compute="_compute_delegation_ux_display",
        help=(
            "Waiting: the delegation is saved but the delegate is not Attended "
            "(confirmed present), so units are not transferred yet. Active: the delegate "
            "is attended (confirmed present); covered types are transferred for vote totals "
            "(other rules such as vote-type overlap still apply in the engine)."
        ),
    )
    delegation_delegate_attendee_state = fields.Selection(
        [
            ("no_row", "Not listed as attendee"),
            (
                "registered",
                "Listed — not finalized",
            ),
            ("confirmed", "Attended (confirmed present)"),
            ("absent", "Did not attend"),
        ],
        string="Delegate attendance",
        compute="_compute_delegation_ux_display",
    )
    delegation_snapshot_units_out = fields.Float(
        string="Delegator units delegated out",
        digits=(16, 4),
        compute="_compute_delegation_ux_display",
        help=(
            "Sum of stored delegated-out units on the delegator's vote lines for the types "
            "covered by this delegation, when transfer is active."
        ),
    )
    delegation_snapshot_units_in = fields.Float(
        string="Delegate units from this delegation",
        digits=(16, 4),
        compute="_compute_delegation_ux_display",
        help=(
            "Sum of stored delegated-in units on the delegate's vote lines for the types "
            "covered by this delegation, when transfer is active."
        ),
    )
    delegation_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("revoked", "Revoked"),
        ],
        string="Delegation state",
        compute="_compute_delegation_ux_display",
        help=(
            "Maps vote transfer for older UI and exports: Waiting → Draft, Active → "
            "Confirmed. Prefer Vote transfer; revoked rows no longer exist (unlink the "
            "delegation to revoke)."
        ),
    )

    _sql_constraints = [
        (
            "delegation_partner_ne_delegate",
            "CHECK(partner_id <> delegate_partner_id)",
            "The delegator and delegate must be different partners.",
        ),
    ]

    @api.constrains(
        "assembly_id",
        "partner_id",
        "delegate_partner_id",
        "vote_type_ids",
    )
    def _check_delegation_constraints(self):
        for rec in self:
            rec._delegation_validate_record_state()

    @api.model
    def _delegation_effective_vote_types(self, assembly, m2m_vote_types):
        """Expanded ``vote.type`` recordset for a (assembly, M2M) snapshot.

        Same rules as :meth:`_get_effective_vote_types` on a saved row:

        * Empty ``m2m_vote_types`` → all ``assembly.vote_type_ids`` (full delegation).
        * Non-empty → only those types (partial).

        Use **before** a row exists (``create`` ``vals``). On a record, call
        :meth:`_get_effective_vote_types` instead.

        Explicit selections must still be ⊆ assembly
        (:meth:`_delegation_validate_vote_types_in_assembly`). Used for overlap,
        cycle, and chain checks.
        """
        VoteType = self.env["vote.type"]
        if not assembly or not assembly.exists():
            return VoteType.browse()
        if m2m_vote_types.ids:
            return m2m_vote_types.sorted("id")
        return assembly.vote_type_ids.sorted("id")

    @api.model
    def _effective_delegations_partner_layer(self, delegations):
        """Partner-layer rules only: delegate is a confirmed attendee.

        Vote-type expansion (empty M2M ⇒ all assembly types) is defined by
        :meth:`_get_effective_vote_types` / :meth:`delegation_covers_vote_type` at
        use sites; this step does not filter by type overlap.

        **Not applied here:** inbound/outbound chain exclusion; those run inside
        :meth:`_get_effective_delegations` for a member edge when requested.
        """
        if not delegations:
            return delegations
        Attendee = self.env["assembly.attendee"]
        by_assembly = defaultdict(set)
        for d in delegations:
            aid = d.assembly_id.id if d.assembly_id else False
            dp = d.delegate_partner_id.id if d.delegate_partner_id else False
            if aid and dp:
                by_assembly[aid].add(dp)
        confirmed_delegate_ids = {}
        for aid, partner_ids in by_assembly.items():
            lines = Attendee._search_attendees_for_assembly(
                aid,
                partner_ids=list(partner_ids),
                attendee_state="confirmed",
            )
            confirmed_delegate_ids[aid] = set(lines.mapped("partner_id").ids)
        return delegations.filtered(
            lambda d, m=confirmed_delegate_ids: d.delegate_partner_id.id
            in m.get(d.assembly_id.id, ())
        )

    @api.model
    def _apply_vote_effect_partner_filters(self, delegations):
        """Backward-compatible alias for :meth:`_get_effective_delegations` with ``delegations=``."""
        return self._get_effective_delegations(delegations=delegations)

    @api.model
    def _search_all_delegations_for_assembly(self, assembly_id):
        """All delegation rows for an assembly (no partner or delegate filter)."""
        if not assembly_id:
            return self.browse()
        return self.search([("assembly_id", "=", assembly_id)])

    def _get_effective_vote_types(self):
        """Canonical expanded ``vote.type`` set for **this** delegation.

        Overlap validation compares :meth:`_get_effective_vote_types` against
        siblings' :meth:`_get_effective_vote_types` (intersection non-empty ⇒ clash).
        """
        self.ensure_one()
        return self.env["assembly.delegation"]._delegation_effective_vote_types(
            self.assembly_id, self.vote_type_ids
        )

    def delegation_covers_vote_type(self, vote_type):
        """Whether this delegation transfers ``vote_type`` (uses expanded M2M vs assembly types)."""
        self.ensure_one()
        if not vote_type:
            return False
        return vote_type in self._get_effective_vote_types()

    @api.model
    def _exclude_outbound_vote_chain_overlap(
        self, assembly_id, delegator_partner_id, delegations_out
    ):
        """Drop outbound rows that overlap effective inbound to the same partner (no chain).

        Mirrors the delegator side of :meth:`_delegation_validate_no_vote_delegation_chain`
        for read-time vote math; on consistent data this is a no-op.
        """
        if not delegations_out or not assembly_id or not delegator_partner_id:
            return delegations_out
        inbound = self._search_delegations_for_member_edge(
            "delegate", assembly_id, delegator_partner_id
        )
        inbound = self._get_effective_delegations(delegations=inbound)
        if not inbound:
            return delegations_out
        inbound_eff = tuple(inc._get_effective_vote_types() for inc in inbound)
        return delegations_out.filtered(
            lambda d, ie=inbound_eff: not any(
                d._get_effective_vote_types() & t for t in ie
            )
        )

    @api.model
    def _exclude_inbound_vote_chain_overlap(
        self, assembly_id, delegate_partner_id, delegations_in
    ):
        """Drop inbound rows that overlap effective outbound from the same partner (no chain).

        Mirrors the delegate side of :meth:`_delegation_validate_no_vote_delegation_chain`
        for read-time vote math; on consistent data this is a no-op.
        """
        if not delegations_in or not assembly_id or not delegate_partner_id:
            return delegations_in
        outbound = self._search_delegations_for_member_edge(
            "delegator", assembly_id, delegate_partner_id
        )
        outbound = self._get_effective_delegations(delegations=outbound)
        if not outbound:
            return delegations_in
        outbound_eff = tuple(ob._get_effective_vote_types() for ob in outbound)
        return delegations_in.filtered(
            lambda d, oe=outbound_eff: not any(
                d._get_effective_vote_types() & t for t in oe
            )
        )

    @api.model
    def _search_delegations_for_member_edge(
        self, role, assembly_id, partner_id, pool=None
    ):
        """Delegations where ``partner_id`` acts as ``role`` on the edge."""
        if pool is not None:
            scoped = pool.filtered(lambda d, a=assembly_id: d.assembly_id.id == a)
            if role == "delegator":
                return scoped.filtered(lambda d, x=partner_id: d.partner_id.id == x)
            return scoped.filtered(
                lambda d, x=partner_id: d.delegate_partner_id.id == x
            )
        domain = [("assembly_id", "=", assembly_id)]
        if role == "delegator":
            domain.append(("partner_id", "=", partner_id))
        else:
            domain.append(("delegate_partner_id", "=", partner_id))
        return self.search(domain)

    @api.model
    def _narrow_inbound_delegations_for_stored_vote_lines(
        self, delegations, assembly_id
    ):
        """Inbound delegations whose delegator may contribute ``delegated_in`` to stored lines."""
        if not delegations:
            return delegations
        delegator_partner_ids = delegations.mapped("partner_id").ids
        if not delegator_partner_ids:
            return self.browse()
        Attendee = self.env["assembly.attendee"]
        lines = Attendee._search_attendees_for_assembly(
            assembly_id,
            partner_ids=list(delegator_partner_ids),
        )
        absent_delegator_pids = set(
            lines.filtered_domain([("attendee_state", "=", "absent")])
            .mapped("partner_id")
            .ids
        )
        keep_delegator_pids = {
            pid for pid in delegator_partner_ids if pid not in absent_delegator_pids
        }
        return delegations.filtered(
            lambda d, kp=keep_delegator_pids: d.partner_id.id in kp
        )

    @api.model
    def _get_effective_delegations(
        self,
        assembly_id=None,
        member_partner_id=None,
        role=None,
        *,
        delegations=None,
        confirmed_delegations_pool=None,
        for_stored_vote_lines=True,
        apply_delegate_attendee_effect=True,
        member_attendee=None,
    ):
        """Single entry for **effective** delegations (same business rules everywhere).

        **Two call shapes:**

        1. ``delegations=<recordset>`` — apply only the partner layer (saved row +
           confirmed delegate attendee). Used for quorum *presence* (delegators
           without their own attendee row), vote recompute batching, and internal
           chain helpers. Unrelated to ``assembly.representation`` (legal/agent
           representation). Does not apply chain exclusion.

        2. ``assembly_id``, ``member_partner_id``, ``role`` — delegations on that
           member edge (delegator or delegate), then optionally partner layer,
           optional :meth:`_narrow_inbound_delegations_for_stored_vote_lines` for
           inbound stored lines, and :meth:`_exclude_outbound_vote_chain_overlap` /
           :meth:`_exclude_inbound_vote_chain_overlap` so votes cannot chain through
           overlapping expanded vote types.

        **Always enforced on the member-edge path:** delegate is a confirmed attendee
        when partner layer is applied, and
        vote-type semantics follow :meth:`_get_effective_vote_types` at callers.

        ``assembly.attendee._get_effective_delegations`` delegates here with
        ``member_attendee`` set when possible.
        """
        if delegations is not None:
            return self._effective_delegations_partner_layer(delegations)
        if (
            not assembly_id
            or not member_partner_id
            or role not in ("delegator", "delegate")
        ):
            return self.browse()

        delegations = self._search_delegations_for_member_edge(
            role, assembly_id, member_partner_id, pool=confirmed_delegations_pool
        )
        if apply_delegate_attendee_effect:
            delegations = self._effective_delegations_partner_layer(delegations)
            if role == "delegator":
                delegations = self._exclude_outbound_vote_chain_overlap(
                    assembly_id, member_partner_id, delegations
                )
        if role == "delegate":
            att = member_attendee[:1] if member_attendee is not None else None
            if att is None or not att:
                att = self.env["assembly.attendee"]._search_for_assembly_partner(
                    assembly_id, member_partner_id, limit=1
                )
            if for_stored_vote_lines and (not att or att.attendee_state != "confirmed"):
                return self.browse()
            if for_stored_vote_lines:
                delegations = self._narrow_inbound_delegations_for_stored_vote_lines(
                    delegations, assembly_id
                )
            if apply_delegate_attendee_effect:
                delegations = self._exclude_inbound_vote_chain_overlap(
                    assembly_id, member_partner_id, delegations
                )
            return delegations
        return delegations

    @api.model
    def _batch_existing_attendee_pairs(self, pairs):
        pairs = {p for p in pairs if p[0] and p[1]}
        if not pairs:
            return set()
        by_assembly = defaultdict(set)
        for assembly_id, partner_id in pairs:
            by_assembly[assembly_id].add(partner_id)
        Attendee = self.env["assembly.attendee"].sudo()
        found = set()
        for assembly_id, partner_ids in by_assembly.items():
            recs = Attendee._search_attendees_for_assembly(
                assembly_id, partner_ids=list(partner_ids)
            )
            for att in recs:
                found.add((att.assembly_id.id, att.partner_id.id))
        return found

    @api.model
    def _delegation_many2one_id_from_vals_or_record(self, vals, record, fname):
        if fname in vals:
            v = vals[fname]
            if not v:
                return False
            if isinstance(v, models.BaseModel):
                return v.id
            if isinstance(v, int):
                return v
            if isinstance(v, (list, tuple)) and v:
                return v[0]
            return False
        if record:
            f = record[fname]
            return f.id if f else False
        return False

    @api.model
    def _delegation_vote_type_ids_from_vals_or_record(self, vals, record):
        VoteType = self.env["vote.type"]
        if "vote_type_ids" not in vals:
            return record.vote_type_ids if record else VoteType
        commands = vals["vote_type_ids"]
        if not commands:
            return VoteType
        ids = set()
        for command in commands:
            if not command:
                continue
            typ = command[0]
            if typ in (5,):
                ids.clear()
            elif typ in (6,) and len(command) == 3:
                ids = set(command[2])
            elif typ in (4,) and len(command) >= 2:
                ids.add(command[1])
            elif typ in (3,) and len(command) >= 2:
                ids.discard(command[1])
        return VoteType.browse(list(ids))

    def _delegation_validate_not_self_delegation(self, partner_id, delegate_partner_id):
        if partner_id and delegate_partner_id and partner_id == delegate_partner_id:
            raise ValidationError(
                self.env._("The delegator and delegate must be different partners.")
            )

    def _delegation_validate_endpoints_are_attendees(
        self, assembly_id, _partner_id, delegate_partner_id
    ):
        need = set()
        if assembly_id and delegate_partner_id:
            need.add((assembly_id, delegate_partner_id))
        found = self._batch_existing_attendee_pairs(need)
        if assembly_id and delegate_partner_id:
            if (assembly_id, delegate_partner_id) not in found:
                raise ValidationError(
                    self.env._(
                        "The delegate must be an attendee in the assembly. "
                        "Please add the delegate as an attendee first."
                    )
                )

    def _delegation_validate_delegate_convocable(self, assembly, delegate_partner):
        if not assembly or not delegate_partner:
            return
        if not assembly.exists():
            return
        partners = self.env["res.partner"].search(assembly._get_partner_domain())
        if delegate_partner not in partners:
            raise ValidationError(
                self.env._(
                    "The delegate must be included in the convocable partners list."
                )
            )

    def _delegation_validate_vote_types_in_assembly(self, vote_type_rs, assembly):
        """Reject explicit ``vote_type_ids`` not included on the assembly."""
        if not vote_type_rs.ids or not assembly or not assembly.vote_type_ids:
            return
        invalid = vote_type_rs - assembly.vote_type_ids
        if invalid:
            raise ValidationError(
                self.env._(
                    "Vote types must be selected from the assembly's vote types."
                )
            )

    @api.model
    def _delegation_graph_reachable(
        self, partner_neighbors, start_partner_id, end_partner_id
    ):
        if not start_partner_id or not end_partner_id:
            return False
        queue = deque([start_partner_id])
        seen = {start_partner_id}
        while queue:
            cur = queue.popleft()
            if cur == end_partner_id:
                return True
            for nxt in partner_neighbors.get(cur, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return False

    @api.model
    def _delegation_cycle_edge_lists_by_vote_type(
        self,
        confirmed_delegations,
        exclude_delegation_id,
    ):
        edge_lists_by_vt = defaultdict(list)
        for d in confirmed_delegations:
            if exclude_delegation_id and d.id == exclude_delegation_id:
                continue
            u, v = d.partner_id.id, d.delegate_partner_id.id
            for vt_id in d._get_effective_vote_types().ids:
                edge_lists_by_vt[vt_id].append((u, v))
        return edge_lists_by_vt

    @api.model
    def _delegation_assert_no_delegation_cycles(
        self,
        assembly_id,
        delegator_partner_id,
        delegate_partner_id,
        effective_vote_type_rs,
        assembly,
        exclude_delegation_id,
        confirmed_delegations=None,
    ):
        if not assembly_id or not delegator_partner_id or not delegate_partner_id:
            return
        if not assembly or not assembly.exists():
            return
        types_to_check = effective_vote_type_rs
        if not types_to_check:
            return
        confirmed = confirmed_delegations
        if confirmed is None:
            confirmed = self._search_all_delegations_for_assembly(assembly_id)
        edge_lists_by_vt = self._delegation_cycle_edge_lists_by_vote_type(
            self._get_effective_delegations(delegations=confirmed),
            exclude_delegation_id,
        )
        err = self.env._(
            "This delegation would create a circular chain of vote delegations "
            "for at least one vote type. Delegations must not form cycles "
            "(for example A → B and B → A on overlapping vote types)."
        )
        for vt in types_to_check:
            edges = edge_lists_by_vt.get(vt.id, ())
            if not edges:
                continue
            neighbors = defaultdict(list)
            for u, v in edges:
                neighbors[u].append(v)
            if self._delegation_graph_reachable(
                neighbors,
                delegate_partner_id,
                delegator_partner_id,
            ):
                raise ValidationError(err)

    @api.model
    def _delegation_validate_no_vote_delegation_chain(
        self,
        assembly_id,
        delegator_partner_id,
        delegate_partner_id,
        effective_out_types,
        exclude_delegation_id=None,
    ):
        """Block overlapping delegations that would chain received votes.

        A partner cannot delegate vote types they receive via another delegation,
        nor receive a delegation while delegating the same types outward (no
        A→B→C on overlapping ``vote.type`` coverage).
        """
        if (
            not assembly_id
            or not delegator_partner_id
            or not delegate_partner_id
            or not effective_out_types
        ):
            return
        err_inbound = self.env._(
            "Chained delegations are not allowed: this delegator already receives "
            "votes (delegation to them) on at least one of the same vote "
            "types. Only your own votes can be delegated, not votes received from "
            "someone else."
        )
        err_outbound = self.env._(
            "Chained delegations are not allowed: this delegate already delegates "
            "outward on overlapping vote types. Remove or narrow that delegation "
            "before they can receive these votes."
        )
        inbound_to_delegator = self._search_delegations_for_member_edge(
            "delegate", assembly_id, delegator_partner_id
        )
        if exclude_delegation_id:
            inbound_to_delegator = inbound_to_delegator.filtered(
                lambda d, x=exclude_delegation_id: d.id != x
            )
        inbound_to_delegator = self._get_effective_delegations(
            delegations=inbound_to_delegator
        )
        for inc in inbound_to_delegator:
            if effective_out_types & inc._get_effective_vote_types():
                raise ValidationError(err_inbound)
        outbound_from_delegate = self._search_delegations_for_member_edge(
            "delegator", assembly_id, delegate_partner_id
        )
        if exclude_delegation_id:
            outbound_from_delegate = outbound_from_delegate.filtered(
                lambda d, x=exclude_delegation_id: d.id != x
            )
        outbound_from_delegate = self._get_effective_delegations(
            delegations=outbound_from_delegate
        )
        for out in outbound_from_delegate:
            if effective_out_types & out._get_effective_vote_types():
                raise ValidationError(err_outbound)

    @api.model
    def _delegation_intersect_effective_vote_types(self, effective_a, effective_b):
        """Intersection of two **expanded** ``vote.type`` recordsets.

        Overlap for duplicate outbound validation is non-empty intersection.
        Either side may come from :meth:`_get_effective_vote_types` or from
        :meth:`_delegation_effective_vote_types` at create time.
        """
        if not effective_a or not effective_b:
            return self.env["vote.type"].browse()
        return effective_a & effective_b

    def _delegation_validate_no_overlapping_outbound(
        self,
        assembly_id,
        partner_id,
        exclude_delegation_id,
        effective_vote_type_rs,
        sibling_delegations=None,
    ):
        """Reject two outbound delegations for the same partner with overlapping types.

        Each row's coverage is its **expanded** effective types
        (:meth:`_get_effective_vote_types`): empty M2M ⇒ all assembly types;
        non-empty M2M ⇒ only selected types. Disjoint partial delegations are
        allowed (empty intersection).
        """
        if not assembly_id or not partner_id:
            return
        err = self.env._(
            "A delegation already exists in this assembly that covers the same vote "
            "type(s). Remove or edit the existing delegation first."
        )
        if sibling_delegations is not None:
            siblings = sibling_delegations
        else:
            siblings = self.search(
                [
                    ("assembly_id", "=", assembly_id),
                    ("partner_id", "=", partner_id),
                ]
            )
        candidate = effective_vote_type_rs
        for other in siblings:
            if other.id == exclude_delegation_id:
                continue
            if self._delegation_intersect_effective_vote_types(
                candidate, other._get_effective_vote_types()
            ):
                raise ValidationError(err)

    @api.model
    def _delegation_validate_create_vals(self, vals):
        assembly_id = self._delegation_many2one_id_from_vals_or_record(
            vals, None, "assembly_id"
        )
        partner_id = self._delegation_many2one_id_from_vals_or_record(
            vals, None, "partner_id"
        )
        delegate_partner_id = self._delegation_many2one_id_from_vals_or_record(
            vals, None, "delegate_partner_id"
        )
        vote_type_rs = self._delegation_vote_type_ids_from_vals_or_record(vals, None)
        assembly = self.env["assembly.assembly"].browse(assembly_id)
        delegate_partner = self.env["res.partner"].browse(delegate_partner_id)
        self._delegation_validate_not_self_delegation(partner_id, delegate_partner_id)
        self._delegation_validate_endpoints_are_attendees(
            assembly_id, partner_id, delegate_partner_id
        )
        self._delegation_validate_delegate_convocable(assembly, delegate_partner)
        self._delegation_validate_vote_types_in_assembly(vote_type_rs, assembly)
        effective_types = self._delegation_effective_vote_types(assembly, vote_type_rs)
        all_asm = self._search_all_delegations_for_assembly(assembly_id)
        siblings = all_asm.filtered(lambda r: r.partner_id.id == partner_id)
        self._delegation_validate_no_overlapping_outbound(
            assembly_id,
            partner_id,
            False,
            effective_types,
            sibling_delegations=siblings,
        )
        self._delegation_validate_no_vote_delegation_chain(
            assembly_id,
            partner_id,
            delegate_partner_id,
            effective_types,
            exclude_delegation_id=None,
        )

    def _delegation_validate_record_state(self):
        assembly = self.assembly_id
        assembly_id = assembly.id if assembly else False
        partner_id = self.partner_id.id if self.partner_id else False
        delegate_partner_id = (
            self.delegate_partner_id.id if self.delegate_partner_id else False
        )
        vote_type_rs = self.vote_type_ids
        effective_types = self._get_effective_vote_types()
        delegate_partner = self.delegate_partner_id
        self._delegation_validate_not_self_delegation(partner_id, delegate_partner_id)
        self._delegation_validate_endpoints_are_attendees(
            assembly_id, partner_id, delegate_partner_id
        )
        self._delegation_validate_delegate_convocable(assembly, delegate_partner)
        self._delegation_validate_vote_types_in_assembly(vote_type_rs, assembly)
        self._delegation_validate_no_overlapping_outbound(
            assembly_id,
            partner_id,
            self.id,
            effective_types,
        )
        if assembly_id and partner_id and delegate_partner_id:
            self._delegation_validate_no_vote_delegation_chain(
                assembly_id,
                partner_id,
                delegate_partner_id,
                effective_types,
                exclude_delegation_id=self.id,
            )
        if assembly_id and partner_id and delegate_partner_id:
            self._delegation_assert_no_delegation_cycles(
                assembly_id=assembly_id,
                delegator_partner_id=partner_id,
                delegate_partner_id=delegate_partner_id,
                effective_vote_type_rs=effective_types,
                assembly=assembly,
                exclude_delegation_id=self.id,
            )

    @api.model
    def _delegation_recompute_add_endpoint_partners(self, by_assembly, rec):
        aid = rec.assembly_id.id
        if not aid:
            return
        pid = rec.partner_id.id
        did = rec.delegate_partner_id.id
        if pid:
            by_assembly[aid].add(pid)
        if did:
            by_assembly[aid].add(did)

    def _delegation_collect_vote_recompute_attendees(  # pylint: disable=too-many-nested-blocks
        self,
        vals=None,
        post_create=False,
        prev_endpoint_partners_by_id=None,
    ):
        vals = dict(vals or {})
        Attendee = self.env["assembly.attendee"]
        by_assembly = defaultdict(set)
        if post_create:
            for delegation in self._get_effective_delegations(delegations=self):
                self._delegation_recompute_add_endpoint_partners(
                    by_assembly, delegation
                )
        else:
            prev_eps = prev_endpoint_partners_by_id or {}
            vote_types_changed = "vote_type_ids" in vals
            assembly_changed = "assembly_id" in vals
            for rec in self:
                aid = rec.assembly_id.id
                snap = prev_eps.get(rec.id)
                if aid and snap is not None:
                    op, od = snap
                    np, nd = rec.partner_id.id, rec.delegate_partner_id.id
                    if (op, od) != (np, nd):
                        for pid in (op, od, np, nd):
                            if pid:
                                by_assembly[aid].add(pid)
                if vote_types_changed or assembly_changed:
                    self._delegation_recompute_add_endpoint_partners(by_assembly, rec)
        attendees = Attendee.browse()
        for aid, partner_ids in by_assembly.items():
            if not partner_ids:
                continue
            attendees |= Attendee._search_attendees_for_assembly(
                aid, partner_ids=list(partner_ids)
            )
        return attendees

    def _delegation_collect_unlink_vote_recompute_attendees(self):
        """Both endpoints per row must refresh snapshots after the row is removed."""
        Attendee = self.env["assembly.attendee"]
        by_assembly = defaultdict(set)
        for rec in self:
            self._delegation_recompute_add_endpoint_partners(by_assembly, rec)
        attendees = Attendee.browse()
        for aid, partner_ids in by_assembly.items():
            if not partner_ids:
                continue
            attendees |= Attendee._search_attendees_for_assembly(
                aid, partner_ids=list(partner_ids)
            )
        return attendees

    def _recompute_votes_after_delegation_persist(
        self,
        vals,
        post_create=False,
        prev_endpoint_partners_by_id=None,
    ):
        attendees = self._delegation_collect_vote_recompute_attendees(
            vals,
            post_create=post_create,
            prev_endpoint_partners_by_id=prev_endpoint_partners_by_id,
        )
        self.env["assembly.attendee"].recompute_votes(attendees)

    @api.depends(
        "partner_id",
        "delegate_partner_id",
        "vote_type_ids",
        "assembly_id",
        "assembly_id.attendee_ids.attendee_state",
        "assembly_id.attendee_ids.partner_id",
        "assembly_id.attendee_ids.attendee_vote_ids.delegated_out_votes",
        "assembly_id.attendee_ids.attendee_vote_ids.delegated_in_votes",
        "assembly_id.attendee_ids.attendee_vote_ids.vote_type_id",
    )
    def _compute_delegation_ux_display(self):
        Attendee = self.env["assembly.attendee"]
        effective_rs = self.env["assembly.delegation"]._get_effective_delegations(
            delegations=self
        )
        for rec in self:
            rec.delegation_snapshot_units_out = 0.0
            rec.delegation_snapshot_units_in = 0.0
            rec.delegation_delegate_attendee_state = "no_row"
            rec.delegation_vote_transfer_state = "waiting_delegate"
            rec.delegation_state = "draft"
            if not rec.assembly_id or not rec.delegate_partner_id:
                continue
            delegate_att = Attendee._search_for_assembly_partner(
                rec.assembly_id.id,
                rec.delegate_partner_id.id,
                limit=1,
            )
            if not delegate_att:
                rec.delegation_delegate_attendee_state = "no_row"
            else:
                rec.delegation_delegate_attendee_state = delegate_att.attendee_state
            if rec in effective_rs:
                rec.delegation_vote_transfer_state = "active"
            if rec.delegation_vote_transfer_state == "active":
                rec.delegation_state = "confirmed"
            if rec.delegation_vote_transfer_state != "active":
                continue
            vt_ids = set(rec._get_effective_vote_types().ids)
            if not vt_ids:
                continue
            delegator_att = Attendee._search_for_assembly_partner(
                rec.assembly_id.id,
                rec.partner_id.id,
                limit=1,
            )
            if delegator_att:
                lines_out = delegator_att.attendee_vote_ids.filtered(
                    lambda line, ids=vt_ids: line.vote_type_id.id in ids
                )
                rec.delegation_snapshot_units_out = sum(
                    lines_out.mapped("delegated_out_votes")
                )
            if delegate_att:
                lines_in = delegate_att.attendee_vote_ids.filtered(
                    lambda line, ids=vt_ids: line.vote_type_id.id in ids
                )
                rec.delegation_snapshot_units_in = sum(
                    lines_in.mapped("delegated_in_votes")
                )

    @api.model
    def _assembly_cleanup_delegation_state_in_views(self):
        ir_ui_view = self.env["ir.ui.view"].sudo()
        candidates = ir_ui_view.search(
            [
                ("arch_db", "ilike", "delegation_state"),
                ("type", "not in", ("qweb",)),
            ]
        )
        field_attr_re = re.compile(r"""(?m)\bname\s*=\s*(['"])delegation_state\1""")
        replacements = (
            (
                "delegation_state == 'confirmed'",
                "delegation_vote_transfer_state == 'active'",
            ),
            (
                'delegation_state == "confirmed"',
                "delegation_vote_transfer_state == 'active'",
            ),
            (
                "delegation_state == 'draft'",
                "delegation_vote_transfer_state == 'waiting_delegate'",
            ),
            (
                'delegation_state == "draft"',
                "delegation_vote_transfer_state == 'waiting_delegate'",
            ),
            (
                "delegation_state == 'revoked'",
                "delegation_vote_transfer_state == 'waiting_delegate'",
            ),
            (
                'delegation_state == "revoked"',
                "delegation_vote_transfer_state == 'waiting_delegate'",
            ),
            (
                "'delegation_state', '=', 'confirmed'",
                "'delegation_vote_transfer_state', '=', 'active'",
            ),
            (
                "'delegation_state', '=', 'draft'",
                "'delegation_vote_transfer_state', '=', 'waiting_delegate'",
            ),
            (
                "'delegation_state', '=', 'revoked'",
                "'delegation_vote_transfer_state', '=', 'waiting_delegate'",
            ),
            (
                '"delegation_state", "=", "confirmed"',
                '"delegation_vote_transfer_state", "=", "active"',
            ),
            (
                '"delegation_state", "=", "draft"',
                '"delegation_vote_transfer_state", "=", "waiting_delegate"',
            ),
            (
                '"delegation_state", "=", "revoked"',
                '"delegation_vote_transfer_state", "=", "waiting_delegate"',
            ),
            (
                "group_by': 'delegation_state'",
                "group_by': 'delegation_vote_transfer_state'",
            ),
            (
                'group_by": "delegation_state"',
                'group_by": "delegation_vote_transfer_state"',
            ),
            (
                "default_delegation_state",
                "default_delegation_vote_transfer_state",
            ),
        )
        for view in candidates:
            arch = view.arch_db
            if not arch or "delegation_state" not in arch:
                continue
            new_arch = field_attr_re.sub(
                r"name=\1delegation_vote_transfer_state\1",
                arch,
            )
            for old, new in replacements:
                new_arch = new_arch.replace(old, new)
            if new_arch == arch:
                continue
            if "delegation_state" in new_arch:
                _logger.warning(
                    "base_assembly: view id=%s model=%s type=%s still contains "
                    "delegation_state; fix manually or in Studio",
                    view.id,
                    view.model,
                    view.type,
                )
                continue
            try:
                view.write({"arch_db": new_arch})
            except Exception as exc:  # pylint: disable=broad-exception-caught
                _logger.warning(
                    "base_assembly: could not write cleaned view id=%s: %s",
                    view.id,
                    exc,
                )
                continue
            _logger.info(
                "base_assembly: updated view id=%s (%s) delegation_state references",
                view.id,
                view.name,
            )
        return True

    def _register_hook(self):
        super()._register_hook()
        try:
            self._assembly_cleanup_delegation_state_in_views()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            _logger.warning(
                "base_assembly: delegation view cleanup at registry init failed: %s",
                exc,
            )

    @api.model_create_multi
    def create(self, vals_list):
        if not vals_list:
            return self.browse()
        self.check_access("create")
        asm_ids = {v.get("assembly_id") for v in vals_list if v.get("assembly_id")}
        if asm_ids:
            self.env["assembly.assembly"].browse(
                list(asm_ids)
            ).exists()._assembly_ensure_not_closed_for_related_changes()
        for vals in vals_list:
            self._delegation_validate_create_vals(vals)
        delegations = super().create(vals_list)
        delegations._recompute_votes_after_delegation_persist({}, post_create=True)
        return delegations

    def write(self, vals):
        vals = dict(vals)
        if self:
            self.mapped("assembly_id")._assembly_ensure_not_closed_for_related_changes()
            self.check_access("write")
            self.check_field_access_rights("write", list(vals))
        prev_endpoint_partners_by_id = None
        if self and ("partner_id" in vals or "delegate_partner_id" in vals):
            prev_endpoint_partners_by_id = {
                d.id: (d.partner_id.id, d.delegate_partner_id.id) for d in self
            }
        res = super().write(vals)
        self._recompute_votes_after_delegation_persist(
            vals,
            prev_endpoint_partners_by_id=prev_endpoint_partners_by_id,
        )
        return res

    def unlink(self):
        self.mapped("assembly_id")._assembly_ensure_not_closed_for_related_changes()
        attendees = self._delegation_collect_unlink_vote_recompute_attendees()
        res = super().unlink()
        if attendees:
            self.env["assembly.attendee"].recompute_votes(attendees)
        return res
