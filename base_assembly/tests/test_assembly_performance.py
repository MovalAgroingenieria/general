# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Performance regression tests for base_assembly (500+ attendees).

Run with: pytest -t performance ...
Or exclude from fast runs: odoo-bin -i base_assembly --test-tags /base_assembly --exclude-tag performance

Set BASE_ASSEMBLY_PERF_N=500 for full load; default 100 for CI.
"""

import os
import time

from odoo.tests import TransactionCase, tagged

from .common import AssemblyTestMixin


def _perf_n():
    n = int(os.environ.get("BASE_ASSEMBLY_PERF_N", "100"))
    return min(max(n, 10), 1000)


@tagged("performance")
class TestAssemblyPerformance(AssemblyTestMixin, TransactionCase):
    """Measure critical operations with large N to catch regressions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.perf_n = _perf_n()

    def test_performance_generate_attendees(self):
        """action_generate_attendees with N partners must stay under threshold."""
        partners = self._create_partners(self.env, count=self.perf_n, prefix="Perf")
        partner_domain = "[('id', 'in', %s)]" % partners.ids
        assembly, _ = self._create_assembly_with_agenda(
            name="Perf assembly",
            partner_domain=partner_domain,
        )
        t0 = time.perf_counter()
        assembly.action_generate_attendees()
        elapsed = time.perf_counter() - t0
        self.assertEqual(len(assembly.attendee_ids), self.perf_n)
        # Plan: ≤30s for 500; scale roughly linearly for CI (100)
        threshold = 60.0 if self.perf_n >= 400 else 30.0
        self.assertLess(
            elapsed,
            threshold,
            f"action_generate_attendees({self.perf_n}) took {elapsed:.1f}s > {threshold}s",
        )

    def test_performance_count_present_attendees(self):
        """count_present_attendees with N attendees (and some delegations) under threshold."""
        partners = self._create_partners(self.env, count=self.perf_n, prefix="Perf")
        partner_domain = "[('id', 'in', %s)]" % partners.ids
        assembly, _ = self._create_assembly_with_agenda(
            name="Perf assembly",
            partner_domain=partner_domain,
        )
        assembly.action_generate_attendees()
        # Confirm half to have present count = N/2
        for att in assembly.attendee_ids[: self.perf_n // 2]:
            att.action_confirm()
        assembly.invalidate_recordset()
        t0 = time.perf_counter()
        present = assembly.count_present_attendees()
        elapsed = time.perf_counter() - t0
        self.assertEqual(present, self.perf_n // 2)
        # Plan: ≤2s for 500
        threshold = 5.0 if self.perf_n >= 400 else 2.0
        self.assertLess(
            elapsed,
            threshold,
            f"count_present_attendees({self.perf_n}) took {elapsed:.1f}s > {threshold}s",
        )

    def test_performance_recompute_votes(self):
        """recompute_votes on N confirmed attendees (with partner.vote) under threshold."""
        partners = self._create_partners(self.env, count=self.perf_n, prefix="Perf")
        partner_domain = "[('id', 'in', %s)]" % partners.ids
        assembly, _ = self._create_assembly_with_agenda(
            name="Perf assembly",
            partner_domain=partner_domain,
        )
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        for att in assembly.attendee_ids:
            self._give_partner_votes(att.partner_id, vote_type, 1)
            att.action_confirm()
        t0 = time.perf_counter()
        assembly.attendee_ids.recompute_votes()
        elapsed = time.perf_counter() - t0
        # Plan: ≤90s for 500 (current implementation is O(N*types))
        threshold = 120.0 if self.perf_n >= 400 else 45.0
        self.assertLess(
            elapsed,
            threshold,
            f"recompute_votes({self.perf_n}) took {elapsed:.1f}s > {threshold}s",
        )

    def test_performance_voting_close(self):
        """action_close with many vote_line_ids under threshold."""
        n = min(self.perf_n, 400)  # cap lines for test duration
        partners = self._create_partners(self.env, count=n, prefix="Perf")
        partner_domain = "[('id', 'in', %s)]" % partners.ids
        assembly, agenda = self._create_assembly_with_agenda(
            name="Perf assembly",
            partner_domain=partner_domain,
        )
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        for att in assembly.attendee_ids:
            self._give_partner_votes(att.partner_id, vote_type, 1)
            att.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        # Create vote lines in batches
        batch_size = 50
        attendees = assembly.attendee_ids
        for i in range(0, len(attendees), batch_size):
            batch = attendees[i : i + batch_size]
            self.env["assembly.voting.line"].create(
                [
                    {
                        "voting_id": voting.id,
                        "attendee_id": att.id,
                        "vote_option": "yes",
                        "votes_applied": 1.0,
                    }
                    for att in batch
                ]
            )
        self.assertEqual(len(voting.vote_line_ids), n)
        t0 = time.perf_counter()
        voting.action_close()
        elapsed = time.perf_counter() - t0
        # Plan: ≤15s for ~400 lines
        threshold = 25.0 if n >= 300 else 15.0
        self.assertLess(
            elapsed,
            threshold,
            f"action_close({n} lines) took {elapsed:.1f}s > {threshold}s",
        )

    def test_performance_assembly_read_form_fields(self):
        """Read of assembly form fields (trigger computes) with N attendees under threshold."""
        partners = self._create_partners(self.env, count=self.perf_n, prefix="Perf")
        partner_domain = "[('id', 'in', %s)]" % partners.ids
        assembly, _ = self._create_assembly_with_agenda(
            name="Perf assembly",
            partner_domain=partner_domain,
        )
        assembly.action_generate_attendees()
        # Typical form read: main fields + one2many counts / computed
        fields_to_read = [
            "name",
            "assembly_state",
            "quorum_type",
            "quorum_value",
            "total_present_attendees",
            "quorum_reached",
            "total_possible_attendees",
        ]
        assembly.invalidate_recordset()
        t0 = time.perf_counter()
        assembly.read(fields_to_read)
        elapsed = time.perf_counter() - t0
        threshold = 5.0 if self.perf_n >= 400 else 3.0
        self.assertLess(
            elapsed,
            threshold,
            f"assembly.read({self.perf_n} attendees) took {elapsed:.1f}s > {threshold}s",
        )
