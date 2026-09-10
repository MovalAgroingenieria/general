/* @odoo-module */

import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { ActivityMenu } from "@hr_attendance/components/attendance_menu/attendance_menu";

patch(ActivityMenu.prototype, {
    setup() {
        super.setup();
        this.state.isDisplayed = false;
    },
    searchReadEmployee() {
        return Promise.resolve();
    },
    signInOut() {
        return null;
    },
});

export class AttendanceBigButton extends Component {
    static template = "hr_attendance_big_button.attendance_button";

    setup() {
        this.action = useService("action");
        this.state = useState({
            checkedIn: false,
            elapsed: "",
            lastCheckInMs: null,
        });
        this._onAttendanceRegisterClick = this._onAttendanceRegisterClick.bind(this);
        onMounted(() => {
            document.addEventListener("click", this._onAttendanceRegisterClick, true);
            this._safeRefreshState();
            this._stateSyncTimer = setInterval(() => this._safeRefreshState(), 60000);
        });
        onWillUnmount(() => {
            document.removeEventListener(
                "click",
                this._onAttendanceRegisterClick,
                true
            );
            clearTimeout(this._elapsedTickStarter);
            clearInterval(this._elapsedTimer);
            clearInterval(this._stateSyncTimer);
        });
    }

    async refreshState() {
        const result = await rpc("/hr_attendance/attendance_user_data");
        this.state.checkedIn = !!result && result.attendance_state === "checked_in";
        this.state.lastCheckInMs = this.state.checkedIn
            ? this._getLastCheckInMillis(result?.last_check_in)
            : null;
        this._syncElapsedTimer();
        this._tickElapsed();
    }

    async _safeRefreshState() {
        try {
            await this.refreshState();
        } catch {
            // Keep last known state to avoid unmounting the systray widget
            // when RPC fails temporarily.
        }
    }

    _getLastCheckInMillis(timestamp) {
        if (!timestamp) {
            return null;
        }
        const parsedDate = deserializeDateTime(timestamp);
        if (parsedDate?.isValid) {
            return parsedDate.toMillis();
        }
        const fallbackDate = new Date(timestamp).getTime();
        return Number.isFinite(fallbackDate) ? fallbackDate : null;
    }

    _tickElapsed() {
        if (!this.state.checkedIn || !this.state.lastCheckInMs) {
            this.state.elapsed = "";
            return;
        }
        this.state.elapsed = this._formatElapsed(this.state.lastCheckInMs);
    }

    _syncElapsedTimer() {
        clearTimeout(this._elapsedTickStarter);
        clearInterval(this._elapsedTimer);
        if (!this.state.checkedIn || !this.state.lastCheckInMs) {
            return;
        }
        const waitToNextMinute = 60000 - (Date.now() % 60000);
        this._elapsedTickStarter = setTimeout(() => {
            this._tickElapsed();
            this._elapsedTimer = setInterval(() => this._tickElapsed(), 60000);
        }, waitToNextMinute);
    }

    _formatElapsed(lastCheckInMs) {
        const diffMs = Math.max(0, Date.now() - lastCheckInMs);
        const hours = Math.floor(diffMs / (1000 * 60 * 60));
        const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
        return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
    }

    _onAttendanceRegisterClick(event) {
        const registerButton = event.target.closest?.(
            ".o_hr_attendance_big_button"
        );
        if (!registerButton || registerButton.disabled) {
            return;
        }
        // Refresh after backend write to keep systray state in sync.
        setTimeout(() => this._safeRefreshState(), 700);
        setTimeout(() => this._safeRefreshState(), 1800);
    }

    openAttendance() {
        this.action.doAction("hr_attendance_big_button.action_hr_attendance_big_button_open");
    }
}

registry.category("systray").add(
    "hr_attendance_big_button.attendance_button",
    {
        Component: AttendanceBigButton,
        isDisplayed: () => true,
    },
    { sequence: 101 }
);
