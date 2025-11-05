# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Partner Address Street Number",
    "summary": "Add a 'street number' field to partner addresses and integrate it in views/formatting.",
    "version": "18.0.1.0.0",
    "category": "Moval General Addons",
    "website": "https://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "depends": [
        "base",
    ],
    "data": [
        "views/res_partner_views.xml",
    ],
}
