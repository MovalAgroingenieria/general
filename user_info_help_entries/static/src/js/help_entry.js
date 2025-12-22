///** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

async function loadEntries(env) {
    const orm = env.services.orm;   // Acceder al servicio ORM desde env
    const entries = await orm.searchRead(
        "user.menu.help.entry",
        [],
        ["name", "url"],
        {}
    );
    entries.forEach((entry) => {
        registry
            .category("user_menuitems")
            .add(entry.name, (env) => {
                return {
                    type: "item",
                    id: entry.name,
                    description: env._t(entry.name),
                    href: entry.url,
                    callback: () => {
                        browser.open(entry.url, "_blank");
                    },
                    sequence: 10,
                };
            }, { sequence: 10, force: true });
    });
    console.log('asdasd');
}

// Registrar el código en el `user_menuitems`
registry.category("user_menuitems").add("prueba", async (env) => {
    await loadEntries(env);
    return {
            type: "item",
            id: 'test',
            hide: true,
            description: env._t('test'),
            href: 'https://google.es',
            callback: () => {
                browser.open('https://google.es', "_blank");
            },
            sequence: 10,
        };
 });

