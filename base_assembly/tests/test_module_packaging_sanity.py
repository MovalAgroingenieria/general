# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Packaging sanity: manifest data paths, installed module, core XML records, controllers import."""

import ast
from pathlib import Path

from odoo.tests import TransactionCase

from .common import AssemblyTestMixin

_MODULE_ROOT = Path(__file__).resolve().parents[1]
_MODULE_TECHNICAL_NAME = _MODULE_ROOT.name


def _load_manifest_dict():
    """Parse ``__manifest__.py`` dict literal (supports leading comments)."""
    raw = (_MODULE_ROOT / "__manifest__.py").read_text(encoding="utf-8")
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start < 0 or end <= start:
        raise ValueError("Invalid __manifest__.py: no dict literal found")
    return ast.literal_eval(raw[start:end])


class TestBaseAssemblyPackagingSanity(AssemblyTestMixin, TransactionCase):
    """Guards clean install references and minimal runtime wiring (no full XML loader)."""

    def test_manifest_data_files_exist(self):
        """Every path in ``data`` exists on disk (catches broken manifest references)."""
        manifest = _load_manifest_dict()
        for rel in manifest.get("data", []):
            path = _MODULE_ROOT / rel
            self.assertTrue(
                path.is_file(),
                "Manifest data file missing: %s" % rel,
            )

    def test_manifest_asset_files_exist(self):
        manifest = _load_manifest_dict()
        for _bundle, paths in (manifest.get("assets") or {}).items():
            for rel in paths:
                prefix = "%s/" % _MODULE_TECHNICAL_NAME
                fs_rel = rel[len(prefix) :] if rel.startswith(prefix) else rel
                path = _MODULE_ROOT / fs_rel
                self.assertTrue(
                    path.is_file(),
                    "Manifest asset file missing: %s" % rel,
                )

    def test_manifest_dependencies_named(self):
        """Declared dependencies are non-empty (base + vote + web)."""
        manifest = _load_manifest_dict()
        deps = manifest.get("depends", [])
        self.assertIsInstance(deps, (list, tuple))
        self.assertIn("base", deps)
        self.assertIn("base_vote", deps)
        self.assertIn("web", deps)

    def test_module_discoverable(self):
        """Module is registered in ``ir.module.module`` (manifest and path are valid)."""
        mod = self.env["ir.module.module"].search(
            [("name", "=", "base_assembly")], limit=1
        )
        self.assertTrue(mod, "base_assembly should be discoverable in ir.module.module")
        self.assertNotEqual(
            mod.state,
            "uninstalled",
            "base_assembly should be part of the loaded addon set for this registry",
        )

    def test_core_models_registered(self):
        """ORM models from the kernel are in ``ir.model``."""
        Model = self.env["ir.model"].sudo()
        for xmlid_name in (
            "assembly.assembly",
            "assembly.attendee",
            "assembly.delegation",
        ):
            self.assertTrue(
                Model.search([("model", "=", xmlid_name)], limit=1),
                "Model %s should be registered" % xmlid_name,
            )

    def test_security_groups_and_access_loaded(self):
        """XML security refs resolve (install would fail otherwise)."""
        self.env.ref("base_assembly.assembly_group_user")
        self.env.ref("base_assembly.assembly_group_manager")

    def test_document_preview_wizard_action_xmlid_exists(self):
        self.env.ref("base_assembly.action_assembly_document_preview_wizard")

    def test_assembly_code_sequence_loaded(self):
        """Sequence from ``data/assembly_sequence_data.xml`` is present."""
        seq = (
            self.env["ir.sequence"]
            .sudo()
            .search([("code", "=", "assembly.assembly")], limit=1)
        )
        self.assertTrue(seq, "ir.sequence assembly.assembly should exist after install")

    def test_attendance_reports_actions_exist(self):
        """At least one bound report on ``assembly.assembly`` (QWeb data loaded)."""
        reports = (
            self.env["ir.actions.report"]
            .sudo()
            .search([("model", "=", "assembly.assembly")])
        )
        self.assertTrue(
            reports,
            "Expected ir.actions.report rows bound to assembly.assembly",
        )

    def test_representation_report_action_xmlid_exists(self):
        """AF §11.5: representation template report is declared."""
        self.env.ref("base_assembly.assembly_assembly_action_report_representation")
        self.env.ref(
            "base_assembly.assembly_representation_action_report_power_of_attorney"
        )

    def test_delegation_certificate_report_action_xmlid_exists(self):
        self.env.ref(
            "base_assembly.assembly_delegation_action_report_vote_delegation_certificate"
        )

    def test_attendance_present_with_delegation_report_action_xmlid_exists(self):
        """Present-only attendance report includes delegations column (bound action)."""
        self.env.ref(
            "base_assembly.assembly_assembly_action_report_attendance_present_with_delegationvote"
        )

    def test_af_v2_call_register_and_window_actions_exist(self):
        """AF v2: call-register report alias and navigation actions load."""
        self.env.ref("base_assembly.assembly_assembly_action_report_call_register")
        act_rep = self.env.ref("base_assembly.assembly_representation_action")
        act_called = self.env.ref(
            "base_assembly.assembly_attendee_action_called_members"
        )
        act_opt = self.env.ref("base_assembly.assembly_agenda_option_action")
        self.assertEqual(act_rep.res_model, "assembly.representation")
        self.assertEqual(act_called.res_model, "assembly.attendee")
        self.assertEqual(act_opt.res_model, "assembly.agenda.option")

    def test_af_v2_form_views_chatter_and_agenda_fields(self):
        """Single check: assembly/agenda chatter + agenda vote/manual/summary fields + rep views."""
        agenda_arch = self.env.ref("base_assembly.assembly_agenda_view_form").arch_db
        for needle in (
            'name="agenda_vote_mode"',
            'name="option_ids"',
            'name="manual_yes"',
            'name="manual_no"',
            'name="manual_abstain"',
            'name="manual_count_blank"',
            'name="manual_total_expected"',
            'name="final_summary"',
            "<chatter",
        ):
            self.assertIn(needle, agenda_arch)
        self.assertIn(
            "<chatter",
            self.env.ref("base_assembly.assembly_assembly_view_form").arch_db,
        )
        self.env.ref("base_assembly.assembly_representation_view_tree")
        self.env.ref("base_assembly.assembly_representation_view_form")

    def test_minimal_core_record_creation(self):
        """End-to-end: create type + assembly + agenda path used across the suite."""
        assembly, _agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        self.assertTrue(assembly.exists())
        self.assertTrue(assembly.code)

    def test_controller_package_importable(self):
        """Controller module imports (routes register when HTTP stack loads tests)."""
        # pylint: disable=import-outside-toplevel,unused-import
        import odoo.addons.base_assembly.controllers.attendance as attendance_ctrl

        self.assertTrue(hasattr(attendance_ctrl, "AttendanceController"))
