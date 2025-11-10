# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Customer Purchase Follow-up",
    "summary": "Track customers without recent purchases and send " "notifications",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "website": "https://www.moval.es",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        "base",
        "sale",
        "crm",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_template_data.xml",
        "data/cron_data.xml",
        "views/res_partner_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "customer_purchase_follow_up/static/src/js/notification_handler.js",
        ],
    },
}
