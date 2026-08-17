/* 2026 Moval Agroingeniería
 * License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
 *
 * Lightweight signature pad for the QR attendance landing page.
 * Standalone (no Odoo assets): served from /base_assembly/static and loaded
 * by the plain HTML landing template. Captures a PNG data URL into the hidden
 * "signature" input on form submit; the button works with or without a sign.
 */
(function () {
    "use strict";

    function init() {
        var canvas = document.getElementById("sig-canvas");
        if (!canvas) {
            return;
        }
        var ctx = canvas.getContext("2d");
        var drawing = false;
        var hasSig = false;
        var last = null;

        function setup() {
            var rect = canvas.getBoundingClientRect();
            var ratio = window.devicePixelRatio || 1;
            canvas.width = Math.round(rect.width * ratio);
            canvas.height = Math.round(rect.height * ratio);
            ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
            ctx.lineWidth = 2.2;
            ctx.lineCap = "round";
            ctx.lineJoin = "round";
            ctx.strokeStyle = "#111";
        }

        function point(e) {
            var rect = canvas.getBoundingClientRect();
            var src = e.touches && e.touches[0] ? e.touches[0] : e;
            return { x: src.clientX - rect.left, y: src.clientY - rect.top };
        }

        function start(e) {
            drawing = true;
            last = point(e);
            e.preventDefault();
        }

        function move(e) {
            if (!drawing) {
                return;
            }
            var p = point(e);
            ctx.beginPath();
            ctx.moveTo(last.x, last.y);
            ctx.lineTo(p.x, p.y);
            ctx.stroke();
            last = p;
            hasSig = true;
            e.preventDefault();
        }

        function end() {
            drawing = false;
        }

        setup();
        canvas.addEventListener("mousedown", start);
        canvas.addEventListener("mousemove", move);
        window.addEventListener("mouseup", end);
        canvas.addEventListener("touchstart", start, { passive: false });
        canvas.addEventListener("touchmove", move, { passive: false });
        canvas.addEventListener("touchend", end);

        var clearBtn = document.getElementById("sig-clear");
        if (clearBtn) {
            clearBtn.addEventListener("click", function () {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                hasSig = false;
                var input = document.getElementById("sig-input");
                if (input) {
                    input.value = "";
                }
            });
        }

        var form = document.getElementById("attendance-form");
        if (form) {
            form.addEventListener("submit", function () {
                var input = document.getElementById("sig-input");
                if (input) {
                    input.value = hasSig ? canvas.toDataURL("image/png") : "";
                }
            });
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
