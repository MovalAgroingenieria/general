# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Partner Address Street Number",
    "summary": "This module add street number to partner address",
    "version": "16.0.1.0.0",
    "category": "Moval General Addons",
    "website": "http://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "depends": [
    ],
    "data": [
        "views/res_partner_views.xml",
    ],
}
