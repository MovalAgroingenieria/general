/** @odoo-module **/

import {FormController} from "@web/views/form/form_controller";
import {registry} from "@web/core/registry";

const notificationHandler = {
    dependencies: ["notification"],

    start(env, {notification}) {
        const originalSetup = FormController.prototype.setup;

        FormController.prototype.setup = function () {
            originalSetup.call(this);
            this.notification = notification;

            const ctx = this.props?.context ||
                this.props?.action?.context ||
                this.model?.root?.context ||
                this.env?.config?.context ||
                {};

            const msg = ctx.notification_message;
            if (msg) {
                setTimeout(() => {
                    this.notification.add(msg, {
                        title: env._t("Success"),
                        type: "success",
                        sticky: false,
                    });
                }, 300);
            }
        };
    }
};

registry.category("services").add("notification_handler", notificationHandler);