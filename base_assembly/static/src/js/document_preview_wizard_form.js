/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { status } from "@odoo/owl";

import { FormController } from "@web/views/form/form_controller";

patch(FormController.prototype, {
    async afterExecuteActionButton(clickParams) {
        await super.afterExecuteActionButton(...arguments);
        if (
            clickParams?.name !== "action_refresh_preview" ||
            this.props?.resModel !== "assembly.document.preview.wizard" ||
            status(this) === "destroyed"
        ) {
            return;
        }
        try {
            if (this.model.root.resId) {
                await this.model.root.load();
            }
        } catch {
            /* Dialog may have been replaced by the returned act_window (target new). */
        }
    },
});
