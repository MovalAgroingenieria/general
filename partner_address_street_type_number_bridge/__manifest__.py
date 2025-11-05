# __manifest__.py
{
    "name": "Street Type Street Number Bridge",
    "version": "18.0.1.0.0",
    "category": "Partner Management",
    "website": "https://www.moval.es",
    "author": "Moval Agroingeniería",
    "maintainers": ["moval"],
    "license": "AGPL-3",
    "depends": ["partner_address_street_type", "partner_address_street_number"],
    "data": [
        "views/res_partner_views.xml",
    ],
}
