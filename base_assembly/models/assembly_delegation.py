# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
# Large delegation + vote-recompute surface kept in one module for cohesion.
# pylint: disable=too-many-lines

from collections import defaultdict, deque

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_DELEGATION_STATE_KEYS = frozenset({"draft", "confirmed", "revoked"})

_DELEGATION_ALLOWED_STATE_TRANSITIONS = {
    "draft": frozenset({"confirmed", "revoked"}),
    "confirmed": frozenset({"revoked"}),
    "revoked": frozenset({"confirmed"}),
}


class AssemblyDelegation(models.Model):
    """Vote delegation between assembly attendees."""

    _name = "assembly.delegation"
    _inherit = ["assembly.mixin.open.assembly"]
    _description = "Vote delegation"
    _order = "assembly_id, partner_id"

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
    )
    delegate_partner_id = fields.Many2one(
        "res.partner",
        string="Delegate",
        required=True,
        ondelete="cascade",
        index=True,
    )
    vote_type_ids = fields.Many2many(
        "vote.type",
        "assembly_delegation_vote_type_rel",
        "delegation_id",
        "vote_type_id",
        string="Vote types",
        domain="[('active', '=', True)]",
        help="Leave empty to delegate all vote types for this assembly.",
    )
    date_delegation = fields.Datetime(default=fields.Datetime.now)
    delegation_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("revoked", "Revoked"),
        ],
        string="State",
        default="draft",
        required=True,
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
        "delegation_state",
    )
    def _check_delegation_constraints(self):
        for rec in self:
            rec._delegation_validate_before_write({})

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
        """Partner-layer rules only: ``delegation_state == confirmed`` and delegate is a confirmed attendee.

        Vote-type expansion (empty M2M ⇒ all assembly types) is defined by
        :meth:`_get_effective_vote_types` / :meth:`delegation_covers_vote_type` at
        use sites; this step does not filter by type overlap.

        **Not applied here:** inbound/outbound chain exclusion; those run inside
        :meth:`_get_effective_delegations` for a member edge when requested.
        """
        if not delegations:
            return delegations
        delegations = delegations.filtered(lambda d: d.delegation_state == "confirmed")
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
    def _search_all_confirmed_delegations_for_assembly(self, assembly_id):
        """All confirmed rows for an assembly (no partner or delegate filter)."""
        if not assembly_id:
            return self.browse()
        return self.search(
            [
                ("assembly_id", "=", assembly_id),
                ("delegation_state", "=", "confirmed"),
            ]
        )

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
        inbound = self._search_confirmed_delegations_for_member_edge(
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
        outbound = self._search_confirmed_delegations_for_member_edge(
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
    def _search_confirmed_delegations_for_member_edge(
        self, role, assembly_id, partner_id, pool=None
    ):
        """Confirmed delegations where ``partner_id`` acts as ``role`` on the edge."""
        if pool is not None:
            scoped = pool.filtered(lambda d, a=assembly_id: d.assembly_id.id == a)
            if role == "delegator":
                return scoped.filtered(lambda d, x=partner_id: d.partner_id.id == x)
            return scoped.filtered(
                lambda d, x=partner_id: d.delegate_partner_id.id == x
            )
        domain = [
            ("assembly_id", "=", assembly_id),
            ("delegation_state", "=", "confirmed"),
        ]
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

        1. ``delegations=<recordset>`` — apply only the partner layer (confirmed row +
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

        **Always enforced on the member-edge path:** ``delegation_state == confirmed``,
        delegate is a confirmed attendee when partner layer is applied, and
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

        delegations = self._search_confirmed_delegations_for_member_edge(
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

    def _validate_confirmed_delegate_attendee(
        self, assembly_id, delegate_partner_id, message
    ):
        if not assembly_id or not delegate_partner_id:
            return
        if not self.env["assembly.assembly"].browse(assembly_id).exists():
            return
        Attendee = self.env["assembly.attendee"].sudo()
        if not Attendee._search_for_assembly_partner(
            assembly_id,
            delegate_partner_id,
            limit=1,
            attendee_state="confirmed",
        ):
            raise ValidationError(message)

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
            confirmed = self._search_all_confirmed_delegations_for_assembly(assembly_id)
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
        """Block overlapping confirmed delegations that would chain received votes.

        A partner cannot delegate vote types they receive via another confirmed
        delegation, nor receive a delegation while delegating the same types
        outward (no A→B→C on overlapping ``vote.type`` coverage).
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
            "votes (confirmed delegation to them) on at least one of the same vote "
            "types. Only your own votes can be delegated, not votes received from "
            "someone else."
        )
        err_outbound = self.env._(
            "Chained delegations are not allowed: this delegate already delegates "
            "outward on overlapping vote types. Revoke or narrow that delegation "
            "before they can receive these votes."
        )
        inbound_to_delegator = self._search_confirmed_delegations_for_member_edge(
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
        outbound_from_delegate = self._search_confirmed_delegations_for_member_edge(
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

        Overlap for duplicate-confirmed validation is non-empty intersection.
        Either side may come from :meth:`_get_effective_vote_types` or from
        :meth:`_delegation_effective_vote_types` at create time.
        """
        if not effective_a or not effective_b:
            return self.env["vote.type"].browse()
        return effective_a & effective_b

    def _delegation_validate_no_duplicate_confirmed(
        self,
        assembly_id,
        partner_id,
        delegation_state,
        exclude_delegation_id,
        effective_vote_type_rs,
        confirmed_siblings=None,
    ):
        """Reject two **confirmed** outbound delegations for the same partner with overlapping types.

        Compared rows: **only** ``delegation_state == 'confirmed'`` for this
        ``(assembly_id, partner_id)`` (draft/revoked are not in the sibling set).

        Each row's coverage is its **expanded** effective types
        (:meth:`_get_effective_vote_types`): empty M2M ⇒ all assembly types;
        non-empty M2M ⇒ only selected types. Disjoint partial delegations are
        allowed (empty intersection).
        """
        if delegation_state != "confirmed" or not assembly_id or not partner_id:
            return
        err = self.env._(
            "A confirmed delegation already exists in this "
            "assembly that covers the same vote type(s). "
            "Please revoke or edit the existing delegation first."
        )
        if confirmed_siblings is not None:
            siblings = confirmed_siblings
        else:
            siblings = self.search(
                [
                    ("assembly_id", "=", assembly_id),
                    ("partner_id", "=", partner_id),
                    ("delegation_state", "=", "confirmed"),
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

    def _delegation_validate_before_write(self, vals):
        self.ensure_one()
        vals = dict(vals or {})
        if not vals:
            self.env["assembly.delegation"]._delegation_validate_record_state(self)
            return
        if "delegation_state" not in vals:
            return
        new_state = vals["delegation_state"]
        if new_state not in _DELEGATION_STATE_KEYS:
            raise UserError(
                self.env._(
                    "Invalid delegation status: %(state)s",
                    state=repr(new_state),
                )
            )
        self._validate_delegation_state_transition(self.delegation_state, new_state)
        if new_state != "confirmed":
            return
        msg_draft = self.env._(
            "Cannot confirm a delegation when the delegate "
            "is not a confirmed attendee in the assembly. "
            "The delegate must confirm attendance first."
        )
        msg_reconfirm = self.env._(
            "Cannot re-confirm a delegation when the delegate "
            "is not a confirmed attendee. "
            "The delegate must confirm attendance first."
        )
        old_state = self.delegation_state
        if old_state == new_state:
            return
        if not self.delegate_partner_id or not self.assembly_id:
            return
        if old_state == "revoked":
            self._validate_confirmed_delegate_attendee(
                self.assembly_id.id,
                self.delegate_partner_id.id,
                msg_reconfirm,
            )
        elif old_state == "draft":
            self._validate_confirmed_delegate_attendee(
                self.assembly_id.id,
                self.delegate_partner_id.id,
                msg_draft,
            )

    @api.model
    def _delegation_validate_create_vals(self, vals):
        initial = vals.get("delegation_state", "draft")
        if initial not in _DELEGATION_STATE_KEYS:
            raise ValidationError(
                self.env._(
                    "Invalid delegation status for new record: %(state)s",
                    state=initial,
                )
            )
        if initial not in ("draft", "confirmed"):
            raise ValidationError(
                self.env._(
                    "New delegations must be created in draft or confirmed status. "
                    "Got: %(state)s",
                    state=initial,
                )
            )
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
        confirmed_all = None
        confirmed_siblings = None
        if initial == "confirmed":
            self._validate_confirmed_delegate_attendee(
                assembly_id,
                delegate_partner_id,
                self.env._(
                    "Cannot create a confirmed delegation "
                    "when the delegate is not a confirmed attendee. "
                    "The delegate must confirm attendance first."
                ),
            )
            confirmed_all = self._search_all_confirmed_delegations_for_assembly(
                assembly_id
            )
            confirmed_siblings = confirmed_all.filtered(
                lambda r: r.partner_id.id == partner_id
            )
        self._delegation_validate_no_duplicate_confirmed(
            assembly_id,
            partner_id,
            initial,
            False,
            effective_types,
            confirmed_siblings=confirmed_siblings,
        )
        if initial == "confirmed":
            self._delegation_validate_no_vote_delegation_chain(
                assembly_id,
                partner_id,
                delegate_partner_id,
                effective_types,
                exclude_delegation_id=None,
            )

    def _delegation_validate_record_state(self, record):
        assembly = record.assembly_id
        assembly_id = assembly.id if assembly else False
        partner_id = record.partner_id.id if record.partner_id else False
        delegate_partner_id = (
            record.delegate_partner_id.id if record.delegate_partner_id else False
        )
        vote_type_rs = record.vote_type_ids
        effective_types = record._get_effective_vote_types()
        state = record.delegation_state
        delegate_partner = record.delegate_partner_id
        self._delegation_validate_not_self_delegation(partner_id, delegate_partner_id)
        self._delegation_validate_endpoints_are_attendees(
            assembly_id, partner_id, delegate_partner_id
        )
        self._delegation_validate_delegate_convocable(assembly, delegate_partner)
        self._delegation_validate_vote_types_in_assembly(vote_type_rs, assembly)
        if state == "confirmed" and assembly_id and delegate_partner_id:
            self._validate_confirmed_delegate_attendee(
                assembly_id,
                delegate_partner_id,
                self.env._(
                    "Cannot confirm a delegation when the delegate "
                    "is not a confirmed attendee in the assembly. "
                    "The delegate must confirm attendance first."
                ),
            )
        self._delegation_validate_no_duplicate_confirmed(
            assembly_id,
            partner_id,
            state,
            record.id,
            effective_types,
        )
        if state == "confirmed" and assembly_id and partner_id and delegate_partner_id:
            self._delegation_validate_no_vote_delegation_chain(
                assembly_id,
                partner_id,
                delegate_partner_id,
                effective_types,
                exclude_delegation_id=record.id,
            )
        if state == "confirmed" and assembly_id and partner_id and delegate_partner_id:
            record._delegation_assert_no_delegation_cycles(
                assembly_id=assembly_id,
                delegator_partner_id=partner_id,
                delegate_partner_id=delegate_partner_id,
                effective_vote_type_rs=effective_types,
                assembly=assembly,
                exclude_delegation_id=record.id,
            )

    def _raise_disallowed_delegation_state_transition(self, old_state, new_state):
        if new_state == "confirmed":
            raise UserError(
                self.env._("Only draft or revoked delegations can be confirmed.")
            )
        if new_state == "revoked":
            raise UserError(
                self.env._("Only draft or confirmed delegations can be revoked.")
            )
        raise UserError(
            self.env._(
                "Invalid delegation status transition: %(old)s → %(new)s",
                old=old_state,
                new=new_state,
            )
        )

    def _validate_delegation_state_transition(self, old_state, new_state):
        if old_state == new_state:
            return
        if (
            old_state not in _DELEGATION_STATE_KEYS
            or new_state not in _DELEGATION_STATE_KEYS
        ):
            raise UserError(
                self.env._(
                    "Invalid delegation status transition: %(old)s → %(new)s",
                    old=old_state,
                    new=new_state,
                )
            )
        allowed_next = _DELEGATION_ALLOWED_STATE_TRANSITIONS.get(old_state, frozenset())
        if new_state not in allowed_next:
            self._raise_disallowed_delegation_state_transition(old_state, new_state)

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
        prev_state_by_id=None,
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
            state_changed = prev_state_by_id is not None
            vote_types_changed = "vote_type_ids" in vals
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
                if state_changed:
                    new_state = vals.get("delegation_state", rec.delegation_state)
                    old_state = prev_state_by_id[rec.id]
                    need = new_state != old_state and new_state in (
                        "confirmed",
                        "revoked",
                    )
                elif vote_types_changed:
                    need = True
                else:
                    need = False
                if need:
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
        prev_state_by_id=None,
        post_create=False,
        prev_endpoint_partners_by_id=None,
    ):
        attendees = self._delegation_collect_vote_recompute_attendees(
            vals,
            prev_state_by_id,
            post_create=post_create,
            prev_endpoint_partners_by_id=prev_endpoint_partners_by_id,
        )
        self.env["assembly.attendee"].recompute_votes(attendees)

    def _transition_delegation_state_via_write(self, new_state, extra_vals=None):
        self.ensure_one()
        vals = dict(extra_vals or ())
        vals["delegation_state"] = new_state
        return self.write(vals)

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
        prev_state_by_id = (
            {d.id: d.delegation_state for d in self}
            if "delegation_state" in vals
            else None
        )
        prev_endpoint_partners_by_id = None
        if self and ("partner_id" in vals or "delegate_partner_id" in vals):
            prev_endpoint_partners_by_id = {
                d.id: (d.partner_id.id, d.delegate_partner_id.id) for d in self
            }
        for rec in self:
            rec._delegation_validate_before_write(vals)
        res = super().write(vals)
        self._recompute_votes_after_delegation_persist(
            vals,
            prev_state_by_id,
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
