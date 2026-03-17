# Copyright 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Web Blockly",
    "summary": "Blockly library integration for Odoo (generic workspace component)",
    "version": "18.0.1.0.0",
    "category": "Hidden/Technical",
    "website": "https://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": ["base", "web"],
    "assets": {
        "web.assets_web": [
            "web_blockly/static/src/blockly_loader.js",
            "web_blockly/static/src/blockly_workspace/blockly_workspace.js",
            "web_blockly/static/src/blockly_workspace/blockly_workspace.xml",
            "web_blockly/static/src/blockly_workspace/blockly_workspace.scss",
        ],
    },
}
