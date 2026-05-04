# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "URL Model Display",
    "version": "18.0.1.0.0",
    "category": "Hidden",
    "summary": "Show model name in URL as query parameter for better readability",
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            (
                "replace",
                "web/static/src/webclient/actions/action_service.js",
                "web_url_model/static/src/webclient/actions/action_service.js",
            ),
        ],
    },
    "license": "LGPL-3",
}
