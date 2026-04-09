# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""AF v2.0 agenda vote modes and core agenda actions/constraints (start_voting, skip)."""

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase
from odoo.tools import mute_logger
from odoo.tools.float_utils import float_is_zero

from .common import AssemblyTestMixin


class TestAssemblyAgendaVoteModes(AssemblyTestMixin, TransactionCase):
    def test_no_vote_without_vote_type(self):
        assembly = self._create_assembly(name="No vote asm")
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Info only",
                "agenda_vote_mode": "no_vote",
                "sequence": 10,
            }
        )
        self.assertEqual(agenda.agenda_vote_mode, "no_vote")
        self.assertFalse(agenda.vote_type_id)
        self.assertFalse(agenda.requires_vote)

    def test_no_vote_rejects_manual_counters(self):
        assembly = self._create_assembly(name="No vote counters asm")
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "N",
                "agenda_vote_mode": "no_vote",
                "sequence": 10,
            }
        )
        with self.assertRaises(ValidationError):
            agenda.write({"manual_yes": 1})

    def test_no_vote_action_start_voting_raises(self):
        assembly, agenda = self._create_assembly_with_agenda(
            name="No vote start asm", requires_vote=False
        )
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        with self.assertRaises(ValidationError):
            agenda.action_start_voting()

    def test_no_vote_action_finalize_manual_raises(self):
        assembly = self._create_assembly(name="No vote finalize asm")
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "N",
                "agenda_vote_mode": "no_vote",
                "sequence": 10,
            }
        )
        with self.assertRaises(UserError):
            agenda.action_finalize_manual()

    def test_weighted_roll_call_still_works(self):
        """Weighted mode unchanged; manual yes/no possible-universe checks do not apply."""
        assembly, agenda = self._create_assembly_with_agenda()
        self.assertEqual(agenda.agenda_vote_mode, "weighted")
        voting = self._open_voting_on_agenda(assembly, agenda)
        self.assertTrue(voting.exists())
        self.assertEqual(voting.agenda_id, agenda)

    def test_weighted_roll_call_uses_agenda_vote_type_on_voting(self):
        """AF regression: weighted line keeps ``vote_type_id`` on opened ``assembly.voting``."""
        assembly, agenda = self._create_assembly_with_agenda()
        self.assertEqual(agenda.agenda_vote_mode, "weighted")
        self.assertTrue(agenda.vote_type_id)
        voting = self._open_voting_on_agenda(assembly, agenda)
        self.assertEqual(voting.vote_type_id, agenda.vote_type_id)
        self.assertEqual(voting.assembly_id, assembly)

    def test_weighted_skips_manual_universe_validation_with_confirmed_attendees(self):
        """Weighted lines ignore manual-universe rules; manual-only fields must stay empty."""
        assembly, agenda = self._create_assembly_with_agenda()
        vt = assembly.vote_type_ids[0]
        assembly.action_generate_attendees()
        self._confirm_attendees(assembly.attendee_ids, vote_type=vt, votes_each=1)
        self.assertGreater(
            assembly._get_manual_yes_no_possible_vote_units(),
            0,
            "Universe > 0 is the condition that would constrain manual_yes_no totals",
        )
        self.assertEqual(agenda.agenda_vote_mode, "weighted")
        with self.assertRaises(ValidationError):
            agenda.write({"manual_total_expected": 999.0})
        voting = self._open_voting_on_agenda(assembly, agenda)
        self.assertTrue(voting.exists())
        self.assertEqual(voting.vote_type_id, agenda.vote_type_id)

    def test_no_vote_rejects_manual_total_expected(self):
        assembly = self._create_assembly(name="No vote manual total asm")
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Info",
                "agenda_vote_mode": "no_vote",
                "requires_vote": False,
                "sequence": 10,
            }
        )
        with self.assertRaises(ValidationError):
            agenda.write({"manual_total_expected": 1.0})

    def test_switch_to_weighted_clears_manual_total_expected(self):
        """Mode sync drops manual-only expected total when leaving manual yes/no."""
        assembly = self._create_assembly(name="Mode switch asm")
        vt = assembly.vote_type_ids[0]
        assembly.action_generate_attendees()
        self._confirm_attendees(assembly.attendee_ids, vote_type=vt, votes_each=1)
        n = len(assembly.attendee_ids)
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Point",
                "agenda_vote_mode": "manual_yes_no",
                "manual_yes": n,
                "manual_no": 0,
                "manual_abstain": 0,
                "manual_count_blank": 0,
                "manual_total_expected": float(n),
                "sequence": 10,
            }
        )
        self.assertFalse(
            float_is_zero(agenda.manual_total_expected, precision_digits=6)
        )
        agenda.write(
            {
                "agenda_vote_mode": "weighted",
                "requires_vote": True,
                "vote_type_id": vt.id,
            }
        )
        self.assertEqual(agenda.agenda_vote_mode, "weighted")
        self.assertEqual(agenda.manual_total_expected, 0.0)

    def test_manual_yes_no_validates_expected_total(self):
        assembly = self._create_assembly(name="Manual YN assembly")
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Manual YN",
                "agenda_vote_mode": "manual_yes_no",
                "manual_total_expected": 10.0,
                "manual_yes": 3,
                "manual_no": 3,
                "manual_abstain": 2,
                "manual_count_blank": 2,
                "sequence": 10,
            }
        )
        with self.assertRaises(ValidationError):
            agenda.write({"manual_yes": 1})

    def test_manual_yes_no_finalize(self):
        assembly = self._create_assembly(name="Manual finalize asm")
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Point",
                "agenda_vote_mode": "manual_yes_no",
                "manual_yes": 0,
                "manual_no": 0,
                "manual_abstain": 0,
                "manual_count_blank": 0,
                "sequence": 10,
            }
        )
        agenda.action_finalize_manual()
        self.assertEqual(agenda.agenda_state, "voted")

    def test_manual_yes_no_passes_when_counts_match_attendee_vote_units(self):
        assembly = self._create_assembly(name="Manual match possible asm")
        vt = assembly.vote_type_ids[0]
        assembly.action_generate_attendees()
        self._confirm_attendees(assembly.attendee_ids, vote_type=vt, votes_each=1)
        n = len(assembly.attendee_ids)
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "YN match",
                "agenda_vote_mode": "manual_yes_no",
                "sequence": 10,
                "manual_yes": n - 1,
                "manual_no": 1,
                "manual_abstain": 0,
                "manual_count_blank": 0,
            }
        )
        agenda.action_finalize_manual()
        self.assertEqual(agenda.agenda_state, "voted")

    def test_manual_yes_no_blocked_when_counts_mismatch_attendee_vote_units(self):
        assembly = self._create_assembly(name="Manual mismatch asm")
        vt = assembly.vote_type_ids[0]
        assembly.action_generate_attendees()
        self._confirm_attendees(assembly.attendee_ids, vote_type=vt, votes_each=1)
        with self.assertRaises(ValidationError):
            self.env["assembly.agenda"].create(
                {
                    "assembly_id": assembly.id,
                    "name": "YN bad",
                    "agenda_vote_mode": "manual_yes_no",
                    "sequence": 10,
                    "manual_yes": 1,
                    "manual_no": 0,
                    "manual_abstain": 0,
                    "manual_count_blank": 0,
                }
            )

    def test_manual_yes_no_rejects_nonzero_when_no_vote_units_possible(self):
        assembly = self._create_assembly(name="Manual zero universe asm")
        assembly.action_generate_attendees()
        with self.assertRaises(ValidationError):
            self.env["assembly.agenda"].create(
                {
                    "assembly_id": assembly.id,
                    "name": "YN no electorate",
                    "agenda_vote_mode": "manual_yes_no",
                    "sequence": 10,
                    "manual_yes": 1,
                    "manual_no": 0,
                    "manual_abstain": 0,
                    "manual_count_blank": 0,
                }
            )

    def test_manual_yes_no_expected_total_must_match_possible_units(self):
        assembly = self._create_assembly(name="Manual expected vs possible asm")
        vt = assembly.vote_type_ids[0]
        assembly.action_generate_attendees()
        self._confirm_attendees(assembly.attendee_ids, vote_type=vt, votes_each=1)
        n = len(assembly.attendee_ids)
        with self.assertRaises(ValidationError):
            self.env["assembly.agenda"].create(
                {
                    "assembly_id": assembly.id,
                    "name": "YN wrong expected",
                    "agenda_vote_mode": "manual_yes_no",
                    "sequence": 10,
                    "manual_total_expected": float(n + 5),
                    "manual_yes": n + 5,
                    "manual_no": 0,
                    "manual_abstain": 0,
                    "manual_count_blank": 0,
                }
            )

    def test_options_forbidden_outside_manual_multi(self):
        assembly, agenda = self._create_assembly_with_agenda()
        with self.assertRaises(ValidationError):
            self.env["assembly.agenda.option"].create(
                {
                    "agenda_id": agenda.id,
                    "name": "Opt",
                    "sequence": 10,
                }
            )

    def test_agenda_option_rejects_duplicate_sequence_same_agenda(self):
        assembly = self._create_assembly(name="Opt seq uniq asm")
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Multi seq",
                "agenda_vote_mode": "manual_multi",
                "sequence": 10,
                "option_ids": [(0, 0, {"name": "First", "sequence": 10})],
            }
        )
        Option = self.env["assembly.agenda.option"]
        # Enforced by SQL unique(agenda_id, sequence); insert fails before Python constrains.
        with mute_logger("odoo.sql_db"):
            with self.assertRaises(Exception):
                Option.create(
                    {
                        "agenda_id": agenda.id,
                        "name": "Second same seq",
                        "sequence": 10,
                    }
                )

    def test_agenda_option_create_and_link(self):
        """Minimal option rows: create via O2M and ensure inverse link on agenda."""
        assembly = self._create_assembly(name="Option link asm")
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Point with options",
                "agenda_vote_mode": "manual_multi",
                "sequence": 10,
                "option_ids": [
                    (0, 0, {"name": "Alpha", "sequence": 10}),
                    (0, 0, {"name": "Beta", "sequence": 20}),
                ],
            }
        )
        self.assertEqual(len(agenda.option_ids), 2)
        self.assertEqual(
            set(agenda.option_ids.mapped("name")),
            {"Alpha", "Beta"},
        )
        for opt in agenda.option_ids:
            self.assertEqual(opt.agenda_id, agenda)

    def test_manual_multi_create_without_options_blocked(self):
        assembly = self._create_assembly(name="Multi no opt asm")
        with self.assertRaises(ValidationError):
            self.env["assembly.agenda"].create(
                {
                    "assembly_id": assembly.id,
                    "name": "Bad multi",
                    "agenda_vote_mode": "manual_multi",
                    "sequence": 10,
                }
            )

    def test_manual_multi_create_with_options_allowed(self):
        assembly = self._create_assembly(name="Multi ok asm")
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Good multi",
                "agenda_vote_mode": "manual_multi",
                "sequence": 10,
                "option_ids": [(0, 0, {"name": "Only", "sequence": 10})],
            }
        )
        self.assertTrue(agenda.option_ids)
        self.assertFalse(agenda.vote_type_id)
        self.assertFalse(agenda.requires_vote)
        with self.assertRaises(ValidationError):
            agenda.write({"option_ids": [(5, 0, 0)]})

    def test_manual_multi_switch_from_weighted_without_options_blocked(self):
        assembly, agenda = self._create_assembly_with_agenda()
        self.assertEqual(agenda.agenda_vote_mode, "weighted")
        with self.assertRaises(ValidationError):
            agenda.write({"agenda_vote_mode": "manual_multi"})

    def test_manual_multi_cannot_start_weighted_roll_call_voting(self):
        """manual_multi is isolated from the roll-call engine (``action_start_voting``)."""
        assembly = self._create_assembly(name="Multi roll asm")
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "M",
                "agenda_vote_mode": "manual_multi",
                "sequence": 10,
                "option_ids": [(0, 0, {"name": "O", "sequence": 10})],
            }
        )
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        with self.assertRaises(ValidationError):
            agenda.action_start_voting()

    def test_manual_counters_forbidden_on_manual_multi(self):
        assembly = self._create_assembly(name="Multi yn counters asm")
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "M",
                "agenda_vote_mode": "manual_multi",
                "sequence": 10,
                "option_ids": [(0, 0, {"name": "O", "sequence": 10})],
            }
        )
        with self.assertRaises(ValidationError):
            agenda.write({"manual_yes": 1})

    def test_manual_counters_forbidden_on_weighted(self):
        assembly, agenda = self._create_assembly_with_agenda()
        with self.assertRaises(ValidationError):
            agenda.write({"manual_yes": 1})

    def test_voting_create_rejected_for_non_weighted_agenda(self):
        assembly = self._create_assembly(name="Non weighted asm")
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Manual",
                "agenda_vote_mode": "manual_yes_no",
                "sequence": 10,
            }
        )
        vt = assembly.vote_type_ids[0]
        with self.assertRaises(ValidationError):
            self.env["assembly.voting"].create(
                {
                    "agenda_id": agenda.id,
                    "vote_type_id": vt.id,
                    "name": "Illegal",
                }
            )

    def test_final_summary_store_and_update(self):
        assembly, agenda = self._create_assembly_with_agenda(
            agenda_title="Summary point"
        )
        agenda.write({"final_summary": "<p>First</p>"})
        self.assertIn("First", agenda.final_summary)
        agenda.write({"final_summary": "<p>Updated</p>"})
        self.assertIn("Updated", agenda.final_summary)
        self.assertNotIn("First", agenda.final_summary)

    def test_final_summary_retained_after_manual_yes_no_finalize(self):
        """``final_summary`` is independent of counters; survives manual close."""
        assembly = self._create_assembly(name="Summary YN asm")
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "YN + summary",
                "agenda_vote_mode": "manual_yes_no",
                "manual_yes": 0,
                "manual_no": 0,
                "manual_abstain": 0,
                "manual_count_blank": 0,
                "sequence": 10,
                "final_summary": "<p>Closing note</p>",
            }
        )
        agenda.action_finalize_manual()
        self.assertEqual(agenda.agenda_state, "voted")
        self.assertIn("Closing note", agenda.final_summary)

    def test_manual_multi_finalize_sets_voted(self):
        """``action_finalize_manual`` closes manual_multi when options exist."""
        assembly = self._create_assembly(name="Multi finalize asm")
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Multi point",
                "agenda_vote_mode": "manual_multi",
                "sequence": 10,
                "option_ids": [(0, 0, {"name": "A", "sequence": 10})],
            }
        )
        agenda.action_finalize_manual()
        self.assertEqual(agenda.agenda_state, "voted")

    def test_manual_multi_option_counts_must_match_possible_vote_units(self):
        """AF v2.0 §2.3: sum of option manual units vs confirmed attendee vote pool."""
        assembly = self._create_assembly(name="Multi possible match asm")
        vt = assembly.vote_type_ids[0]
        assembly.action_generate_attendees()
        self._confirm_attendees(assembly.attendee_ids, vote_type=vt, votes_each=1)
        n = len(assembly.attendee_ids)
        with self.assertRaises(ValidationError):
            self.env["assembly.agenda"].create(
                {
                    "assembly_id": assembly.id,
                    "name": "Bad totals",
                    "agenda_vote_mode": "manual_multi",
                    "sequence": 10,
                    "option_ids": [
                        (0, 0, {"name": "A", "sequence": 10, "manual_vote_count": 1}),
                    ],
                }
            )
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Good totals",
                "agenda_vote_mode": "manual_multi",
                "sequence": 10,
                "option_ids": [
                    (0, 0, {"name": "A", "sequence": 10, "manual_vote_count": n}),
                ],
            }
        )
        self.assertEqual(sum(agenda.option_ids.mapped("manual_vote_count")), n)
        self.assertEqual(agenda.manual_multi_votes_sum, n)

    def test_manual_multi_option_negative_vote_count_rejected(self):
        assembly = self._create_assembly(name="Multi neg asm")
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "M",
                "agenda_vote_mode": "manual_multi",
                "sequence": 10,
                "option_ids": [(0, 0, {"name": "A", "sequence": 10})],
            }
        )
        opt = agenda.option_ids[0]
        with self.assertRaises(ValidationError):
            opt.write({"manual_vote_count": -1})

    def test_cannot_switch_from_weighted_to_manual_with_existing_votings(self):
        assembly, agenda = self._create_assembly_with_agenda()
        self._open_voting_on_agenda(assembly, agenda)
        with self.assertRaises(ValidationError):
            agenda.write({"agenda_vote_mode": "manual_yes_no"})


class TestAssemblyAgenda(AssemblyTestMixin, TransactionCase):
    """Tests for assembly.agenda: start_voting, skip, constraints."""

    def test_action_start_voting_creates_voting_open_and_sets_agenda_in_progress(self):
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        self.assertEqual(agenda.agenda_state, "pending")
        agenda.action_start_voting()
        self.assertEqual(agenda.agenda_state, "in_progress")
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        self.assertTrue(voting)
        self.assertEqual(voting.voting_state, "open")
        self.assertTrue(voting.date_open)

    def test_action_start_voting_without_vote_type_raises(self):
        assembly, agenda = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                agenda_title="No vote type", requires_vote=True
            )
        )
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        # ORM forbids clearing vote_type while requires_vote; use SQL for this edge case
        self.env.cr.execute(
            "UPDATE assembly_agenda SET vote_type_id = NULL WHERE id = %s",
            (agenda.id,),
        )
        agenda.invalidate_recordset(["vote_type_id"])
        with self.assertRaises(ValidationError) as ctx:
            agenda.action_start_voting()
        self.assertIn("vote type", str(ctx.exception).lower())

    def test_action_start_voting_when_not_pending_or_in_progress_raises(self):
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        voting.action_close()
        self.assertEqual(agenda.agenda_state, "voted")
        with self.assertRaises(ValidationError) as ctx:
            agenda.action_start_voting()
        self.assertIn("not open for voting", str(ctx.exception).lower())

    def test_action_start_voting_while_already_open_raises(self):
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        with self.assertRaises(ValidationError) as ctx:
            agenda.action_start_voting()
        self.assertIn("open voting", str(ctx.exception).lower())

    def test_action_skip_sets_agenda_state_skipped(self):
        _, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        self.assertEqual(agenda.agenda_state, "pending")
        agenda.action_skip()
        self.assertEqual(agenda.agenda_state, "skipped")

    def test_vote_type_must_be_in_assembly_types(self):
        _, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        other_vote_type = (
            self._create_vote_type(  # noqa: F841  # pylint: disable=protected-access
                self.env, name="Other type", code="OTHER"
            )
        )
        with self.assertRaises(ValidationError) as ctx:
            agenda.vote_type_id = other_vote_type.id
        self.assertIn("assembly's vote types", str(ctx.exception))

    def test_cannot_change_vote_type_when_votings_exist(self):
        vote_type1 = self._create_vote_type(self.env, name="VT1", code="VT1")
        # pylint: disable=protected-access
        vote_type2 = self._create_vote_type(self.env, name="VT2", code="VT2")
        # pylint: disable=protected-access
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Type two",
                "code": "TWO",
                "vote_type_ids": [(6, 0, (vote_type1 | vote_type2).ids)],
                "partner_domain": "[]",
            }
        )
        partners = self._create_partners(  # noqa: F841
            self.env, 2
        )  # pylint: disable=protected-access
        assembly, agenda = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                assembly_type=assembly_type,
                partner_domain="[('id', 'in', %s)]" % partners.ids,
            )
        )
        agenda.vote_type_id = vote_type1
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        with self.assertRaises(ValidationError) as ctx:
            agenda.write({"vote_type_id": vote_type2.id})
        self.assertIn("already has votings", str(ctx.exception))
