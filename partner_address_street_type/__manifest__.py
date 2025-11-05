# __manifest__.py
{
    "name": "Partner Address Street Type",
    "summary": "Add street type to partner address",
    "version": "18.0.1.1.0",
    "category": "Partner Management",
    "website": "https://www.moval.es",
    "author": "Moval Agroingeniería",
    "maintainers": ["moval"],
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "depends": [
        "contacts", "base_setup"
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/res_street_type_views.xml",
        "views/res_street_type_menus.xml",
        "views/res_config_settings_view.xml",
        "views/res_partner_views.xml",
    ],
}
