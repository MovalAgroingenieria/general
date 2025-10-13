/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

export class TeleworkDateWithDayField extends Component {
    static template = "hr_telework_tracking_site_capacity.TeleworkDateWithDayField";
    static props = {
        ...standardFieldProps,
    };

    get dateValue() {
        if (!this.props.value) return '';
        const date = new Date(this.props.value);
        return date.toISOString().split('T')[0];
    }

    get weekdayDisplay() {
        if (!this.props.value) return '';
        const date = new Date(this.props.value);
        const weekdays = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
        return weekdays[date.getDay()];
    }

    onDateChange(ev) {
        this.props.update(ev.target.value);
    }
}

registry.category("fields").add("telework_date_with_day", TeleworkDateWithDayField);
