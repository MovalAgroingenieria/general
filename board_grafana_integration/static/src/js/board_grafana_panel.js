odoo.define('board_grafana_integration.panel', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');
var SystrayMenu = require('web.SystrayMenu');
var Widget = require('web.Widget');

var QWeb = core.qweb;

var WIDTH_STORAGE_KEY = 'board_grafana_integration.panel_width';
var DEFAULT_WIDTH = 600;
var MIN_WIDTH = 320;
var MAX_WIDTH_RATIO = 0.7;

var GrafanaPanel = Widget.extend({
    template: 'board_grafana_integration.Panel',
    events: {
        'click .o_grafana_panel_close': '_onClose',
        'click .o_grafana_panel_reload': '_onReload',
        'click .o_grafana_panel_new_tab': '_onNewTab',
        'mousedown .o_grafana_panel_resizer': '_onResizeStart',
    },

    init: function (parent) {
        this._super.apply(this, arguments);
        this.grafana_model = new Model('board.grafana');
        this.is_open = false;
        this.is_loaded = false;
        // Width chosen by the user; the applied one may be smaller if the
        // window is narrow
        this.width = this._getStoredWidth();
    },

    start: function () {
        this._applyWidth();
        $(window).on('resize.grafana_panel',
            _.debounce(this._applyWidth.bind(this), 100));
        return this._super.apply(this, arguments);
    },

    destroy: function () {
        $(document).off('.grafana_panel');
        $(window).off('.grafana_panel');
        $('body').removeClass('o_grafana_panel_open');
        this._super.apply(this, arguments);
    },

    toggle: function () {
        if (this.is_open) {
            this.close();
        } else {
            this.open();
        }
    },

    open: function () {
        this.is_open = true;
        this.$el.removeClass('o_hidden');
        $('body').addClass('o_grafana_panel_open');
        this._applyWidth();
        // The iframe is only loaded the first time the panel is opened
        if (!this.is_loaded) {
            this._load();
        }
        core.bus.trigger('resize');
    },

    close: function () {
        this.is_open = false;
        this.$el.addClass('o_hidden');
        $('body').removeClass('o_grafana_panel_open');
        core.bus.trigger('resize');
    },

    _load: function () {
        var self = this;
        var $body = this.$('.o_grafana_panel_body');
        $body.html(QWeb.render('board_grafana_integration.PanelLoading'));
        return this.grafana_model.call('get_grafana_panel_frame', [])
            .then(function (frame) {
                $body.html(frame);
                // The "not configured" warning is retried on the next
                // opening
                self.is_loaded = $body.find('iframe').length > 0;
            }, function () {
                $body.empty();
                self.is_loaded = false;
            });
    },

    _getCurrentUrl: function () {
        var iframe = this.$('.o_grafana_panel_frame')[0];
        var url = false;
        if (iframe) {
            url = iframe.src;
            // Grafana is served from the same domain as Odoo, so the page
            // being displayed can be read. Otherwise the browser blocks it.
            try {
                url = iframe.contentWindow.location.href;
            } catch (e) {
                url = iframe.src;
            }
        }
        return url;
    },

    _getStoredWidth: function () {
        var width = parseInt(
            window.localStorage.getItem(WIDTH_STORAGE_KEY), 10);
        return width || DEFAULT_WIDTH;
    },

    _clampWidth: function (width) {
        var max_width = Math.floor(window.innerWidth * MAX_WIDTH_RATIO);
        return Math.max(MIN_WIDTH, Math.min(width, max_width));
    },

    _applyWidth: function () {
        var width = this._clampWidth(this.width);
        this.$el.css('width', width + 'px');
        document.body.style.setProperty(
            '--o-grafana-panel-width', width + 'px');
    },

    _onClose: function (event) {
        event.preventDefault();
        this.close();
    },

    _onReload: function (event) {
        event.preventDefault();
        this._load();
    },

    _onNewTab: function (event) {
        var self = this;
        var url = this._getCurrentUrl();
        event.preventDefault();
        if (url && url !== 'about:blank') {
            window.open(url, '_blank');
        } else {
            this.grafana_model.call('action_go_to_grafana_server', [[]])
                .then(function (action) {
                    self.do_action(action);
                });
        }
    },

    _onResizeStart: function (event) {
        var self = this;
        event.preventDefault();
        // While dragging, the iframe must not capture the mouse events
        this.$el.addClass('o_grafana_panel_resizing');
        $(document)
            .on('mousemove.grafana_panel', function (ev) {
                self.width = self._clampWidth(window.innerWidth - ev.clientX);
                self._applyWidth();
            })
            .on('mouseup.grafana_panel', function () {
                $(document).off('.grafana_panel');
                self.$el.removeClass('o_grafana_panel_resizing');
                window.localStorage.setItem(WIDTH_STORAGE_KEY, self.width);
                core.bus.trigger('resize');
            });
    },
});

var GrafanaSystrayItem = Widget.extend({
    template: 'board_grafana_integration.SystrayItem',
    events: {
        'click a': '_onClick',
    },

    start: function () {
        var self = this;
        // Hidden until the server confirms the setting and the access rights
        this.$el.addClass('o_hidden');
        new Model('board.grafana')
            .call('is_grafana_navbar_button_visible', [])
            .then(function (is_visible) {
                self.$el.toggleClass('o_hidden', !is_visible);
            });
        return this._super.apply(this, arguments);
    },

    destroy: function () {
        if (this.panel) {
            this.panel.destroy();
        }
        this._super.apply(this, arguments);
    },

    _getPanel: function () {
        if (!this.panel_def) {
            this.panel = new GrafanaPanel(this);
            this.panel_def = this.panel
                .appendTo($('.o_web_client > .o_main'))
                .then(_.constant(this.panel));
        }
        return this.panel_def;
    },

    _onClick: function (event) {
        event.preventDefault();
        this._getPanel().then(function (panel) {
            panel.toggle();
        });
    },
});

SystrayMenu.Items.push(GrafanaSystrayItem);

return {
    GrafanaPanel: GrafanaPanel,
    GrafanaSystrayItem: GrafanaSystrayItem,
};

});
