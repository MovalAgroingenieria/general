odoo.define('board_grafana_integration.kiosk', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');
var Widget = require('web.Widget');
// Required by the "Back to Odoo" button, disabled for now
// var web_client = require('web.web_client');

var QWeb = core.qweb;

// Full screen client action ("Grafana kiosk dashboard"), meant to be the
// home action of the users that only have to see a Grafana dashboard
var GrafanaKiosk = Widget.extend({
    template: 'board_grafana_integration.Kiosk',
    // Disabled for now: the users of this home action must not go back to
    // Odoo
    // events: {
    //     'click .o_grafana_kiosk_exit': '_onExit',
    // },

    start: function () {
        var $body = this.$('.o_grafana_kiosk_body');
        $body.html(QWeb.render('board_grafana_integration.PanelLoading'));
        new Model('board.grafana').call('get_grafana_kiosk_frame', [])
            .then(function (frame) {
                $body.html(frame);
            });
        return this._super.apply(this, arguments);
    },

    // _onExit: function (event) {
    //     // Same menu that Odoo opens when the user has no home action
    //     var first_menu_id = web_client.menu.$el.find('a:first')
    //         .data('menu');
    //     event.preventDefault();
    //     if (first_menu_id) {
    //         web_client.menu.menu_click(first_menu_id);
    //     }
    // },
});

core.action_registry.add('board_grafana_kiosk', GrafanaKiosk);

return GrafanaKiosk;

});
