/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class AttendanceIcon extends Component {
    setup() {
        this.orm = useService("orm");
        this.user = useService("user");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            isPresent: false,
            employeeId: null,
            attendanceTime: "",
            lastCheckIn: null,
        });

        this.timer = null;

        onMounted(() => {
            this.loadAttendanceData();
            this.env.bus.addEventListener('hr_attendance_update', this.loadAttendanceData.bind(this));
        });

        onWillUnmount(() => {
            if (this.timer) {
                clearInterval(this.timer);
            }
            this.env.bus.removeEventListener('hr_attendance_update', this.loadAttendanceData.bind(this));
        });
    }

    async loadAttendanceData() {
        try {
            const [employee] = await this.orm.searchRead("hr.employee", [
                ["user_id", "=", this.user.userId],
            ], ["id", "attendance_state", "last_attendance_id"], { limit: 1 });

            if (employee) {
                const wasPresent = this.state.isPresent;
                this.state.employeeId = employee.id;
                this.state.isPresent = employee.attendance_state === "checked_in";

                if (this.state.isPresent) {
                    this.updateAttendanceTime();
                    if (this.timer) clearInterval(this.timer);
                    this.timer = setInterval(() => this.updateAttendanceTime(), 60000); // Actualiza cada minuto
                } else {
                    if (this.timer) {
                        clearInterval(this.timer);
                        this.timer = null;
                    }
                    this.state.attendanceTime = "";
                }

                if (wasPresent !== this.state.isPresent) {
                    const message = this.state.isPresent ?
                        "Has registrado correctamente tu entrada" :
                        "Has registrado correctamente tu salida";
                    this.notification.add(message, {
                        type: "success",
                    });
                }
            }
        } catch (error) {
            console.error("Error loading attendance data", error);
        }
    }

    async updateAttendanceTime() {
        try {
            // Call the backend method to calculate attendance time
            const result = await this.orm.call(
                "hr.employee",
                "get_current_attendance_time",
                []
            );
            if (result) {
                this.state.attendanceTime = result.display;
            }
        } catch (error) {
            console.error("Error updating attendance time", error);
        }
    }

    navigateToAttendances() {
        this.action.doAction('hr_attendance.hr_attendance_action_my_attendances');
    }
}

AttendanceIcon.template = "worker_activity_self_monitoring.AttendanceIcon";

export const attendanceIconItem = {
    Component: AttendanceIcon,
    isDisplayed: () => true,
};

registry.category("systray").add("worker_activity_self_monitoring.AttendanceIcon", attendanceIconItem);