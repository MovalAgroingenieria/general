/** @odoo-module **/

/**
 * Load Blockly from CDN (or override for self-hosted).
 * Used by web_blockly and modules that depend on it (e.g. base_vote_blockly).
 */

const BLOCKLY_CDN = "https://unpkg.com/blockly@9.3.3/blockly_compressed.js";
const BLOCKLY_BLOCKS_CDN = "https://unpkg.com/blockly@9.3.3/blocks_compressed.js";
const BLOCKLY_JAVASCRIPT_CDN = "https://unpkg.com/blockly@9.3.3/javascript_compressed.js";
const BLOCKLY_MSG_ES = "https://unpkg.com/blockly@9.3.3/msg/es.js";
export const BLOCKLY_MEDIA = "https://unpkg.com/blockly@9.3.3/media/";

export function loadScript(src) {
    return new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = src;
        script.onload = () => resolve();
        script.onerror = () => reject(new Error("Failed to load " + src));
        document.head.appendChild(script);
    });
}

/**
 * Load Blockly core and blocks. Resolves with window.Blockly.
 * Safe to call multiple times; returns same instance once loaded.
 */
export function loadBlockly() {
    if (window.Blockly && window.Blockly.Blocks) {
        return Promise.resolve(window.Blockly);
    }
    return loadScript(BLOCKLY_CDN)
        .then(() => loadScript(BLOCKLY_BLOCKS_CDN))
        .then(() => loadScript(BLOCKLY_JAVASCRIPT_CDN))
        .then(() => loadScript(BLOCKLY_MSG_ES).catch(() => {}))
        .then(() => {
            if (!window.Blockly || !window.Blockly.Blocks) {
                throw new Error("Blockly.Blocks not available after load");
            }
            return window.Blockly;
        });
}
