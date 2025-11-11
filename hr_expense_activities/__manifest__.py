# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Activities Expenses",
    "summary": "Optionally disable activity creation for new expenses",
    "version": "18.0.1.0.0",
    "author": "Moval Agroingeniería",
    "website": "https://www.moval.es",
    "maintainers": ["moval-agro"],
    "support": "soporte@moval.es",
    "license": "AGPL-3",
    "category": "Human Resources/Expenses",
    "depends": ["hr_expense"],
    "post_init_hook": "post_init_hook",
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "images": ["static/description/banner.png"],
}
