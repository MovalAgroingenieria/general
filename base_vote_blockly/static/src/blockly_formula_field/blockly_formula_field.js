/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { BlocklyWorkspace } from "@web_blockly/static/src/blockly_workspace/blockly_workspace";
import { loadBlockly, BLOCKLY_MEDIA } from "@web_blockly/static/src/blockly_loader";
import {
    defineVoteBlocks,
    getOrCreateJinjaGenerator,
    blocklyWorkspaceToJinja,
} from "../blockly_vote_blocks";

import { Component, useRef, useEffect, onWillUnmount, useState } from "@odoo/owl";

export class BlocklyFormulaField extends Component {
    static template = "base_vote_blockly.BlocklyFormulaField";
    static components = { BlocklyWorkspace };
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.blocklyReady = useState({ value: false });
        this.toolbox = useState({ value: null });
        this.getCode = null;
        this.changeTimeout = null;
        useEffect(() => {
            this.initBlockly();
        });
    }

    get canSaveFormula() {
        return !!this.props.record;
    }

    get canTestFormula() {
        const record = this.props.record;
        return !!record && record.resId && !record.isNew;
    }

    get displayFormula() {
        const formula = this.props.record?.data?.formula;
        if (formula && formula.trim()) return formula.trim();
        return _t("(Arrastra bloques para generar la fórmula)");
    }

    async initBlockly() {
        try {
            const Blockly = await loadBlockly();
            let relationOptions = [
                [_t("(campo lista)"), "parcel_ids"],
                [_t("Parcelas"), "parcel_ids"],
                [_t("Contactos relacionados"), "child_ids"],
            ];
            let sumFieldOptions = [
                [_t("(campo numérico)"), "surface"],
                [_t("Superficie"), "surface"],
                [_t("Cantidad"), "quantity"],
            ];
            try {
                const relFields = await this.orm.searchRead(
                    "ir.model.fields",
                    [
                        ["model", "=", "res.partner"],
                        ["ttype", "in", ["one2many", "many2many"]],
                    ],
                    ["name", "string", "relation"],
                    { order: "string" }
                );
                if (relFields.length) {
                    relationOptions = relFields.map((f) => [
                        f.string ? `${f.string} (${f.name})` : f.name,
                        f.name,
                    ]);
                    const seen = new Set();
                    const sumOptions = [];
                    for (const rf of relFields) {
                        if (!rf.relation || seen.has(rf.relation)) continue;
                        seen.add(rf.relation);
                        const numFields = await this.orm.searchRead(
                            "ir.model.fields",
                            [
                                ["model", "=", rf.relation],
                                ["ttype", "in", ["integer", "float"]],
                            ],
                            ["name", "string"],
                            { order: "string" }
                        );
                        for (const nf of numFields) {
                            if (seen.has(`attr_${nf.name}`)) continue;
                            seen.add(`attr_${nf.name}`);
                            sumOptions.push([
                                nf.string
                                    ? `${nf.string} (${nf.name})`
                                    : nf.name,
                                nf.name,
                            ]);
                        }
                    }
                    if (sumOptions.length) sumFieldOptions = sumOptions;
                }
            } catch (e) {
                console.warn(
                    "Blockly: could not load res.partner relation fields",
                    e
                );
            }
            defineVoteBlocks(Blockly, relationOptions, sumFieldOptions);
            getOrCreateJinjaGenerator(Blockly);
            this.getCode = (workspace, BlocklyLib) =>
                blocklyWorkspaceToJinja(workspace, BlocklyLib);
            this.toolbox.value = {
                kind: "categoryToolbox",
                contents: [
                    {
                        kind: "category",
                        name: "Fórmula",
                        contents: [
                            { kind: "block", type: "vote_fixed" },
                            { kind: "block", type: "vote_count" },
                            { kind: "block", type: "vote_sum" },
                            { kind: "sep" },
                            { kind: "block", type: "math_number" },
                            { kind: "block", type: "math_arithmetic" },
                        ],
                    },
                ],
            };
            this.blocklyReady.value = true;
        } catch (e) {
            console.error("Blockly init error", e);
        }
    }

    onValueChange(xml, code) {
        if (!this.props.record) return;
        this.props.record.update({
            formula_blockly_xml: xml,
            formula: code || "",
        });
    }

    async onSaveFormula() {
        if (!this.canSaveFormula) return;
        try {
            const saved = await this.props.record.save();
            if (saved) {
                this.notification.add(
                    _t("Fórmula guardada correctamente."),
                    { type: "success" }
                );
            }
        } catch (e) {
            this.notification.add(
                e?.message || _t("Error al guardar la fórmula."),
                { type: "danger" }
            );
        }
    }

    async onTestFormula() {
        if (!this.canTestFormula) return;
        const formula = this.props.record.data.formula || "";
        try {
            const { TestFormulaDialog } = await import(
                "../formula_editor_field/formula_editor_field"
            );
            this.dialog.add(TestFormulaDialog, {
                formula,
                voteTypeId: this.props.record.resId,
                close: () => {},
            });
        } catch (e) {
            this.notification.add(
                _t("No se pudo abrir el diálogo de prueba."),
                { type: "warning" }
            );
        }
    }

    onWillUnmount() {
        if (this.changeTimeout) clearTimeout(this.changeTimeout);
    }
}

export const blocklyFormulaField = {
    component: BlocklyFormulaField,
    displayName: _t("Blockly (blocks)"),
    supportedTypes: ["text"],
    extractProps: () => ({}),
};

registry.category("fields").add("blockly_formula", blocklyFormulaField);
