/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class TaskIcon extends Component {
    setup() {
        this.orm = useService("orm");
        this.user = useService("user");
        this.action = useService("action");
        this.state = useState({
            taskRunning: false,
            taskId: null,
            taskName: "",
            projectId: null
        });

        onMounted(() => this.loadTaskData());
    }

    async loadTaskData() {
        try {
            const currentUserId = this.user.userId;
            const tasks = await this.orm.searchRead("project.task", [
                ["starter_user_id", "=", currentUserId],
                ["task_running", "=", true]
            ], ["id", "name", "project_id"], { limit: 1 });

            if (tasks && tasks.length > 0) {
                this.state.taskRunning = true;
                this.state.taskId = tasks[0].id;
                this.state.taskName = tasks[0].name;
                this.state.projectId = tasks[0].project_id[0]; // Guardamos el ID del proyecto
            } else {
                this.state.taskRunning = false;
                this.state.taskId = null;
                this.state.taskName = "";
                this.state.projectId = null;
            }
        } catch (error) {
        }
    }

    navigateToTask() {
        if (this.state.taskRunning && this.state.taskId) {
            // When there is an active task: create breadcrumb current_view -> task_panel -> specific_task
            this.action.doAction('project.action_view_task', {
                stackPosition: 'new'  // Add to stack instead of replacing
            }).then(() => {
                // Navigate to the specific task keeping the breadcrumb
                this.action.doAction({
                    type: 'ir.actions.act_window',
                    res_model: 'project.task',
                    res_id: this.state.taskId,
                    views: [[false, 'form']],
                    target: 'current',
                    stackPosition: 'new'  // Add to stack to preserve navigation
                });
            });
        } else {
            // When no active task: go to task panel keeping previous view
            this.action.doAction('project.action_view_task', {
                stackPosition: 'new'  // Add to stack to keep previous view
            });
        }
    }
}

TaskIcon.template = "worker_activity_self_monitoring.TaskIcon";

export const taskIconItem = {
    Component: TaskIcon,
    isDisplayed: () => true,
};

registry.category("systray").add("worker_activity_self_monitoring.TaskIcon", taskIconItem);