odoo.define('fontawesome_ext.ListRenderer', function (require) {
"use strict";

var ListRenderer = require('web.ListRenderer');


ListRenderer.include({

    _renderButton: function (record, node) {
        var $button = this._super.apply(this, arguments);

        if (node.attrs.brand_icon) {
            $('<div>')
                .addClass('fab fa-fw o_button_icon')
                .addClass(node.attrs.brand_icon)
                .prependTo($button);
        }

        if (node.attrs.duotone_icon) {
            var icon_div = $('<div>')
                .addClass('duotone-icon btn-link o_icon_button')
                .addClass(node.attrs.duotone_icon);
            var icon_path1 = $('<span>').addClass('path1');
            var icon_path2 = $('<span>').addClass('path2');
            icon_path2.prependTo(icon_path1);
            icon_path1.prependTo(icon_div);
            icon_div.prependTo($button);
        }

        return $button;
    }
});

});
