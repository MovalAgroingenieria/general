// -*- coding: utf-8 -*-
odoo.define('remotecontrol_avamet.AvametImport', function (require) {
    'use strict';

    var Widget = require('web.Widget');
    var Model = require('web.DataModel');
    var session = require('web.session');
    var core = require('web.core');
    var QWeb = core.qweb;
    var _t = core._t;

    var AvametImportWidget = Widget.extend({

        events: {
            'click .o_avamet_btn_reload':         '_onReload',
            'click .o_avamet_btn_create':          '_onCreate',
            'click .o_avamet_station_title':       '_onToggleStation',
            'click .o_avamet_btn_sel_station':     '_onSelectStation',
            'click .o_avamet_btn_desel_station':   '_onDeselectStation',
            'click .o_avamet_btn_sel_all':         '_onSelectAll',
            'click .o_avamet_btn_desel_all':       '_onDeselectAll',
            'change .o_avamet_sensor_chk':         '_onSensorCheck',
        },

        init: function (parent, action) {
            this._super(parent, action);
            this.remotecontrol_id = action.context.remotecontrol_id;
            this.remotecontrol_name = action.context.remotecontrol_name || '';
            this.wizard_id = null;
            this.initial_date = '';
            this.stations = [];
            this.sensors = [];
            this.station_sel = {};
            this.sensor_sel = {};
            this.expanded = {};
            this.existing_device_lines = {};
            this.existing_sensor_lines = {};
            this.last_clicked_sensor_id = null;
            this.loading = false;
            this.status = '';
            this.error = '';
        },

        willStart: function () {
            var self = this;
            var wizard_model = new Model('remotecontrol.avamet.import.wizard');
            return this._super().then(function () {
                return wizard_model.call('create', [{
                    remotecontrol_id: self.remotecontrol_id,
                }]).then(function (wizard_id) {
                    self.wizard_id = wizard_id;
                    return wizard_model.call(
                        'read', [[wizard_id], ['initial_date']]
                    );
                }).then(function (result) {
                    self.initial_date = result[0].initial_date || '';
                });
            });
        },

        start: function () {
            var self = this;
            return this._super().then(function () {
                self._render();
            });
        },

        // ------------------------------------------------------------------
        // Render
        // ------------------------------------------------------------------

        _render: function () {
            var lang = (session.user_context && session.user_context.lang) || '';
            var l = {
                initial_date:  _t('Initial date'),
                btn_load:      _t('Load from AVAMET'),
                btn_create:    _t('Create devices and sensors'),
                creating:      _t('Creating...'),
                loading_msg:   _t('Loading stations from AVAMET API...'),
                import_log:    _t('Import log'),
                n_selected:    _t('sensors selected'),
                select_all:    _t('Select all'),
                deselect_all:  _t('Deselect all'),
                station_all:   _t('All'),
                exists_device: _t('Device already exists \u2013 will be updated'),
                exists_badge:  _t('exists'),
                exists_sensor: _t('Sensor already exists \u2013 will be updated'),
                empty_hint:    _t(
                    'Click "Load from AVAMET" to fetch available stations and sensors.'
                ),
                col_api:    _t('API field'),
                col_name:   _t('Sensor name'),
                col_sample: _t('Sample'),
                col_uom:    _t('UOM'),
                col_short:  _t('Short'),
            };
            if (lang.indexOf('es') === 0) {
                l = _.extend(l, {
                    initial_date:  'Fecha inicial',
                    btn_load:      'Cargar desde AVAMET',
                    btn_create:    'Crear dispositivos y sensores',
                    creating:      'Creando...',
                    loading_msg:   'Cargando estaciones desde la API de AVAMET...',
                    import_log:    'Registro de importacion',
                    n_selected:    'sensores seleccionados',
                    select_all:    'Seleccionar todo',
                    deselect_all:  'Deseleccionar todo',
                    station_all:   'Todo',
                    exists_device: 'El dispositivo ya existe: se actualizara',
                    exists_badge:  'existe',
                    exists_sensor: 'El sensor ya existe: se actualizara',
                    empty_hint:    'Haz clic en "Cargar desde AVAMET" para obtener las estaciones y sensores disponibles.',
                    col_api:       'Campo API',
                    col_name:      'Nombre del sensor',
                    col_sample:    'Muestra',
                    col_uom:       'UdM',
                    col_short:     'Corto',
                });
            } else if (lang.indexOf('ca') === 0) {
                l = _.extend(l, {
                    initial_date:  'Data inicial',
                    btn_load:      'Carrega des d\'AVAMET',
                    btn_create:    'Crear dispositius i sensors',
                    creating:      'Creant...',
                    loading_msg:   'Carregant estacions des de l\'API d\'AVAMET...',
                    import_log:    'Registre d\'importacio',
                    n_selected:    'sensors seleccionats',
                    select_all:    'Seleccionar-ho tot',
                    deselect_all:  'Deseleccionar-ho tot',
                    station_all:   'Tot',
                    exists_device: 'El dispositiu ja existeix: s\'actualitzara',
                    exists_badge:  'existeix',
                    exists_sensor: 'El sensor ja existeix: s\'actualitzara',
                    empty_hint:    'Fes clic a "Carrega des d\'AVAMET" per obtenir les estacions i sensors disponibles.',
                    col_api:       'Camp API',
                    col_name:      'Nom del sensor',
                    col_sample:    'Mostra',
                    col_uom:       'UdM',
                    col_short:     'Curt',
                });
            }
            this.$el.html(QWeb.render('AvametImport', {widget: this, l: l}));
        },

        // ------------------------------------------------------------------
        // Helpers (called from QWeb template)
        // ------------------------------------------------------------------

        _stationSensors: function (station_id) {
            return _.filter(this.sensors, function (s) {
                return s.device_line_id && s.device_line_id[0] === station_id;
            });
        },

        _stationSelectedCount: function (station_id) {
            var self = this;
            return _.filter(this._stationSensors(station_id), function (s) {
                return self.sensor_sel[s.id];
            }).length;
        },

        _totalSelected: function () {
            return _.filter(_.values(this.sensor_sel), Boolean).length;
        },

        // ------------------------------------------------------------------
        // DOM partial updates (avoid full re-render on every checkbox click)
        // ------------------------------------------------------------------

        _updateBadge: function (station_id) {
            var total = this._stationSensors(station_id).length;
            var sel = this._stationSelectedCount(station_id);
            this.$('[data-badge-for="' + station_id + '"]').text(sel + '/' + total);
        },

        _updateGlobalBar: function () {
            var total = this.sensors.length;
            var sel = this._totalSelected();
            this.$('.o_avamet_global_count').text(sel + '/' + total);
            this.$('.o_avamet_btn_create')
                .prop('disabled', sel === 0)
                .find('.o_avamet_create_count').text(sel);
        },

        // ------------------------------------------------------------------
        // Data loading (called after reload)
        // ------------------------------------------------------------------

        _loadData: function () {
            var self = this;
            var wizard_model = new Model('remotecontrol.avamet.import.wizard');
            var device_model = new Model(
                'remotecontrol.avamet.import.wizard.device.line');
            var line_model = new Model(
                'remotecontrol.avamet.import.wizard.line');

            return wizard_model.call(
                'read', [[self.wizard_id], ['status_message']]
            ).then(function (result) {
                self.status = result[0].status_message || '';
                return device_model.call('search_read', [], {
                    domain: [['wizard_id', '=', self.wizard_id]],
                    fields: ['id', 'station_id', 'station_name', 'selected'],
                    order: 'station_name',
                });
            }).then(function (stations) {
                self.stations = stations;
                self.station_sel = {};
                self.expanded = {};
                _.each(stations, function (s) {
                    self.station_sel[s.id] = s.selected;
                    self.expanded[s.id] = true;
                });
                return line_model.call('search_read', [], {
                    domain: [['wizard_id', '=', self.wizard_id]],
                    fields: ['id', 'device_line_id', 'station_name',
                             'api_field', 'sensor_name', 'sample_value',
                             'uom_name', 'uom_short_name', 'selected'],
                    order: 'station_name, sensor_name',
                });
            }).then(function (lines) {
                self.sensors = lines;
                self.sensor_sel = {};
                self.last_clicked_sensor_id = null;
                _.each(lines, function (l) {
                    self.sensor_sel[l.id] = l.selected;
                });
                return wizard_model.call('check_existing', [[self.wizard_id]], {});
            }).then(function (existing) {
                self.existing_device_lines = {};
                self.existing_sensor_lines = {};
                _.each(existing.device_line_ids, function (id) {
                    self.existing_device_lines[id] = true;
                });
                _.each(existing.sensor_line_ids, function (id) {
                    self.existing_sensor_lines[id] = true;
                });
            });
        },

        // ------------------------------------------------------------------
        // Event handlers
        // ------------------------------------------------------------------

        _onReload: function () {
            var self = this;
            var date_val = this.$('.o_avamet_date_input').val() || false;
            self.loading = true;
            self.error = '';
            self._render();

            var wizard_model = new Model('remotecontrol.avamet.import.wizard');
            wizard_model.call(
                'write', [[self.wizard_id], {initial_date: date_val}]
            ).then(function () {
                return wizard_model.call(
                    'action_reload_stations', [[self.wizard_id]]
                );
            }).then(function () {
                return self._loadData();
            }).then(function () {
                self.loading = false;
                self._render();
            }).fail(function (err) {
                self.loading = false;
                self.error = (err.data && err.data.message) ||
                             err.message || 'Error loading stations';
                self._render();
            });
        },

        _onToggleStation: function (e) {
            var station_id = parseInt(
                $(e.currentTarget).data('station-id'), 10);
            this.expanded[station_id] = !this.expanded[station_id];
            this.$('[data-body-for="' + station_id + '"]')
                .toggle(this.expanded[station_id]);
            $(e.currentTarget).find('.o_avamet_toggle_icon')
                .toggleClass('fa-chevron-down', this.expanded[station_id])
                .toggleClass('fa-chevron-right', !this.expanded[station_id]);
        },

        _onSensorCheck: function (e) {
            var sensor_id = parseInt($(e.target).data('sensor-id'), 10);
            var station_id = parseInt($(e.target).data('station-id'), 10);
            var new_state = e.target.checked;

            if (e.shiftKey && this.last_clicked_sensor_id !== null) {
                // Range selection: apply new_state to all sensors between
                // last clicked and current, inclusive.
                var sensor_ids = _.pluck(this.sensors, 'id');
                var cur_idx = _.indexOf(sensor_ids, sensor_id);
                var last_idx = _.indexOf(sensor_ids, this.last_clicked_sensor_id);
                var start = Math.min(cur_idx, last_idx);
                var end = Math.max(cur_idx, last_idx);
                var self = this;
                for (var i = start; i <= end; i++) {
                    var sid = sensor_ids[i];
                    self.sensor_sel[sid] = new_state;
                    self.$('[data-sensor-id="' + sid + '"].o_avamet_sensor_chk')
                        .prop('checked', new_state);
                    self.$('[data-sensor-id="' + sid + '"]').closest('tr')
                        .toggleClass('o_avamet_deselected', !new_state);
                }
                _.each(this.stations, function (st) {
                    self._updateBadge(st.id);
                });
            } else {
                this.sensor_sel[sensor_id] = new_state;
                $(e.target).closest('tr')
                    .toggleClass('o_avamet_deselected', !new_state);
                this._updateBadge(station_id);
            }

            // Anchor only moves on non-shift click
            if (!e.shiftKey) {
                this.last_clicked_sensor_id = sensor_id;
            }
            this._updateGlobalBar();
        },

        _onSelectStation: function (e) {
            e.stopPropagation();
            this._setStationSelection(
                parseInt($(e.currentTarget).data('station-id'), 10), true);
        },

        _onDeselectStation: function (e) {
            e.stopPropagation();
            this._setStationSelection(
                parseInt($(e.currentTarget).data('station-id'), 10), false);
        },

        _setStationSelection: function (station_id, value) {
            var self = this;
            var sensors = this._stationSensors(station_id);
            _.each(sensors, function (s) {
                self.sensor_sel[s.id] = value;
                self.$('[data-sensor-id="' + s.id + '"].o_avamet_sensor_chk')
                    .prop('checked', value);
                self.$('[data-sensor-id="' + s.id + '"]').closest('tr')
                    .toggleClass('o_avamet_deselected', !value);
            });
            this.station_sel[station_id] = value;
            this.last_clicked_sensor_id = null;
            this._updateBadge(station_id);
            this._updateGlobalBar();
        },

        _onSelectAll: function () {
            var self = this;
            _.each(this.sensors, function (s) {
                self.sensor_sel[s.id] = true;
            });
            _.each(this.stations, function (st) {
                self.station_sel[st.id] = true;
            });
            this.$('.o_avamet_sensor_chk').prop('checked', true);
            this.$('.o_avamet_sensor_row').removeClass('o_avamet_deselected');
            _.each(this.stations, function (st) {
                self._updateBadge(st.id);
            });
            this.last_clicked_sensor_id = null;
            this._updateGlobalBar();
        },

        _onDeselectAll: function () {
            var self = this;
            _.each(this.sensors, function (s) {
                self.sensor_sel[s.id] = false;
            });
            _.each(this.stations, function (st) {
                self.station_sel[st.id] = false;
            });
            this.$('.o_avamet_sensor_chk').prop('checked', false);
            this.$('.o_avamet_sensor_row').addClass('o_avamet_deselected');
            _.each(this.stations, function (st) {
                self._updateBadge(st.id);
            });
            this.last_clicked_sensor_id = null;
            this._updateGlobalBar();
        },

        _onCreate: function () {
            var self = this;
            var selected_sensor_ids = [];
            var selected_device_ids = [];
            var sensor_edits = {};

            _.each(self.sensors, function (s) {
                if (self.sensor_sel[s.id]) {
                    selected_sensor_ids.push(s.id);
                }
            });
            // A station must be included whenever at least one of its
            // sensors is selected — station_sel is not updated on individual
            // checkbox changes, so derive it from the sensor state.
            _.each(self.stations, function (st) {
                var has_selected = _.some(
                    self._stationSensors(st.id),
                    function (s) { return self.sensor_sel[s.id]; }
                );
                if (has_selected) {
                    selected_device_ids.push(st.id);
                }
            });

            // Collect inline name/uom edits
            self.$('.o_avamet_sensor_name_input').each(function () {
                var sid = parseInt($(this).data('sensor-id'), 10);
                sensor_edits[sid] = sensor_edits[sid] || {};
                sensor_edits[sid].sensor_name = $(this).val();
            });
            self.$('.o_avamet_uom_name_input').each(function () {
                var sid = parseInt($(this).data('sensor-id'), 10);
                sensor_edits[sid] = sensor_edits[sid] || {};
                sensor_edits[sid].uom_name = $(this).val();
            });
            self.$('.o_avamet_uom_short_input').each(function () {
                var sid = parseInt($(this).data('sensor-id'), 10);
                sensor_edits[sid] = sensor_edits[sid] || {};
                sensor_edits[sid].uom_short_name = $(this).val();
            });

            if (!selected_sensor_ids.length) {
                return;
            }

            self.$('.o_avamet_btn_create').prop('disabled', true);
            self.$('.o_avamet_creating_msg').show();
            self.$('.o_avamet_error_msg').hide();

            var wizard_model = new Model('remotecontrol.avamet.import.wizard');
            wizard_model.call('action_apply_and_create', [
                [self.wizard_id],
                selected_sensor_ids,
                selected_device_ids,
                sensor_edits,
            ]).then(function (result) {
                // Navigate via URL to force a clean page reload.
                // Using do_action() for the transition from a client action
                // to act_window in the same call stack causes rendering bugs
                // in the tree view (QWeb2 - TreeView.rows TypeError).
                window.location.href = '/web#action=' + result.action_id;
            }).fail(function (err) {
                self.$('.o_avamet_btn_create').prop('disabled', false);
                self.$('.o_avamet_creating_msg').hide();
                var msg = (err.data && err.data.message) ||
                          err.message || 'Error creating devices';
                self.$('.o_avamet_error_msg').text(msg).show();
            });
        },
    });

    core.action_registry.add('avamet_import', AvametImportWidget);

    return AvametImportWidget;
});
