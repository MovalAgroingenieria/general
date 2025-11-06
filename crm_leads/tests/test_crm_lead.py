# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# pylint: disable=protected-access
from odoo.exceptions import UserError
from odoo.tests import TransactionCase
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestCrmLeadExtension(TransactionCase):
    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()

        cls.CrmLead = cls.env["crm.lead"]
        cls.CrmStage = cls.env["crm.stage"]
        cls.CrmTeam = cls.env["crm.team"]
        cls.CrmTag = cls.env["crm.tag"]
        cls.UtmSource = cls.env["utm.source"]
        cls.ResUsers = cls.env["res.users"]
        cls.ResPartner = cls.env["res.partner"]

        # Minimal user and partner to own records
        cls.partner = cls.ResPartner.create({"name": "Test Partner"})
        cls.user = cls.ResUsers.create(
            {
                "name": "Tester",
                "login": "tester_crm_lead",
                "email": "tester@example.com",
            }
        )

        # Stages (one "new", one "normal")
        cls.stage_new = cls.CrmStage.create(
            {"name": "New (Is New)", "sequence": 1, "is_new": True}
        )
        cls.stage_progress = cls.CrmStage.create(
            {"name": "In Progress", "sequence": 2, "is_new": False}
        )

        # CRM team with our user as leader
        cls.team = cls.CrmTeam.create(
            {
                "name": "Default Team",
                "user_id": cls.user.id,  # leader/manager
            }
        )

        # Extra team where user is only member
        cls.team_member = cls.CrmTeam.create({"name": "Member Team"})
        cls.team_member.member_ids = [(4, cls.user.id)]

        # Tag and UTM Source for validation
        cls.tag = cls.CrmTag.create({"name": "Priority"})
        cls.source = cls.UtmSource.create({"name": "Web"})

    def _new_lead(self, **vals):
        data = {
            "name": "Test Lead",
            "partner_id": self.partner.id,
            "stage_id": self.stage_new.id,
            "user_id": self.user.id,
            # team_id intentionally omitted to let compute assign it
            "type": "lead",
        }
        data.update(vals)
        return self.CrmLead.create(data)

    # ---------- _compute_team_id behavior ----------
    def test_compute_team_assigns_default_team_without_type_restriction(self):
        lead = self._new_lead(team_id=False, type="opportunity")
        lead._compute_team_id()

        # A team must be assigned
        self.assertTrue(lead.team_id, "A team should be assigned to the lead")

        # And it must be a team where the user is leader or member
        self.assertTrue(
            lead.user_id == lead.team_id.user_id
            or lead.user_id in lead.team_id.member_ids,
            "Assigned team must be one the user leads or belongs to",
        )

    def test_compute_team_keeps_existing_team_if_user_is_leader(self):
        lead = self._new_lead(team_id=self.team.id)
        # Even if we trigger compute, team must remain
        lead._compute_team_id()
        self.assertEqual(
            lead.team_id, self.team, "Team should not change if user is team leader"
        )

    def test_compute_team_keeps_existing_team_if_user_is_member(self):
        lead = self._new_lead(team_id=self.team_member.id)
        lead._compute_team_id()
        self.assertEqual(
            lead.team_id,
            self.team_member,
            "Team should not change if user is a member of the current team",
        )

    def test_compute_team_with_no_user_does_nothing(self):
        lead = self._new_lead(user_id=False, team_id=False)
        lead._compute_team_id()
        self.assertFalse(
            lead.team_id, "Without user assigned, compute should not assign a team"
        )

    # ---------- write() validation on stage change ----------

    def test_write_raises_if_stage_changes_without_tag_and_source(self):
        lead = self._new_lead(tag_ids=[], source_id=False)
        with self.assertRaises(UserError):
            lead.write({"stage_id": self.stage_progress.id})

    def test_write_allows_stage_change_with_tag_and_source(self):
        lead = self._new_lead()
        lead.tag_ids = [(4, self.tag.id)]
        lead.source_id = self.source.id
        # Should not raise
        lead.write({"stage_id": self.stage_progress.id})
        self.assertEqual(
            lead.stage_id,
            self.stage_progress,
            "Stage change should succeed when Category and Origin are set",
        )
