/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";

/**
 * Vote-specific Blockly blocks and Jinja code generator.
 * relationFieldOptions: [[label, fieldName], ...] for partner relation fields.
 * sumFieldOptions: [[label, fieldName], ...] for numeric attribute to sum.
 */
export function defineVoteBlocks(
    Blockly,
    relationFieldOptions = null,
    sumFieldOptions = null
) {
    if (!Blockly || !Blockly.Blocks) {
        console.warn("Blockly or Blockly.Blocks not available");
        return;
    }
    const relationOptions =
        Array.isArray(relationFieldOptions) && relationFieldOptions.length
            ? relationFieldOptions.map((o) => [String(o[0]), String(o[1])])
            : [[_t("(campo lista)"), "ter_parcel_ids"]];

    const attrOptions =
        Array.isArray(sumFieldOptions) && sumFieldOptions.length
            ? sumFieldOptions.map((o) => [String(o[0]), String(o[1])])
            : [[_t("(campo numérico)"), "surface"]];

    Blockly.Blocks["vote_fixed"] = {
        init() {
            this.jsonInit({
                message0: "%1",
                args0: [
                    { type: "field_number", name: "VALUE", value: 1, min: 0 },
                ],
                output: "Number",
                colour: 120,
                tooltip: _t("Número fijo de votos"),
            });
        },
    };

    Blockly.Blocks["vote_count"] = {
        init() {
            this.jsonInit({
                message0: _t("Contar registros en lista %1"),
                args0: [
                    {
                        type: "field_dropdown",
                        name: "RELATION",
                        options: relationOptions,
                    },
                ],
                output: "Number",
                colour: 230,
                tooltip: _t("Número de registros (p. ej. parcelas)"),
            });
        },
    };

    Blockly.Blocks["vote_sum"] = {
        init() {
            this.jsonInit({
                message0: _t("Sumar campo %1 de la lista %2 ÷ %3"),
                args0: [
                    {
                        type: "field_dropdown",
                        name: "ATTR",
                        options: attrOptions,
                    },
                    {
                        type: "field_dropdown",
                        name: "RELATION",
                        options: relationOptions,
                    },
                    {
                        type: "field_number",
                        name: "DIVISOR",
                        value: 10,
                        min: 0.001,
                    },
                ],
                output: "Number",
                colour: 160,
                tooltip: _t(
                    "Sumar un campo numérico y dividir (p. ej. superficie ÷ 10)"
                ),
            });
        },
    };

    if (!Blockly.Blocks["math_number"]) {
        Blockly.Blocks["math_number"] = {
            init() {
                this.jsonInit({
                    message0: "%1",
                    args0: [
                        { type: "field_number", name: "NUM", value: 0 },
                    ],
                    output: "Number",
                    colour: 230,
                });
            },
        };
    }
    if (!Blockly.Blocks["math_arithmetic"]) {
        Blockly.Blocks["math_arithmetic"] = {
            init() {
                this.jsonInit({
                    message0: "%1 %2 %3",
                    args0: [
                        { type: "input_value", name: "A", check: "Number" },
                        {
                            type: "field_dropdown",
                            name: "OP",
                            options: [
                                ["+", "ADD"],
                                ["−", "MINUS"],
                                ["×", "MULTIPLY"],
                                ["÷", "DIVIDE"],
                            ],
                        },
                        { type: "input_value", name: "B", check: "Number" },
                    ],
                    output: "Number",
                    colour: 230,
                });
            },
        };
    }

    Blockly.JavaScript["vote_fixed"] = function (block) {
        const value = block.getFieldValue("VALUE");
        return [value, Blockly.JavaScript.ORDER_ATOMIC];
    };

    Blockly.JavaScript["vote_count"] = function (block) {
        const rel = block.getFieldValue("RELATION") || "id";
        const code = `partner.${rel} | length`;
        return [code, Blockly.JavaScript.ORDER_ATOMIC];
    };

    Blockly.JavaScript["vote_sum"] = function (block) {
        const attr = block.getFieldValue("ATTR") || "surface";
        const rel = block.getFieldValue("RELATION") || "ter_parcel_ids";
        const div = block.getFieldValue("DIVISOR") || 10;
        const code = `(partner.${rel} | map(attribute='${attr}') | sum) / ${div}`;
        return [code, Blockly.JavaScript.ORDER_ATOMIC];
    };
}

function createJinjaGenerator(Blockly) {
    const g = new Blockly.Generator("Jinja");
    if (!g.forBlock) g.forBlock = {};
    g.PRECEDENCE = 0;
    g.forBlock["vote_fixed"] = function (block) {
        const v = block.getFieldValue("VALUE");
        return [String(v), g.PRECEDENCE];
    };
    g.forBlock["vote_count"] = function (block) {
        const rel = (block.getFieldValue("RELATION") || "id").replace(
            /[^a-zA-Z0-9_]/g,
            ""
        );
        return [rel ? `partner.${rel} | length` : "0", g.PRECEDENCE];
    };
    g.forBlock["vote_sum"] = function (block) {
        const attr = (block.getFieldValue("ATTR") || "surface").replace(
            /[^a-zA-Z0-9_]/g,
            ""
        );
        const rel = (block.getFieldValue("RELATION") || "ter_parcel_ids").replace(
            /[^a-zA-Z0-9_]/g,
            ""
        );
        const div = parseFloat(block.getFieldValue("DIVISOR")) || 10;
        if (!rel || !attr) return ["0", g.PRECEDENCE];
        return [
            `(partner.${rel} | map(attribute='${attr}') | sum) / ${div}`,
            g.PRECEDENCE,
        ];
    };
    g.forBlock["math_number"] = function (block) {
        const v = block.getFieldValue("NUM");
        return [String(v), g.PRECEDENCE];
    };
    g.forBlock["math_arithmetic"] = function (block, generator) {
        const op = block.getFieldValue("OP");
        const order = op === "MULTIPLY" || op === "DIVIDE" ? 1 : 0;
        const A = generator.valueToCode(block, "A", order) || "0";
        const B = generator.valueToCode(block, "B", order) || "0";
        const opMap = {
            ADD: "+",
            MINUS: "-",
            MULTIPLY: "*",
            DIVIDE: "/",
        };
        const sym = opMap[op] || "+";
        return [`(${A}) ${sym} (${B})`, order];
    };
    return g;
}

let _jinjaGenerator = null;

export function getOrCreateJinjaGenerator(Blockly) {
    if (_jinjaGenerator) return _jinjaGenerator;
    _jinjaGenerator = createJinjaGenerator(Blockly);
    if (
        typeof Blockly.registry !== "undefined" &&
        Blockly.registry.register
    ) {
        const Type = Blockly.registry.Type || {};
        const typeName = Type.CODE_GENERATOR || "codeGenerator";
        try {
            Blockly.registry.register(
                typeName,
                "Jinja",
                _jinjaGenerator,
                true
            );
        } catch (e) {
            console.warn("Blockly: could not register Jinja generator", e);
        }
    }
    if (
        Blockly.Generator &&
        typeof Blockly.Generator.generators_ !== "undefined"
    ) {
        Blockly.Generator.generators_["Jinja"] = _jinjaGenerator;
    }
    return _jinjaGenerator;
}

export function blocklyWorkspaceToJinja(workspace, Blockly) {
    const gen = getOrCreateJinjaGenerator(Blockly);
    const code = gen.workspaceToCode(workspace);
    const s = (code || "").trim();
    if (!s) return "";
    return s.startsWith("{{") ? s : `{{ ${s} }}`;
}
