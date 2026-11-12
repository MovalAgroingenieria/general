odoo.define('board_grafana_integration.panel', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');
var SystrayMenu = require('web.SystrayMenu');
var WebClient = require('web.WebClient');
var Widget = require('web.Widget');

var QWeb = core.qweb;

var WIDTH_STORAGE_KEY = 'board_grafana_integration.panel_width';
var DEFAULT_WIDTH = 600;
var MIN_WIDTH = 320;
var MAX_WIDTH_RATIO = 0.7;
var AUTH_ROUTE = '/board_grafana/auth';
var ACTION_UPDATED_EVENT = 'board_grafana_integration:current_action_updated';
// Query parameters not kept when a Grafana page is opened in a new tab:
// the token of the previous sign-in and the kiosk mode, which is only added
// on request
var DROPPED_URL_PARAMS = [
    'auth_token',
    'kiosk',
    '_dash.hideTimePicker',
    '_dash.hideVariables',
    '_dash.hideLinks',
];
// Kiosk mode: no Grafana menus, and (Grafana 11.3 or later) no time picker,
// variables or dashboard links. "kiosk" goes without value, as documented
// by Grafana. Same as KIOSK_URL_PARAMS of board.grafana (Python).
var KIOSK_URL_PARAMS = [
    'kiosk',
    '_dash.hideTimePicker=true',
    '_dash.hideVariables=true',
    '_dash.hideLinks=true',
];

function getFrameUrl(iframe) {
    var url = iframe.src;
    // Grafana is served from the same domain as Odoo, so the page being
    // displayed can be read. Otherwise the browser blocks it and the page
    // first loaded in the iframe is used.
    try {
        var location_url = iframe.contentWindow.location.href;
        if (location_url && location_url !== 'about:blank') {
            url = location_url;
        }
    } catch (e) {
        url = iframe.src;
    }
    return url;
}

function cleanGrafanaUrl(url, kiosk) {
    // Grafana paths (e.g. "/d/<uid>") are kept relative to the Grafana URL
    var is_path = url.charAt(0) === '/' && url.charAt(1) !== '/';
    var parsed_url = new URL(url, window.location.href);
    _.each(DROPPED_URL_PARAMS, function (param) {
        parsed_url.searchParams.delete(param);
    });
    if (kiosk) {
        parsed_url.search = (parsed_url.search ?
            parsed_url.search + '&' : '?') + KIOSK_URL_PARAMS.join('&');
    }
    return is_path ?
        parsed_url.pathname + parsed_url.search + parsed_url.hash :
        parsed_url.href;
}

function getGrafanaAuthUrl(url, kiosk) {
    var parsed_url = new URL(url, window.location.href);
    var grafana_url = parsed_url.href;
    // The page first loaded in the iframe is already the Odoo route
    if (parsed_url.origin === window.location.origin &&
            parsed_url.pathname === AUTH_ROUTE) {
        grafana_url = parsed_url.searchParams.get('path') || '';
    }
    return AUTH_ROUTE + '?path=' +
        encodeURIComponent(cleanGrafanaUrl(grafana_url, kiosk));
}

function openInGrafana(widget, url, kiosk) {
    var def;
    if (url && url !== 'about:blank') {
        // Opened through Odoo, which signs the user in to Grafana again
        window.open(getGrafanaAuthUrl(url, kiosk), '_blank');
        def = $.when();
    } else {
        def = new Model('board.grafana')
            .call('action_go_to_grafana_server', [[]])
            .then(function (action) {
                return widget.do_action(action);
            });
    }
    return def;
}

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
        return iframe ? getFrameUrl(iframe) : false;
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
        event.preventDefault();
        openInGrafana(this, this._getCurrentUrl());
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

// Shown only while the Grafana dashboard (board.grafana form) is displayed
var GrafanaOpenSystrayItem = Widget.extend({
    template: 'board_grafana_integration.OpenSystrayItem',
    events: {
        'click a': '_onClick',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.action = false;
        this.is_enabled = false;
        core.bus.on(ACTION_UPDATED_EVENT, this, this._onCurrentActionUpdated);
    },

    start: function () {
        var self = this;
        this._updateVisibility();
        // Hidden until the server confirms the setting and the access rights
        new Model('board.grafana')
            .call('is_grafana_open_button_visible', [])
            .then(function (is_enabled) {
                self.is_enabled = is_enabled;
                self._updateVisibility();
            });
        return this._super.apply(this, arguments);
    },

    _isGrafanaAction: function (action) {
        var action_descr = action && action.action_descr;
        var widget = action && action.widget;
        return Boolean(action_descr &&
            action_descr.res_model === 'board.grafana' &&
            widget && widget.active_view &&
            widget.active_view.type === 'form');
    },

    _getFrame: function () {
        var widget = this.action && this.action.widget;
        return widget ? widget.$('iframe#grafana_frame')[0] : undefined;
    },

    _updateVisibility: function () {
        if (this.$el) {
            this.$el.toggleClass('o_hidden', !(this.is_enabled && this.action));
        }
    },

    _onCurrentActionUpdated: function (action) {
        this.action = this._isGrafanaAction(action) ? action : false;
        this._updateVisibility();
    },

    _onClick: function (event) {
        var iframe = this._getFrame();
        event.preventDefault();
        openInGrafana(this, iframe ? getFrameUrl(iframe) : false, true);
    },
});

WebClient.include({
    current_action_updated: function (action) {
        this._super.apply(this, arguments);
        core.bus.trigger(ACTION_UPDATED_EVENT, action);
    },
});

SystrayMenu.Items.push(GrafanaSystrayItem);
SystrayMenu.Items.push(GrafanaOpenSystrayItem);

return {
    GrafanaPanel: GrafanaPanel,
    GrafanaSystrayItem: GrafanaSystrayItem,
    GrafanaOpenSystrayItem: GrafanaOpenSystrayItem,
};

});
