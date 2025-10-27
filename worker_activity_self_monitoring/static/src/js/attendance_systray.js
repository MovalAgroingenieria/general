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
                    if (employee.last_attendance_id) {
                        const [attendance] = await this.orm.searchRead("hr.attendance", [
                            ["id", "=", employee.last_attendance_id[0]],
                        ], ["check_in"], { limit: 1 });
                        //It's possible that the time fail when the hours change from summer time to winter time.
                        //Change twoHorsDate in winter: 1 * 60 * 60 * 1000; in summer: 2 * 60 * 60 * 1000;
                        if (attendance) {
                            // Determine if we're in summer time (DST) or winter time
                            const checkDate = new Date(attendance.check_in);
                            const january = new Date(checkDate.getFullYear(), 0, 1);
                            const july = new Date(checkDate.getFullYear(), 6, 1);
                            const isDST = checkDate.getTimezoneOffset() < Math.max(january.getTimezoneOffset(), july.getTimezoneOffset());
                            const twoHorsDate = 1 * 60 * 60 * 1000;
                            const checkinHours = new Date(attendance.check_in).getTime();
                            const correctDate = checkinHours + twoHorsDate
                            this.state.lastCheckIn = new Date(correctDate);
                            this.updateAttendanceTime();
                            if (this.timer) clearInterval(this.timer);
                            this.timer = setInterval(() => this.updateAttendanceTime(), 60000); // Actualiza cada minuto
                        }
                    }
                } else {
                    if (this.timer) {
                        clearInterval(this.timer);
                        this.timer = null;
                    }
                    this.state.attendanceTime = "";
                    this.state.lastCheckIn = null;
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

    updateAttendanceTime() {
        if (!this.state.lastCheckIn) return;

        const now = new Date();
        const diff = now - this.state.lastCheckIn;

        const hours = Math.floor(diff / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

        this.state.attendanceTime = `${hours}h ${minutes}m`;
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