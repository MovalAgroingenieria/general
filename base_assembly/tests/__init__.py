# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
# isort: skip_file
#
<<<<<<< HEAD
# Canonical regression suite (base module): fewer modules; each import loads at install.
#
# Removed or merged in this pass:
#   - test_functional_spec_compliance_pack → quorum/delegation/vote/http coverage elsewhere
#   - test_vote_recomputation_regression → test_vote_recomputation_consistency
#   - test_recomputation_multiple_changes → test_vote_recomputation_consistency
#   - test_state_machine_assembly → test_assembly_state_transitions_spec
#   - test_state_machine_attendee → test_attendee_state_transitions_spec
#   - test_state_machine_delegation → test_assembly_delegation
#   - test_assembly_security_regression → test_assembly_security_acl
#   - test_vote_edge_cases_production → test_vote_consistency_production
#   - test_assembly_agenda → test_assembly_agenda_vote_modes
#
# Earlier removals (see git history):
#   - test_functional_spec_coverage_matrix, test_phase_delegations_quorum,
#     test_assembly_performance, test_report_af_v2_sections, test_assembly_attendee_vat_confirm
#
# AF v2 regression map:
#   VAT: test_assembly_af_v2_contracts
#   manual_multi / modes: test_assembly_agenda_vote_modes (+ core agenda actions)
#   rendering: test_assembly_html_rendering
#   representation: test_assembly_representation (+ contracts)
#   attendance links: test_assembly_attendance_link_tracker + test_http_attendance
#
from . import (
    test_module_packaging_sanity,
    # Core models
    test_assembly_agenda_constraints,
    test_assembly_agenda_refactored,
    test_assembly_agenda_list_view_arch,
    test_assembly_agenda_vote_modes,
    test_assembly_assembly,
    test_assembly_af_v2_infrastructure,
    test_assembly_af_v2_contracts,
=======
# Regression suite (base module): prefer fewer modules; each import loads at install.
#
# Removed as redundant (cases kept elsewhere):
#   - test_functional_spec_coverage_matrix → merged into test_votes
#   - test_phase_delegations_quorum → quorum/D overlap quorum_people + assembly_quorum_*;
#     delegation security → test_assembly_security_acl; vote_type ∉ assembly → overlap_spec
#   - test_assembly_performance → optional perf, not contract regression
#
# Coverage map (target areas):
#   Quorum: test_quorum_people_functional_spec, test_assembly_quorum_delegation_voting (rules+V+R),
#           test_functional_spec_compliance_pack (QA slice)
#   Non-attendee delegator / partial-full / no-chain: test_vote_recompute_non_attendee_delegator,
#           test_delegation_vote_effect_filtering_spec, test_delegation_no_chain,
#           compliance_pack, test_votes
#   Vote recompute: test_vote_recomputation_consistency, test_vote_recomputation_regression,
#           test_recomputation_multiple_changes, vote_consistency / edge production
#   Uniqueness attendee.vote: test_attendee_vote_persistence_uniqueness, consistency tests
#   State: test_state_machine_*, test_*_state_transitions_spec
#   HTTP/controllers: test_http_*, test_portal_assembly, test_online_voting_antifraud

from . import (
    test_module_packaging_sanity,
    # Core models
    test_assembly_agenda,
    test_assembly_agenda_constraints,
    test_assembly_agenda_refactored,
    test_assembly_assembly,
>>>>>>> origin/18.0
    test_assembly_attendee,
    test_assembly_attendee_vote,
    test_attendee_vote_persistence_uniqueness,
    test_attendee_write_explicit_paths,
    test_assembly_delegation,
<<<<<<< HEAD
    test_assembly_representation,
    test_assembly_html_rendering,
    test_assembly_voting,
    # State machines + spec transitions (assembly graph merged into spec module)
    test_assembly_state_transitions_spec,
    test_assembly_closed_immutability,
    test_attendee_state_transitions_spec,
=======
    test_assembly_voting,
    # State machines + spec transitions
    test_state_machine_assembly,
    test_assembly_state_transitions_spec,
    test_assembly_closed_immutability,
    test_state_machine_attendee,
    test_attendee_state_transitions_spec,
    test_state_machine_delegation,
>>>>>>> origin/18.0
    # Inheritance / create paths
    test_assembly_create_inheritance,
    test_assembly_type_inheritance_consistency,
    test_assembly_create_without_onchange,
<<<<<<< HEAD
    # Delegation effectiveness & validation (delegation SM merged into delegation module)
    test_delegation_no_chain,
    test_delegation_overlap_validation_spec,
    test_delegation_vote_effect_filtering_spec,
    # Vote recompute & persistence (regression + multi-change merged)
    test_vote_recomputation_consistency,
    test_vote_recompute_non_attendee_delegator,
    test_votes,
=======
    # Delegation effectiveness & validation
    test_delegation_no_chain,
    test_delegation_overlap_validation_spec,
    test_delegation_vote_effect_filtering_spec,
    # Vote recompute & persistence
    test_vote_recomputation_consistency,
    test_vote_recomputation_regression,
    test_vote_recompute_non_attendee_delegator,
    test_votes,
    test_recomputation_multiple_changes,
>>>>>>> origin/18.0
    # Agenda / vote-type edge cases
    test_agenda_validation_edge_cases,
    test_multiple_vote_types_edge_cases,
    test_invariants_validation,
    test_vote_consistency_production,
<<<<<<< HEAD
    # Confirm flows
    test_assembly_attendee_confirm_improved,
    test_assembly_attendee_confirm_warning,
    # Integration: quorum + delegation + voting + AF v1.5 compat + E2E
    test_assembly_quorum_delegation_voting,
    test_quorum_people_functional_spec,
    test_af_v15_core_compat,
    test_assembly_e2e_full_flow,
    # Security (short regression matrix merged into ACL module)
    test_assembly_security_acl,
    # HTTP / portal
    test_assembly_attendance_link_tracker,
=======
    test_vote_edge_cases_production,
    # Confirm flows
    test_assembly_attendee_confirm_improved,
    test_assembly_attendee_confirm_warning,
    # Integration: quorum + delegation + voting + results + E2E + cross-QA pack
    test_assembly_quorum_delegation_voting,
    test_quorum_people_functional_spec,
    test_functional_spec_compliance_pack,
    test_assembly_e2e_full_flow,
    # Security
    test_assembly_security_acl,
    test_assembly_security_regression,
    # HTTP / portal
>>>>>>> origin/18.0
    test_http_attendance,
    test_http_portal,
    test_portal_assembly,
    test_http_public_display,
    test_http_vote,
    test_online_voting_antifraud,
)
