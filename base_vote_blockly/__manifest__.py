# Copyright 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Base Vote Blockly",
    "summary": "Blockly formula editor for vote types (depends on web_blockly and base_vote)",
    "version": "18.0.1.0.0",
    "category": "Administration",
    "website": "https://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": ["base_vote", "web_blockly"],
    "data": [
        "views/vote_type_views.xml",
    ],
    "assets": {
        "web.assets_web": [
            "base_vote_blockly/static/src/blockly_vote_blocks.js",
            "base_vote_blockly/static/src/blockly_formula_field/blockly_formula_field.js",
            "base_vote_blockly/static/src/blockly_formula_field/blockly_formula_field.xml",
            "base_vote_blockly/static/src/blockly_formula_field/blockly_formula_field.scss",
            "base_vote_blockly/static/src/formula_editor_field/formula_editor_field.js",
            "base_vote_blockly/static/src/formula_editor_field/formula_editor_field.xml",
        ],
    },
}
