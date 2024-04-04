odoo.define('portal.portal_ext', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.portalDetails.include({
    /**
    events: {
        ...publicWidget.registry.portalDetails.prototype.events,
        'change select[name="category_id"]': '_onCategoryChange'
    }, */
    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        this.$('.js_select2').select2();
        let $category = this.$('select[name="category_id"]');
        $category.on('change', () => {
            let categoryId = ($category.val() || [""]);
            let $categoryText = this.$('input[name="categories_value_text"]');
            $categoryText.val(categoryId.join(','));
        });
        return def;
    },
});
});
