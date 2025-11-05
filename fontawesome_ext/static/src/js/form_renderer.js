odoo.define('fontawesome_ext.FormRenderer', function (require) {
"use strict";

var FormRenderer = require('web.FormRenderer');

FormRenderer.include({

    _renderStatButton: function (node) {
        var $button = this._super.apply(this, arguments);
        if (node.attrs.duotone_icon) {
            var icon_div = $('<i>')
                .addClass('duotone-icon fa-fw o_button_icon')
                .addClass(node.attrs.duotone_icon);
            var icon_path1 = $('<span>').addClass('path1');
            var icon_path2 = $('<span>').addClass('path2');
            icon_path2.prependTo(icon_path1);
            icon_path1.prependTo(icon_div);
            icon_div.prependTo($button);
        }
        return $button;
    },
    _renderTagButton: function (node) {
        var $button = this._super.apply(this, arguments);
        if (node.attrs.duotone_icon) {
            var icon_div = $('<i>')
                .addClass('duotone-icon fa-fw o_button_icon')
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
