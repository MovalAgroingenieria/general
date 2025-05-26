# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    "name": "Bundle user experience modules",
    "summary": "Install at once all common modules related to the user "
               "experience",
    "version": "16.0.1.0.0",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "category": "Hidden",
    "application": False,
    "installable": True,
    "depends": [
        "base_technical_user",
        "disable_odoo_online"
        # "edit_save_button"
        "moval_corporate_image"
        "web_advanced_search"
        "web_chatter_position"
        "web_listview_range_select"
        "web_no_bubble"
        "web_responsive"
        "web_sheet_full_width"
        "web_tree_dynamic_colored_field"
    ],
    "data": [
    ],
}
