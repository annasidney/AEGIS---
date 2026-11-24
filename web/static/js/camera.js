/**
 * AEGIS Multimodal Vision & Neural Object Tracking Controller
 * Real-Time Browser-based COCO-SSD Deep Learning Object Detection (WebGL accelerated).
 */

class CameraController {
    constructor() {
        this.video = document.getElementById("webcamVideo");
        this.overlayCanvas = document.getElementById("detectionOverlayCanvas");
        this.captureCanvas = document.getElementById("captureCanvas");
        this.btnToggle = document.getElementById("btnToggleWebcam");
        this.btnAskView = document.getElementById("btnAskAboutView");
        this.btnSnap = document.getElementById("btnCameraSnap");
        this.hudBar = document.getElementById("visionHudBar");
        this.hudList = document.getElementById("hudDetectedList");
        this.overlayText = document.getElementById("webcamOverlay");
        this.resultsBox = document.getElementById("visionResultsBox");

        this.stream = null;
        this.isStreaming = false;
        this.cocoModel = null;
        this.isDetecting = false;
        this.currentDetectedObjects = [];

        this.init();
    }

    async init() {
        if (this.btnToggle) {
            this.btnToggle.addEventListener("click", () => this.toggleWebcam());
        }
        if (this.btnAskView) {
            this.btnAskView.addEventListener("click", () => this.askAboutCurrentView());
        }
        if (this.btnSnap) {
            this.btnSnap.addEventListener("click", () => this.triggerQuickSnapshot());
        }

        // Lazy load COCO-SSD model in background
        this.loadCocoModel();
    }

    async loadCocoModel() {
        if (window.cocoSsd) {
            try {
                console.log("[AEGIS Vision] Initializing Neural Object Detector...");
                this.cocoModel = await cocoSsd.load();
                console.log("[AEGIS Vision] COCO-SSD Neural Model Active!");
            } catch (err) {
                console.warn("[AEGIS Vision] COCO-SSD load warning:", err);
            }
        }
    }

    async toggleWebcam() {
        if (this.isStreaming) {
            this.stopWebcam();
        } else {
            await this.startWebcam();
        }
    }

    async startWebcam() {
        try {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                alert("Camera access is not supported by your browser.");
                return;
            }

            this.overlayText.innerText = "Initializing Optical Sensors...";
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
                audio: false
            });

            this.video.srcObject = this.stream;
            await this.video.play();

            this.isStreaming = true;
            this.overlayText.style.display = "none";
            this.btnToggle.innerHTML = '<i class="fa-solid fa-video-slash"></i> Stop Camera';
            this.btnToggle.classList.add("btn-danger");
            if (this.hudBar) this.hudBar.style.display = "flex";

            // Start object detection loop
            this.isDetecting = true;
            this.startDetectionLoop();

            if (window.visualizer) {
                window.visualizer.setState("camera");
            }
        } catch (err) {
            console.error("[Camera Error]:", err);
            this.overlayText.innerText = `Camera Access Denied: ${err.message}`;
        }
    }

    stopWebcam() {
        this.isDetecting = false;
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        if (this.video) {
            this.video.srcObject = null;
        }
        this.isStreaming = false;
        this.overlayText.style.display = "flex";
        this.overlayText.innerText = "Camera Standby (Click 'Start Webcam')";
        this.btnToggle.innerHTML = '<i class="fa-solid fa-video"></i> Start Webcam';
        this.btnToggle.classList.remove("btn-danger");
        if (this.hudBar) this.hudBar.style.display = "none";

        // Clear canvas
        if (this.overlayCanvas) {
            const ctx = this.overlayCanvas.getContext("2d");
            ctx.clearRect(0, 0, this.overlayCanvas.width, this.overlayCanvas.height);
        }

        if (window.visualizer) {
            window.visualizer.setState("idle");
        }
    }

    async startDetectionLoop() {
        if (!this.overlayCanvas || !this.video) return;

        const ctx = this.overlayCanvas.getContext("2d");

        const detectFrame = async () => {
            if (!this.isStreaming || !this.isDetecting) return;

            // Match canvas coordinates to video stream
            if (this.video.videoWidth > 0 && this.overlayCanvas.width !== this.video.videoWidth) {
                this.overlayCanvas.width = this.video.videoWidth;
                this.overlayCanvas.height = this.video.videoHeight;
            }

            ctx.clearRect(0, 0, this.overlayCanvas.width, this.overlayCanvas.height);

            if (this.cocoModel && this.video.readyState === 4) {
                try {
                    const predictions = await this.cocoModel.detect(this.video);
                    this.currentDetectedObjects = predictions;

                    // Draw bounding boxes and HUD tags
                    predictions.forEach(prediction => {
                        const [x, y, width, height] = prediction.bbox;
                        const label = prediction.class.toUpperCase();
                        const confidence = Math.round(prediction.score * 100);

                        // Bounding Box (Neon Cyber Cyan)
                        ctx.strokeStyle = "#00f0ff";
                        ctx.lineWidth = 3;
                        ctx.shadowColor = "#00f0ff";
                        ctx.shadowBlur = 10;
                        ctx.strokeRect(x, y, width, height);

                        // Corner Reticles
                        const rLen = Math.min(width, height) * 0.2;
                        ctx.strokeStyle = "#10b981";
                        ctx.lineWidth = 4;
                        // Top-left
                        ctx.beginPath();
                        ctx.moveTo(x, y + rLen); ctx.lineTo(x, y); ctx.lineTo(x + rLen, y);
                        ctx.stroke();

                        // Label Background Tag
                        ctx.fillStyle = "rgba(6, 9, 17, 0.85)";
                        ctx.shadowBlur = 0;
                        ctx.fillRect(x, y > 24 ? y - 24 : y, ctx.measureText(`${label} ${confidence}%`).width + 16, 22);

                        // Label Text
                        ctx.fillStyle = "#00f0ff";
                        ctx.font = "bold 12px 'Fira Code', monospace";
                        ctx.fillText(`${label} ${confidence}%`, x + 8, (y > 24 ? y - 8 : y + 16));
                    });

                    // Update HUD Bar Text
                    if (this.hudList) {
                        if (predictions.length > 0) {
                            const summary = predictions.map(p => `${p.class.toUpperCase()} (${Math.round(p.score * 100)}%)`).join(" • ");
                            this.hudList.innerText = summary;
                        } else {
                            this.hudList.innerText = "Active Scan: No target objects in focus";
                        }
                    }
                } catch (e) {
                    // Ignore frame drop
                }
            }

            requestAnimationFrame(detectFrame);
        };

        requestAnimationFrame(detectFrame);
    }

    captureFrameBase64() {
        if (!this.isStreaming || !this.video) return null;
        const canvas = this.captureCanvas || document.createElement("canvas");
        canvas.width = this.video.videoWidth || 640;
        canvas.height = this.video.videoHeight || 480;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(this.video, 0, 0, canvas.width, canvas.height);
        return canvas.toDataURL("image/jpeg", 0.85);
    }

    async askAboutCurrentView() {
        if (!this.isStreaming) {
            await this.startWebcam();
            // Wait brief moment for detection
            await new Promise(r => setTimeout(r, 1200));
        }

        const b64 = this.captureFrameBase64();
        const detected = this.currentDetectedObjects;

        // Switch tab to conversation or show prompt
        const prompt = "What do you see in the camera view right now?";
        if (window.aegisApp) {
            window.aegisApp.sendPromptWithVision(prompt, b64, detected);
        }
    }

    async triggerQuickSnapshot() {
        if (!this.isStreaming) {
            await this.startWebcam();
            return;
        }
        this.askAboutCurrentView();
    }
}

// Instantiate on window
window.addEventListener("DOMContentLoaded", () => {
    window.cameraController = new CameraController();
});
