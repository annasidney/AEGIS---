/**
 * AEGIS Voice Integration
 * Web Speech API with Push-To-Talk (PTT), Barge-in / Kill Speech, and Zero-Latency Synthesis.
 */

class VoiceController {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.isHoldingPTT = false;
        this.synth = window.speechSynthesis;
        this.ttsEnabled = true;

        this.btnMic = document.getElementById("btnVoiceToggle");
        this.btnKill = document.getElementById("btnKillSpeech");
        this.micIcon = document.getElementById("micIcon");
        this.statusMsg = document.getElementById("voiceStatusMsg");
        this.promptInput = document.getElementById("userInputPrompt");
        this.chkAudio = document.getElementById("chkAudioTTS");

        this.initRecognition();
        this.bindEvents();
    }

    initRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            if (this.statusMsg) this.statusMsg.innerText = "Web Speech API not supported in this browser.";
            return;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = "en-US";

        this.recognition.onstart = () => {
            this.isListening = true;
            if (this.btnMic) this.btnMic.classList.add("recording");
            if (this.statusMsg) this.statusMsg.innerText = "🎙️ Listening... (Speak clearly)";
            if (window.aegisVisualizer) window.aegisVisualizer.setState("listening");
        };

        this.recognition.onresult = (event) => {
            let interimTranscript = "";
            let finalTranscript = "";

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }

            if (this.promptInput) {
                this.promptInput.value = finalTranscript || interimTranscript;
            }

            // If not holding PTT and final recognized, or if speech says 'kill' / 'stop'
            const currentText = (finalTranscript || interimTranscript).toLowerCase().trim();
            if (currentText.includes("kill speech") || currentText.includes("stop talking") || currentText === "stop" || currentText === "shut up") {
                this.killSpeech();
                if (this.promptInput) this.promptInput.value = "";
                return;
            }
        };

        this.recognition.onerror = (event) => {
            if (event.error !== "no-speech") {
                console.warn("[SpeechRecognition Error]:", event.error);
            }
            this.stopListening();
        };

        this.recognition.onend = () => {
            this.stopListening();
        };
    }

    bindEvents() {
        // Kill Speech Button
        if (this.btnKill) {
            this.btnKill.addEventListener("click", () => this.killSpeech());
        }

        // Global Hotkeys: Escape or 'K' to KILL speech immediately
        window.addEventListener("keydown", (e) => {
            if (e.key === "Escape" || (e.key.toLowerCase() === "k" && document.activeElement !== this.promptInput)) {
                this.killSpeech();
            }

            // Push-To-Talk via Spacebar (when not typing in textarea)
            if (e.code === "Space" && document.activeElement !== this.promptInput && !this.isHoldingPTT) {
                e.preventDefault();
                this.isHoldingPTT = true;
                this.killSpeech(); // Stop speech when user talks
                this.startListening();
                if (this.btnMic) this.btnMic.classList.add("holding-talk");
                if (this.statusMsg) this.statusMsg.innerText = "🎙️ PUSH-TO-TALK (HOLDING SPACEBAR)...";
            }
        });

        window.addEventListener("keyup", (e) => {
            if (e.code === "Space" && this.isHoldingPTT) {
                e.preventDefault();
                this.isHoldingPTT = false;
                if (this.btnMic) this.btnMic.classList.remove("holding-talk");
                this.stopListening();

                // Auto-submit after release
                setTimeout(() => {
                    if (this.promptInput && this.promptInput.value.trim() && window.aegisApp) {
                        window.aegisApp.handleSend();
                    }
                }, 300);
            }
        });

        // Mouse / Touch Push-To-Talk on Mic Button
        if (this.btnMic) {
            const startPTT = (e) => {
                e.preventDefault();
                this.isHoldingPTT = true;
                this.killSpeech();
                this.startListening();
                this.btnMic.classList.add("holding-talk");
                if (this.statusMsg) this.statusMsg.innerText = "🎙️ PUSH-TO-TALK (HOLDING MIC)...";
            };

            const endPTT = (e) => {
                if (!this.isHoldingPTT) return;
                e.preventDefault();
                this.isHoldingPTT = false;
                this.btnMic.classList.remove("holding-talk");
                this.stopListening();

                setTimeout(() => {
                    if (this.promptInput && this.promptInput.value.trim() && window.aegisApp) {
                        window.aegisApp.handleSend();
                    }
                }, 300);
            };

            this.btnMic.addEventListener("mousedown", startPTT);
            this.btnMic.addEventListener("mouseup", endPTT);
            this.btnMic.addEventListener("mouseleave", endPTT);

            this.btnMic.addEventListener("touchstart", startPTT, { passive: false });
            this.btnMic.addEventListener("touchend", endPTT, { passive: false });
        }

        if (this.chkAudio) {
            this.chkAudio.addEventListener("change", (e) => {
                this.ttsEnabled = e.target.checked;
                if (!this.ttsEnabled) this.killSpeech();
            });
        }
    }

    startListening() {
        if (this.recognition && !this.isListening) {
            try {
                this.recognition.start();
            } catch (e) {}
        }
    }

    stopListening() {
        this.isListening = false;
        if (this.btnMic) {
            this.btnMic.classList.remove("recording");
            this.btnMic.classList.remove("holding-talk");
        }
        if (this.statusMsg) this.statusMsg.innerText = "Voice recognition standby";
        if (window.aegisVisualizer) window.aegisVisualizer.setState("ready");
        if (this.recognition) {
            try {
                this.recognition.stop();
            } catch (e) {}
        }
    }

    killSpeech() {
        // Immediate Frontend Silence
        if (this.synth) {
            this.synth.cancel();
        }

        // Notify Backend to Kill Any Active PowerShell/pyttsx3 TTS Process
        fetch("/api/voice/stop", { method: "POST" }).catch(() => {});

        if (window.aegisVisualizer) {
            window.aegisVisualizer.setState("ready");
        }

        if (this.statusMsg) {
            this.statusMsg.innerText = "🛑 Speech Interrupted / Silenced.";
            setTimeout(() => {
                if (this.statusMsg.innerText.includes("Silenced")) {
                    this.statusMsg.innerText = "Voice recognition standby";
                }
            }, 1800);
        }
    }

    speak(text) {
        if (!this.ttsEnabled || !this.synth) return;

        // Clean markdown, links, LaTeX formulas for natural pronunciation
        const clean = text
            .replace(/#{1,6}\s+/g, "")
            .replace(/\*\*(.*?)\*\*/g, "$1")
            .replace(/\*(.*?)\*/g, "$1")
            .replace(/`{1,3}[^`]*`{1,3}/g, "")
            .replace(/\[(.*?)\]\((.*?)\)/g, "$1")
            .replace(/https?:\/\/\S+/g, "")
            .replace(/\$\$.*?\$\$/gs, "equation")
            .substring(0, 450); // Read first 450 characters smoothly

        this.synth.cancel();
        const utterance = new SpeechSynthesisUtterance(clean);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;

        utterance.onstart = () => {
            if (window.aegisVisualizer) window.aegisVisualizer.setState("speaking");
        };

        utterance.onend = () => {
            if (window.aegisVisualizer) window.aegisVisualizer.setState("ready");
        };

        utterance.onerror = () => {
            if (window.aegisVisualizer) window.aegisVisualizer.setState("ready");
        };

        this.synth.speak(utterance);
    }
}

window.aegisVoice = new VoiceController();
