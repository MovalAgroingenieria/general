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
        // Limpiar historial de navegación y ir al panel de tareas
        window.history.replaceState({}, '', '/web');

        this.action.doAction('project.action_view_task', {
            clearBreadcrumbs: true,
            stackPosition: 'replaceCurrentAction'
        }).then(() => {
            // Si hay una tarea activa, navegar a ella después
            if (this.state.taskRunning && this.state.taskId && this.state.projectId) {
                setTimeout(() => {
                    this.action.doAction({
                        type: 'ir.actions.act_window',
                        res_model: 'project.task',
                        res_id: this.state.taskId,
                        views: [[false, 'form']],
                        target: 'current',
                        context: {
                            'default_project_id': this.state.projectId,
                            'search_default_project_id': this.state.projectId
                        },
                        clearBreadcrumbs: false
                    });
                }, 100);
            }
        });
    }
}

TaskIcon.template = "worker_activity_self_monitoring.TaskIcon";

export const taskIconItem = {
    Component: TaskIcon,
    isDisplayed: () => true,
};

registry.category("systray").add("worker_activity_self_monitoring.TaskIcon", taskIconItem);