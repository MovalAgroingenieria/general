/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

export class TeleworkModeField extends Component {
    static template = "hr_telework_tracking_site_capacity.TeleworkModeField";
    static props = {
        ...standardFieldProps,
    };

    get modeIcon() {
        if (this.props.value === 'remote') {
            return 'fa-home';
        } else if (this.props.value === 'onsite') {
            return 'fa-building';
        }
        return '';
    }

    get modeLabel() {
        if (this.props.value === 'remote') {
            return 'Teletrabajo';
        } else if (this.props.value === 'onsite') {
            return 'Presencial';
        }
        return '';
    }

    get modeColor() {
        if (this.props.value === 'remote') {
            return '#28a745'; // Verde
        } else if (this.props.value === 'onsite') {
            return '#007bff'; // Azul
        }
        return '#6c757d';
    }

    onModeChange(ev) {
        this.props.update(ev.target.value);
    }
}

registry.category("fields").add("telework_mode", TeleworkModeField);
