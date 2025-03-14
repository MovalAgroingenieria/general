odoo.define('user_info_help_entries.help_entry', function (require) {
    'use strict';

    var UserMenu = require('web.UserMenu');
    var rpc = require('web.rpc');
    var session = require('web.session');

    UserMenu.include({
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self._fetchHelpEntries();
            });
        },

        _fetchHelpEntries: function () {
            var self = this;

            rpc.query({
                model: 'user.menu.help.entry',
                method: 'search_read',
                args: [[['active', '=', true]], ['name', 'url', 'groups']],
            }).then(function (entries) {
                if (!entries || !entries.length) {
                    return;
                }
                self._filterEntriesByUserGroups(entries);
            });
        },

        _filterEntriesByUserGroups: function (entries) {
            var self = this;

            rpc.query({
                model: 'res.users',
                method: 'read',
                args: [[session.uid], ['groups_id']],
            }).then(function (userData) {
                var userGroups = userData && userData[0] && userData[0].groups_id ? userData[0].groups_id : [];

                var filteredEntries = _.filter(entries, function (entry) {
                    return !entry.groups || entry.groups.length === 0 || _.intersection(entry.groups, userGroups).length > 0;
                });

                if (filteredEntries.length > 0) {
                    self._renderHelpEntries(filteredEntries);
                }
            });
        },

        _renderHelpEntries: function (entries) {
            var $userDropdownMenu = this.$('.dropdown-menu');

            if (!$userDropdownMenu.length) {
                return;
            }

            // **1. Eliminar elementos no deseados**
            $userDropdownMenu.find("a[data-menu='documentation'], a[data-menu='support'], a[data-menu='shortcuts'], a[data-menu='account']").remove();

            // **2. Buscar "Cerrar sesión"**
            var $logoutMenu = $userDropdownMenu.find("a[data-menu='logout']").first();

            // **3. Agregar un separador ANTES de las nuevas entradas si no existe ya uno**
            if (!$logoutMenu.prev('.dropdown-divider').length) {
                $logoutMenu.before($('<div role="separator" class="dropdown-divider"></div>'));
            }

            // **4. Insertar las nuevas entradas**
            _.each(entries, function (entry) {
                var $a = $('<a/>', {
                    href: entry.url,
                    target: '_blank',
                    text: entry.name,
                    class: 'dropdown-item',
                    role: 'menuitem',
                });

                $logoutMenu.before($a);
            });

            // **5. Agregar un separador DESPUÉS de las nuevas entradas (antes de "Cerrar sesión")**
            if (!$logoutMenu.prev('.dropdown-divider').length) {
                $logoutMenu.before($('<div role="separator" class="dropdown-divider"></div>'));
            }
        },
    });
});
