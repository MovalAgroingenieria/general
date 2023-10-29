# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Moval Corporate Image",
    "summary": """Decorate instances with moval iconography""",
    "version": "16.0.1.1.0",
    "category": "Moval General Addons",
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "application": False,
    "installable": False,
    "depends": [
        "web",
        "fontawesome_ext",
    ],
    "data": [
        "views/webclient_templates.xml"
    ],
    "assets": {
        "web.assets_qweb": [
            "/moval_corporate_image/static/src/xml/menu.xml",
        ],
    },
}
