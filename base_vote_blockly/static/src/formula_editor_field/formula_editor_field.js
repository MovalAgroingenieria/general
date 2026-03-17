/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useAutoresize } from "@web/core/utils/autoresize";
import { useInputField } from "@web/views/fields/input_field_hook";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

import { Component, useState, useRef, onWillStart } from "@odoo/owl";

export class TestFormulaDialog extends Component {
    static template = "base_vote_blockly.TestFormulaDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        formula: String,
        voteTypeId: Number,
    };

    setup() {
        this.title = _t("Probar fórmula");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            partnerId: null,
            partners: [],
            result: null,
            loading: false,
        });
        onWillStart(async () => {
            const partners = await this.orm.searchRead(
                "res.partner",
                [],
                ["id", "name", "display_name"],
                { limit: 100 }
            );
            this.state.partners = partners;
            if (partners.length) {
                this.state.partnerId = partners[0].id;
            }
        });
    }

    get canTest() {
        return (
            this.state.partnerId != null &&
            this.props.formula &&
            this.props.formula.trim()
        );
    }

    onPartnerChange(ev) {
        const val = ev.target.value;
        this.state.partnerId = val ? parseInt(val, 10) : null;
    }

    async onTest() {
        if (!this.canTest || this.state.loading) return;
        this.state.loading = true;
        this.state.result = null;
        try {
            const res = await this.orm.call(
                "vote.type",
                "test_formula",
                [this.props.voteTypeId],
                { formula: this.props.formula, partner_id: this.state.partnerId }
            );
            if (res.error) {
                this.state.result = { error: res.error };
                this.notification.add(res.error, { type: "danger" });
            } else {
                this.state.result = res;
                this.notification.add(_t("Result: %s", res.value), {
                    type: "success",
                });
            }
        } catch (e) {
            this.state.result = { error: e.message || String(e) };
            this.notification.add(e.message || String(e), { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    onClose() {
        this.props.close();
    }
}

export class FormulaEditorField extends Component {
    static template = "base_vote_blockly.FormulaEditorField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };

    setup() {
        this.textareaRef = useRef("textarea");
        this.dialog = useService("dialog");
        useInputField({
            getValue: () => this.props.record.data[this.props.name] || "",
            refName: "textarea",
            preventLineBreaks: false,
        });
        useAutoresize(this.textareaRef, { minimumHeight: 120 });
    }

    get canTest() {
        const record = this.props.record;
        return (
            record.resId &&
            typeof record.resId === "number" &&
            !record.isNew
        );
    }

    onTestFormula() {
        if (!this.canTest) return;
        const formula = this.textareaRef.el
            ? this.textareaRef.el.value
            : this.props.record.data[this.props.name] || "";
        this.dialog.add(TestFormulaDialog, {
            formula,
            voteTypeId: this.props.record.resId,
            close: () => {},
        });
    }
}

export const formulaEditorField = {
    component: FormulaEditorField,
    displayName: _t("Formula (Jinja2)"),
    supportedTypes: ["text"],
    extractProps: ({ attrs }) => ({
        placeholder: attrs.placeholder,
    }),
};

registry.category("fields").add("formula_editor", formulaEditorField);
