odoo.define('customer_purchase_follow_up.notification_handler', function (require) {
"use strict";

var FormController = require('web.FormController');
var core = require('web.core');

FormController.include({
    /**
     * Override to show notification message from context
     */
    start: function () {
        var result = this._super.apply(this, arguments);
        var context = this.initialState.context;

        // Show notification if present in context
        if (context && context.notification_message) {
            var self = this;
            setTimeout(function() {
                self.displayNotification({
                    title: 'Éxito',
                    message: context.notification_message,
                    type: 'success',
                    sticky: false
                });
            }, 500);
        }

        return result;
    }
});

});