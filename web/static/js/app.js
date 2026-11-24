/**
 * AEGIS Master Application Controller
 * Handles user interactions, REST APIs, Approval Modals, Neural Vision triggers, and Multimodal Canvas state.
 */

class AegisApp {
    constructor() {
        this.sessionId = "aegis_session_" + Math.random().toString(36).substring(2, 7);
        this.chatViewport = document.getElementById("chatViewport");
        this.promptInput = document.getElementById("userInputPrompt");
        this.btnSend = document.getElementById("btnSendPrompt");
        this.fileInput = document.getElementById("imageFileInput");
        this.currentPendingActionId = null;

        this.init();
    }

    init() {
        this.startClock();
        this.bindGlobalEvents();
        this.loadAuditLogs();
        this.loadRulesAndVault();
        this.loadWorkspaceFiles();
    }

    startClock() {
        const clockElem = document.getElementById("liveClock");
        const update = () => {
            if (clockElem) {
                const now = new Date();
                clockElem.innerText = now.toTimeString().split(" ")[0];
            }
        };
        setInterval(update, 1000);
        update();
    }

    bindGlobalEvents() {
        // Send button and Enter key
        if (this.btnSend) {
            this.btnSend.addEventListener("click", () => this.handleSend());
        }

        if (this.promptInput) {
            this.promptInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    this.handleSend();
                }
            });
        }

        // File upload input
        if (this.fileInput) {
            this.fileInput.addEventListener("change", (e) => {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = (event) => {
                        this.handleSend("Analyze this uploaded image and identify all objects.", event.target.result);
                    };
                    reader.readAsDataURL(file);
                }
            });
        }

        // Tab Switching
        document.querySelectorAll(".tab-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const tabId = btn.getAttribute("data-tab");
                this.switchTab(tabId);
            });
        });

        // Modals
        this.bindModalEvents();
    }

    bindModalEvents() {
        // Approval Modal Buttons
        const btnApprove = document.getElementById("btnApproveAction");
        const btnReject = document.getElementById("btnRejectAction");
        if (btnApprove) btnApprove.addEventListener("click", () => this.resolveApproval(true));
        if (btnReject) btnReject.addEventListener("click", () => this.resolveApproval(false));

        // Settings Modal
        const btnSettings = document.getElementById("btnSettingsModal");
        const modalSettings = document.getElementById("settingsModal");
        const btnCloseSettings = document.getElementById("btnCloseSettings");
        const btnSaveSettings = document.getElementById("btnSaveSettings");

        if (btnSettings && modalSettings) {
            btnSettings.addEventListener("click", () => modalSettings.classList.add("show"));
            if (btnCloseSettings) btnCloseSettings.addEventListener("click", () => modalSettings.classList.remove("show"));
            if (btnSaveSettings) {
                btnSaveSettings.addEventListener("click", async () => {
                    const mode = document.getElementById("settingSupervisionMode").value;
                    const name = document.getElementById("settingUserName").value;
                    const provider = document.getElementById("settingModelProvider").value;
                    const apiKey = document.getElementById("settingApiKey").value;

                    await fetch("/api/profile", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ supervision_mode: mode, name: name })
                    });

                    if (apiKey) {
                        await fetch("/api/settings/apikey", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ provider: provider, key: apiKey })
                        });
                    }

                    document.getElementById("currentSupervisionMode").innerText = mode;
                    modalSettings.classList.remove("show");
                    this.appendMessage("assistant", `Settings updated. Active mode: **${mode}**.`);
                });
            }
        }

        // Add Rule Modal
        const btnAddRule = document.getElementById("btnAddRuleModal");
        const modalRule = document.getElementById("newRuleModal");
        const btnCloseRule = document.getElementById("btnCloseRuleModal");
        const btnSaveRule = document.getElementById("btnSaveNewRule");

        if (btnAddRule && modalRule) {
            btnAddRule.addEventListener("click", () => modalRule.classList.add("show"));
            if (btnCloseRule) btnCloseRule.addEventListener("click", () => modalRule.classList.remove("show"));
            if (btnSaveRule) {
                btnSaveRule.addEventListener("click", async () => {
                    const name = document.getElementById("ruleNameInput").value;
                    const text = document.getElementById("ruleTextInput").value;
                    const risk = document.getElementById("ruleRiskOverride").value;

                    if (!text) return alert("Rule text is required.");

                    await fetch("/api/rules", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ name: name, rule_text: text, risk_override: risk })
                    });

                    modalRule.classList.remove("show");
                    this.loadRulesAndVault();
                    this.appendMessage("assistant", `New safety policy registered: **${name}** (Risk: ${risk}).`);
                });
            }
        }

        // Refresh Files button
        const btnRefreshFiles = document.getElementById("btnRefreshFiles");
        if (btnRefreshFiles) {
            btnRefreshFiles.addEventListener("click", () => this.loadWorkspaceFiles());
        }

        // System Info button
        const btnSys = document.getElementById("btnSystemInfo");
        if (btnSys) {
            btnSys.addEventListener("click", () => this.handleSend("Show system telemetry status"));
        }

        // Audit Filter
        const filterSelect = document.getElementById("auditRiskFilter");
        if (filterSelect) {
            filterSelect.addEventListener("change", (e) => this.loadAuditLogs(e.target.value));
        }
    }

    switchTab(tabId) {
        document.querySelectorAll(".tab-btn").forEach(btn => {
            btn.classList.toggle("active", btn.getAttribute("data-tab") === tabId);
        });
        document.querySelectorAll(".tab-content").forEach(content => {
            content.classList.toggle("active", content.id === `tab-${tabId}`);
        });

        // Trigger refreshes if needed
        if (tabId === "audit") this.loadAuditLogs();
        if (tabId === "workspace") this.loadWorkspaceFiles();
        if (tabId === "rules") this.loadRulesAndVault();
    }

    updatePipelineNodes(stage, durationMs = 0) {
        const nodes = ["nodeInput", "nodeIntent", "nodeMemory", "nodeReasoning", "nodeSupervision", "nodeAction", "nodeAudit"];
        nodes.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.className = "p-node";
        });

        const activeCount = {
            "input": 1, "intent": 2, "context": 3, "reasoning": 4, "supervision": 5, "action": 6, "audit": 7
        }[stage] || 1;

        for (let i = 0; i < activeCount; i++) {
            const el = document.getElementById(nodes[i]);
            if (el) {
                if (i === activeCount - 1) el.classList.add("active");
                else el.classList.add("done");
            }
        }

        const timer = document.getElementById("pipelineDuration");
        if (timer) timer.innerText = `Latency: ${durationMs} ms`;
    }

    async handleSend(customPrompt = null, imageData = null, detectedObjects = null) {
        const prompt = customPrompt || (this.promptInput ? this.promptInput.value.trim() : "");
        if (!prompt && !imageData && !detectedObjects) return;

        if (this.promptInput && !customPrompt) this.promptInput.value = "";

        // Stop previous speech on new user message (Kill feature)
        if (window.aegisVoice) {
            window.aegisVoice.killSpeech();
        }

        // Render user message card
        this.appendMessage("user", prompt);

        // Update orb and pipeline
        if (window.aegisVisualizer) window.aegisVisualizer.setState("thinking");
        this.updatePipelineNodes("reasoning");

        try {
            const resp = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    prompt: prompt,
                    session_id: this.sessionId,
                    image_data: imageData,
                    detected_objects: detectedObjects
                })
            });

            const data = await resp.json();
            if (data.error) {
                this.appendMessage("assistant", `⚠️ Error: ${data.error}`);
                if (window.aegisVisualizer) window.aegisVisualizer.setState("ready");
                return;
            }

            this.processEngineResponse(data);

        } catch (e) {
            this.appendMessage("assistant", `⚠️ Connection failed: ${e.message}`);
            if (window.aegisVisualizer) window.aegisVisualizer.setState("ready");
        }
    }

    async sendPromptWithVision(prompt, base64Image, detectedObjects) {
        this.switchTab("vision");
        await this.handleSend(prompt, base64Image, detectedObjects);
    }

    processEngineResponse(data) {
        this.updatePipelineNodes("audit", data.duration_ms || 0);

        // 1. Check if Action requires User Supervision Approval
        if (data.decision_state === "REQUEST_PERMISSION") {
            this.triggerApprovalModal(data);
            return;
        }

        // 2. Render Assistant response
        let extraWidgetHtml = "";
        if (data.action_result && data.action_result.visual_type === "youtube_player") {
            const songName = (data.action_result.data && data.action_result.data.song) ? data.action_result.data.song : "Music";
            const targetUrl = data.action_result.data ? (data.action_result.data.url || data.action_result.data.target_url) : "https://www.youtube.com";

            // Update floating HUD
            const hud = document.getElementById("floatingMediaHud");
            const hudTitle = document.getElementById("hudSongTitle");
            if (hud && hudTitle) {
                hudTitle.innerText = songName.toUpperCase();
                hud.style.display = "block";
            }

            extraWidgetHtml = `
                <div class="media-deck-card" style="margin: 12px 0; padding: 14px; background: rgba(10, 25, 47, 0.9); border: 1px solid var(--accent-cyan); border-radius: 10px; box-shadow: 0 4px 20px rgba(0, 240, 255, 0.2);">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; border-bottom: 1px solid rgba(0, 240, 255, 0.2); padding-bottom: 8px;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <i class="fa-solid fa-compact-disc fa-spin" style="color: var(--accent-cyan); font-size: 1.3rem;"></i>
                            <span style="font-weight: 700; color: #ffffff; font-size: 1rem; letter-spacing: 0.5px;">${songName.toUpperCase()}</span>
                        </div>
                        <span class="badge" style="background: rgba(0, 240, 255, 0.15); color: var(--accent-cyan); border: 1px solid var(--accent-cyan); font-size: 0.75rem; font-weight: bold;"><i class="fa-brands fa-youtube" style="color: #ff3333; margin-right: 4px;"></i> ACTIVE ON SCREEN</span>
                    </div>
                    <div style="color: var(--text-dim); font-size: 0.85rem; margin-bottom: 12px;">
                        <i class="fa-solid fa-check-circle" style="color: var(--accent-cyan);"></i> Opened in default browser. Control playback directly below:
                    </div>
                    <div class="media-control-bar" style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center;">
                        <button class="btn-sm btn-primary" onclick="controlMedia('pause')"><i class="fa-solid fa-pause"></i> Pause</button>
                        <button class="btn-sm btn-primary" onclick="controlMedia('resume')"><i class="fa-solid fa-play"></i> Resume</button>
                        <button class="btn-sm btn-outline" onclick="controlMedia('vol_down')" title="Volume Down"><i class="fa-solid fa-volume-low"></i> Vol -</button>
                        <button class="btn-sm btn-outline" onclick="controlMedia('vol_up')" title="Volume Up"><i class="fa-solid fa-volume-high"></i> Vol +</button>
                        <button class="btn-sm btn-outline" onclick="controlMedia('mute')"><i class="fa-solid fa-volume-xmark"></i> Mute</button>
                        <button class="btn-sm chip-danger" onclick="controlMedia('stop')"><i class="fa-solid fa-stop"></i> Stop</button>
                        <a href="${targetUrl}" target="_blank" class="btn-sm btn-outline" style="text-decoration: none; margin-left: auto;"><i class="fa-solid fa-arrow-up-right-from-square"></i> YouTube Window</a>
                    </div>
                </div>
            `;
        }

        this.appendMessage("assistant", data.output_text, data.supervision ? data.supervision.risk_level : "SAFE", extraWidgetHtml);

        // 3. Multimodal Canvas Updates
        if (data.action_result) {
            const ar = data.action_result;
            
            // Automatically open site / video in browser tab if URL provided
            if (ar.data && (ar.data.url || ar.data.target_url)) {
                const targetUrl = ar.data.url || ar.data.target_url;
                try {
                    window.open(targetUrl, "_blank");
                } catch (err) {
                    console.warn("[Window Open Blocked by Browser]:", err);
                }
            }

            if (ar.visual_type === "mermaid" && ar.data) {
                this.switchTab("blueprints");
                if (window.aegisMermaid) window.aegisMermaid.render(ar.data.code, ar.data.title);
            } else if (ar.visual_type === "chart" && ar.data) {
                this.switchTab("analytics");
                if (window.aegisChart) window.aegisChart.render(ar.data);
            }
        }

        // 4. Vision result updates in Vision Tab
        if (data.vision_result) {
            const resBox = document.getElementById("visionResultsBox");
            if (resBox) {
                const parsedVision = (window.marked && typeof marked.parse === "function") ? marked.parse(data.vision_result.analysis) : data.vision_result.analysis;
                resBox.innerHTML = `
                    <div class="vision-live-result">
                        ${parsedVision}
                        <div class="vision-meta-tag">Sensor: ${data.vision_result.source} | Resolution: ${data.vision_result.dimensions}</div>
                    </div>
                `;
            }
        }

        // 5. Vocalize output if enabled
        if (window.aegisVoice && data.output_text) {
            window.aegisVoice.speak(data.output_text);
        }

        // Refresh audit logs
        this.loadAuditLogs();
        this.loadWorkspaceFiles();
    }

    triggerApprovalModal(data) {
        this.currentPendingActionId = data.execution_id;
        const modal = document.getElementById("approvalModal");
        if (!modal) return;

        if (window.aegisVisualizer) {
            window.aegisVisualizer.setState("supervising");
            window.aegisVisualizer.playUiSound("alert");
        }

        // Populate modal data
        const risk = data.supervision.risk_level || "CRITICAL";
        const badge = document.getElementById("modalRiskBadge");
        if (badge) {
            badge.innerText = risk;
            badge.className = `risk-badge risk-${risk}`;
        }

        document.getElementById("modalActionType").innerText = data.intent.action_type || "unspecified";
        document.getElementById("modalTarget").innerText = data.supervision.blast_radius.target || "Workspace";
        document.getElementById("modalReasonText").innerText = data.reasoning.explanation || data.supervision.reason;
        document.getElementById("modalBlastRadius").innerText = data.supervision.blast_radius.impact_summary || "Permanent change.";

        modal.classList.add("show");

        // Also add preview card to chat
        this.appendMessage("assistant", data.output_text, risk);
    }

    async resolveApproval(approved) {
        const modal = document.getElementById("approvalModal");
        if (modal) modal.classList.remove("show");

        if (!this.currentPendingActionId) return;

        if (window.aegisVisualizer) {
            window.aegisVisualizer.playUiSound(approved ? "approve" : "alert");
            window.aegisVisualizer.setState("thinking");
        }

        try {
            const resp = await fetch("/api/approve", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    action_id: this.currentPendingActionId,
                    approved: approved,
                    session_id: this.sessionId
                })
            });

            const data = await resp.json();
            this.appendMessage("assistant", data.message, approved ? "SAFE" : "CRITICAL");

            // Open URL if approved action was open/play
            if (approved && data.action_result && data.action_result.data && (data.action_result.data.url || data.action_result.data.target_url)) {
                const targetUrl = data.action_result.data.url || data.action_result.data.target_url;
                window.open(targetUrl, "_blank");
            }

            if (window.aegisVoice) {
                window.aegisVoice.speak(data.message);
            }

            // Refresh views
            this.loadAuditLogs();
            this.loadWorkspaceFiles();
            if (window.aegisVisualizer) window.aegisVisualizer.setState("ready");

        } catch (e) {
            this.appendMessage("assistant", `Failed to resolve approval: ${e.message}`);
        } finally {
            this.currentPendingActionId = null;
        }
    }

    appendMessage(role, text, riskLevel = null, extraHtml = "") {
        if (!this.chatViewport) return;

        const card = document.createElement("div");
        card.className = `message-card ${role}-card`;

        let headerHtml = "";
        if (role === "user") {
            headerHtml = `<div class="msg-header"><i class="fa-solid fa-user-astronaut"></i> EXECUTIVE</div>`;
        } else if (role === "assistant") {
            const badgeHtml = riskLevel ? `<span class="risk-badge risk-${riskLevel}">${riskLevel}</span>` : "";
            headerHtml = `<div class="msg-header"><span><i class="fa-solid fa-shield-halved"></i> AEGIS</span> ${badgeHtml}</div>`;
        }

        const parsedContent = (window.marked && typeof marked.parse === "function") ? marked.parse(text) : text;

        card.innerHTML = `
            ${headerHtml}
            <div class="msg-body">${parsedContent} ${extraHtml}</div>
        `;

        this.chatViewport.appendChild(card);
        this.chatViewport.scrollTop = this.chatViewport.scrollHeight;
    }

    async loadAuditLogs(riskFilter = "") {
        try {
            const url = riskFilter ? `/api/audit-logs?risk=${riskFilter}` : `/api/audit-logs`;
            const resp = await fetch(url);
            const data = await resp.json();

            // Update metrics
            if (data.metrics) {
                const m = data.metrics;
                document.getElementById("metricTotal").innerText = m.total_actions || 0;
                document.getElementById("metricApproved").innerText = m.approved_count || 0;
                document.getElementById("metricRejected").innerText = m.rejected_count || 0;
                document.getElementById("metricBlocked").innerText = m.safety_blocked_count || 0;
            }

            // Populate table
            const tbody = document.getElementById("auditTableBody");
            if (!tbody) return;
            tbody.innerHTML = "";

            if (!data.logs || data.logs.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-dim);">No action history recorded yet.</td></tr>`;
                return;
            }

            data.logs.forEach(log => {
                const tr = document.createElement("tr");
                const cleanPrompt = (log.user_prompt || "").substring(0, 30);
                tr.innerHTML = `
                    <td>${log.timestamp.split(" ")[1] || log.timestamp}</td>
                    <td title="${log.user_prompt}">${cleanPrompt}...</td>
                    <td><span class="risk-badge risk-${log.risk_level}">${log.risk_level}</span></td>
                    <td>${log.user_approval_status}</td>
                    <td><code>${log.executed_action}</code></td>
                    <td><code>${log.execution_hash || '---'}</code></td>
                `;
                tbody.appendChild(tr);
            });

        } catch (e) {
            console.warn("[Audit Log Load Error]:", e);
        }
    }

    async loadRulesAndVault() {
        try {
            // Load Rules
            const rulesResp = await fetch("/api/rules");
            const rulesData = await rulesResp.json();
            const rulesCont = document.getElementById("rulesListContainer");
            if (rulesCont && rulesData.rules) {
                rulesCont.innerHTML = "";
                rulesData.rules.forEach(r => {
                    const card = document.createElement("div");
                    card.className = "rule-card";
                    card.innerHTML = `
                        <div>
                            <div class="r-name">${r.name} <span class="risk-badge risk-${r.risk_override || 'HIGH'}">${r.risk_override || 'HIGH'}</span></div>
                            <div class="r-text">${r.rule_text}</div>
                        </div>
                        <button class="btn-sm" onclick="toggleRuleStatus(${r.id}, ${r.is_active ? 0 : 1})">
                            ${r.is_active ? '<i class="fa-solid fa-check text-success"></i> Active' : '<i class="fa-solid fa-ban text-dim"></i> Disabled'}
                        </button>
                    `;
                    rulesCont.appendChild(card);
                });
            }

            // Load Knowledge Vault
            const vaultResp = await fetch("/api/knowledge");
            const vaultData = await vaultResp.json();
            const vaultCont = document.getElementById("vaultListContainer");
            if (vaultCont && vaultData.knowledge) {
                vaultCont.innerHTML = "";
                vaultData.knowledge.forEach(k => {
                    const card = document.createElement("div");
                    card.className = "vault-card";
                    card.innerHTML = `
                        <div>
                            <div class="r-name">${k.topic}</div>
                            <div class="r-text">${k.fact_content}</div>
                        </div>
                        <span class="badge" style="font-size: 0.65rem; color: var(--text-dim);">${k.category}</span>
                    `;
                    vaultCont.appendChild(card);
                });
            }

        } catch (e) {
            console.warn("[Rules/Vault Load Error]:", e);
        }
    }

    async loadWorkspaceFiles() {
        try {
            const resp = await fetch("/api/files");
            const data = await resp.json();
            const grid = document.getElementById("workspaceFilesGrid");
            if (!grid) return;
            grid.innerHTML = "";

            if (!data.files || data.files.length === 0) {
                grid.innerHTML = `<div style="grid-column: span 3; text-align: center; color: var(--text-dim); padding: 20px;">Workspace directory is empty.</div>`;
                return;
            }

            data.files.forEach(f => {
                const card = document.createElement("div");
                card.className = "file-item-card";
                let iconClass = "fa-file-lines";
                if (f.extension === ".md") iconClass = "fa-file-code";
                if (f.extension === ".py") iconClass = "fa-file-code text-warning";
                if (f.extension === ".json") iconClass = "fa-file-lines text-success";

                card.innerHTML = `
                    <i class="fa-solid ${iconClass}"></i>
                    <div class="f-name">${f.name}</div>
                    <div class="f-size">${f.size} bytes</div>
                `;
                grid.appendChild(card);
            });

        } catch (e) {
            console.warn("[Workspace Files Load Error]:", e);
        }
    }
}

// Global Quick Action Helper for SIH Demos
window.executeQuickPrompt = function(promptText) {
    if (window.aegisApp) {
        window.aegisApp.handleSend(promptText);
    }
};

window.controlMedia = async function(command) {
    try {
        const resp = await fetch("/api/media/control", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ command: command })
        });
        const data = await resp.json();
        if (window.aegisVisualizer) {
            window.aegisVisualizer.playUiSound("click");
            window.aegisVisualizer.flashStatus("MEDIA: " + command.toUpperCase());
        }
        if (command === "stop") {
            const hud = document.getElementById("floatingMediaHud");
            if (hud) hud.style.display = "none";
        }
    } catch (e) {
        console.warn("[Media Control Error]:", e);
    }
};

window.toggleRuleStatus = async function(ruleId, newStatus) {
    await fetch(`/api/rules/${ruleId}/toggle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: Boolean(newStatus) })
    });
    if (window.aegisApp) window.aegisApp.loadRulesAndVault();
};

document.addEventListener("DOMContentLoaded", () => {
    window.aegisApp = new AegisApp();
});
