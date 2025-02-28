odoo.define("sh_task_time.time_track", function (require) {
    "use strict";
    var AbstractField = require("web.AbstractField");
    var core = require("web.core");
    var field_registry = require("web.field_registry");
    var time = require("web.time");
    var Widget = require("web.Widget");
    var _t = core._t;
    var TimeCounter = AbstractField.extend({
        supportedFieldTypes: [],

        willStart: function () {
            var self = this;
            var def = this._rpc({
                model: "account.analytic.line",
                method: "search_read",
                domain: [
                    ["task_id", "=", this.record.data.id],
                    ["end_date", "=", false],
                    ["start_date", "!=", false],
                ],
            }).then(function (result) {
            	console.log('result->'+result);
                if (self.mode === "readonly") {
                    var currentDate = new Date();
                    self.duration = 0;
                    _.each(result, function (data) {
                        self.duration += data.end_date ? self._getDateDifference(data.start_date, data.end_date) : self._getDateDifference(time.auto_str_to_date(data.start_date), currentDate);
                    });
                }
            });
            return $.when(this._super.apply(this, arguments), def);
        },

        destroy: function () {
            this._super.apply(this, arguments);
            clearTimeout(this.timer);
        },

        isSet: function () {
            return true;
        },

        _getDateDifference: function (dateStart, dateEnd) {
            return moment(dateEnd).diff(moment(dateStart));
        },

        _render: function () {
            this._startTimeCounter();
        },

        _startTimeCounter: function () {
            var self = this;
            this.timer = "";
            clearTimeout(this.timer);
            if (this.record.data.start_time) {
                this.timer = setTimeout(function () {
                    self.duration += 1000;
                    self._startTimeCounter();
                }, 1000);
            } else {
                clearTimeout(this.timer);
            }
            this.$el.html($("<span>" + moment.utc(this.duration).format("HH:mm:ss") + "</span>"));
        },
    });

    field_registry.add("task_time_counter", TimeCounter);
});
