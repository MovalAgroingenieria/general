# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestProjectTaskRunningFields(TransactionCase):
    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.user = cls.env.ref("base.user_admin")
        cls.project = cls.env["project.project"].create({"name": "Project Test"})

    def test_task_running_requires_starter_and_time(self):
        task = self.env["project.task"].create(
            {
                "name": "Task Test",
                "project_id": self.project.id,
            }
        )
        with self.assertRaises(ValidationError):
            task.write({"task_running": True})

    def test_task_running_valid(self):
        now = fields.Datetime.now()
        task = self.env["project.task"].create(
            {
                "name": "Task Running",
                "project_id": self.project.id,
                "task_running": True,
                "starter_user_id": self.user.id,
                "start_time": now - timedelta(minutes=5),
            }
        )
        self.assertTrue(task.task_running)
        self.assertEqual(task.starter_user_id, self.user)
        self.assertTrue(task.start_time)

    def test_task_not_running_must_not_have_related_fields(self):
        now = fields.Datetime.now()
        task = self.env["project.task"].create(
            {
                "name": "Task Inconsistent",
                "project_id": self.project.id,
            }
        )
        with self.assertRaises(ValidationError):
            task.write(
                {
                    "task_running": False,
                    "starter_user_id": self.user.id,
                    "start_time": now,
                }
            )

    def test_onchange_clears_fields(self):
        now = fields.Datetime.now()
        task = self.env["project.task"].new(
            {
                "name": "Task Onchange",
                "project_id": self.project.id,
                "task_running": True,
                "starter_user_id": self.user.id,
                "start_time": now,
            }
        )
        task.task_running = False
        task._onchange_task_running()  # pylint: disable=protected-access
        self.assertFalse(task.starter_user_id)
        self.assertFalse(task.start_time)
