/**
 * AEGIS Holographic Orb & Audio Visualizer Controller
 */

class VisualizerManager {
    constructor() {
        this.orb = document.getElementById("hologramOrb");
        this.orbText = document.getElementById("orbStatusText");
        this.statusDot = document.getElementById("coreStatusDot");
    }

    setState(state, label = "") {
        if (!this.orb) return;

        // Reset classes
        this.orb.className = "hologram-orb";
        if (this.statusDot) this.statusDot.className = "status-indicator live-pulse";

        switch (state.toLowerCase()) {
            case "listening":
                this.orb.classList.add("listening");
                if (this.orbText) this.orbText.innerText = "VOICE INPUT DETECTING...";
                break;

            case "thinking":
            case "reasoning":
                this.orb.classList.add("thinking");
                if (this.orbText) this.orbText.innerText = "AEGIS REASONING & ANALYZING...";
                break;

            case "supervising":
            case "approval":
                this.orb.classList.add("supervising");
                if (this.orbText) this.orbText.innerText = "⚠️ SUPERVISION GATE ACTIVE";
                break;

            case "speaking":
                this.orb.classList.add("listening");
                if (this.orbText) this.orbText.innerText = "VOCALIZING RESPONSE...";
                break;

            default:
                if (this.orbText) this.orbText.innerText = label || "AEGIS SUPERVISED • READY";
                break;
        }
    }

    playUiSound(type = "click") {
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);

            if (type === "approve") {
                osc.frequency.setValueAtTime(440, ctx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.15);
                gain.gain.setValueAtTime(0.1, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.15);
                osc.start();
                osc.stop(ctx.currentTime + 0.15);
            } else if (type === "alert") {
                osc.type = "sawtooth";
                osc.frequency.setValueAtTime(300, ctx.currentTime);
                osc.frequency.setValueAtTime(220, ctx.currentTime + 0.1);
                gain.gain.setValueAtTime(0.12, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.25);
                osc.start();
                osc.stop(ctx.currentTime + 0.25);
            }
        } catch (e) {
            // AudioContext not allowed before user gesture
        }
    }
}

window.aegisVisualizer = new VisualizerManager();
