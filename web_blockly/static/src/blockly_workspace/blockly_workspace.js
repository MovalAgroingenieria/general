/** @odoo-module **/

import { Component, useRef, useEffect, onWillUnmount } from "@odoo/owl";
import { loadBlockly, BLOCKLY_MEDIA } from "../blockly_loader";

/**
 * Generic Blockly workspace component.
 * - value: XML string (workspace state)
 * - toolbox: Blockly toolbox config object (kind: "categoryToolbox", contents: [...])
 * - mediaPath: optional, default BLOCKLY_MEDIA
 * - getCode: optional function(workspace, Blockly) => string to derive code from workspace
 * - onValueChange: optional callback(xml, code) when workspace changes
 */
export class BlocklyWorkspace extends Component {
    static template = "web_blockly.BlocklyWorkspace";
    static props = {
        value: { type: String, optional: true },
        toolbox: { type: Object, optional: true },
        mediaPath: { type: String, optional: true },
        getCode: { type: Function, optional: true },
        onValueChange: { type: Function, optional: true },
    };

    setup() {
        this.containerRef = useRef("container");
        this.workspace = null;
        this.changeTimeout = null;
        this.resizeObserver = null;
        useEffect(() => {
            if (this.containerRef.el && !this.workspace) {
                this.onMount();
            }
        });
    }

    get mediaPath() {
        return this.props.mediaPath || BLOCKLY_MEDIA;
    }

    get toolbox() {
        return this.props.toolbox || { kind: "categoryToolbox", contents: [] };
    }

    async onMount() {
        const el = this.containerRef.el;
        if (!el || this.workspace) return;
        try {
            const Blockly = await loadBlockly();
            if (!this.containerRef.el || this.workspace) return;
            await this._waitForSize(el);
            if (!this.containerRef.el || this.workspace) return;
            this.workspace = Blockly.inject(el, {
                toolbox: this.toolbox,
                media: this.mediaPath,
                css: true,
                grid: { spacing: 20, length: 3 },
                zoom: { controls: true, wheel: true, startScale: 1 },
                trashcan: true,
            });
            const ws = this.workspace;
            const doResize = () => {
                if (ws && ws.resize) ws.resize();
            };
            setTimeout(doResize, 50);
            setTimeout(doResize, 300);
            this.resizeObserver = new ResizeObserver(() => doResize());
            this.resizeObserver.observe(el);
            const xml = this.props.value || "";
            if (xml.trim()) {
                try {
                    const textToDom = Blockly.utils?.xml?.textToDom || Blockly.Xml.textToDom;
                    const dom = textToDom(xml);
                    Blockly.Xml.domToWorkspace(dom, this.workspace);
                } catch (e) {
                    console.warn("Blockly: could not load initial XML", e);
                }
            }
            this.workspace.addChangeListener(() => this.scheduleNotify());
            this.scheduleNotify();
        } catch (e) {
            console.error("Blockly workspace load error", e);
        }
    }

    _waitForSize(el, deadline = Date.now() + 6000) {
        return new Promise((resolve) => {
            const tick = () => {
                if (el.offsetWidth > 0 || Date.now() > deadline) {
                    resolve();
                    return;
                }
                setTimeout(tick, 100);
            };
            tick();
        });
    }

    scheduleNotify() {
        if (this.changeTimeout) clearTimeout(this.changeTimeout);
        this.changeTimeout = setTimeout(() => this.notifyValue(), 0);
    }

    notifyValue() {
        if (!this.workspace || !window.Blockly) return;
        const Blockly = window.Blockly;
        const dom = Blockly.Xml.workspaceToDom(this.workspace);
        const xml = Blockly.Xml.domToText(dom);
        let code = "";
        if (this.props.getCode) {
            try {
                code = this.props.getCode(this.workspace, Blockly) || "";
            } catch (e) {
                console.warn("Blockly getCode error", e);
            }
        }
        if (this.props.onValueChange) {
            this.props.onValueChange(xml, code);
        }
    }

    onWillUnmount() {
        if (this.resizeObserver && this.containerRef.el) {
            this.resizeObserver.disconnect();
            this.resizeObserver = null;
        }
        if (this.changeTimeout) clearTimeout(this.changeTimeout);
        if (this.workspace && window.Blockly) {
            window.Blockly.WorkspaceSvg.prototype.dispose.call(this.workspace);
            this.workspace = null;
        }
    }
}
