/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

/**
 * Service that preloads help menu entries.
 * It runs once when the web client starts.
 */
export const userMenuHelpEntriesService = {
    dependencies: ["orm"],

    async start(env, { orm }) {
        // Internal cache
        const state = {
            loaded: false,
            entries: [],
        };

        /**
         * Loads entries from the server (cached).
         */
        async function load() {
            if (state.loaded) {
                return state.entries;
            }

            state.entries = await orm.searchRead(
                "user.menu.help.entry",
                [],
                ["id", "name", "url"],
                {}
            );

            state.loaded = true;
            return state.entries;
        }

        // Preload data at startup to ensure synchronous access later
        await load();

        return {
            load,
            get entries() {
                return state.entries;
            },
            get loaded() {
                return state.loaded;
            },
        };
    },
};

// Register the service
registry.category("services").add(
    "user_menu_help_entries",
    userMenuHelpEntriesService
);

/**
 * Register dynamic items in the user menu.
 * IMPORTANT:
 * - No async
 * - No OWL hooks
 * - Must be fully synchronous
 */
registry.category("user_menuitems").add(
    "help_entries_dynamic",
    (env) => {
        const service = env.services.user_menu_help_entries;

        // Safety check: if data is not loaded yet, do not render anything
        if (!service || !service.loaded) {
            return {
                type: "item",
                id: "help_entries_loading",
                hide: true,
                description: "loading",
                sequence: 0,
            };
        }

        // Register one menu item per entry
        for (const entry of service.entries) {
            const itemId = `help_entry_${entry.id}`;

            registry.category("user_menuitems").add(
                itemId,
                () => ({
                    type: "item",
                    id: itemId,
                    description: entry.name, // dynamic DB value, already translated if field is translate=True
                    href: entry.url,
                    callback: () => browser.open(entry.url, "_blank"),
                    sequence: 10,
                }),
                { sequence: 10, force: true }
            );
        }

        // This item is hidden and only acts as a bootstrap
        return {
            type: "item",
            id: "help_entries_dynamic",
            hide: true,
            description: "help_entries_dynamic",
            sequence: 0,
        };
    },
    { sequence: 0, force: true }
);
