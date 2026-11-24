/**
 * AEGIS Mermaid.js Blueprint Renderer
 */

class MermaidViewer {
    constructor() {
        this.container = document.getElementById("mermaidContainer");
        this.titleElem = document.getElementById("blueprintTitle");
        this.btnCopy = document.getElementById("btnDownloadBlueprint");
        this.currentCode = "";

        this.init();
    }

    init() {
        if (window.mermaid) {
            mermaid.initialize({
                startOnLoad: true,
                theme: 'dark',
                securityLevel: 'loose',
                themeVariables: {
                    darkMode: true,
                    background: '#060911',
                    primaryColor: '#00f0ff',
                    primaryTextColor: '#f1f5f9',
                    primaryBorderColor: '#00f0ff',
                    lineColor: '#38bdf8',
                    secondaryColor: '#8b5cf6',
                    tertiaryColor: '#1e293b'
                }
            });
        }

        if (this.btnCopy) {
            this.btnCopy.addEventListener("click", () => {
                if (this.currentCode) {
                    navigator.clipboard.writeText(this.currentCode);
                    this.btnCopy.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
                    setTimeout(() => {
                        this.btnCopy.innerHTML = '<i class="fa-solid fa-copy"></i> Copy Code';
                    }, 2000);
                }
            });
        }
    }

    async render(code, title = "System Architectural Blueprint") {
        if (!this.container) return;
        this.currentCode = code;

        if (this.titleElem) {
            this.titleElem.innerHTML = `<i class="fa-solid fa-sitemap"></i> ${title}`;
        }

        try {
            const id = "mermaid_" + Math.random().toString(36).substring(2, 9);
            const { svg } = await mermaid.render(id, code);
            this.container.innerHTML = svg;
        } catch (e) {
            console.warn("[Mermaid Render Error]:", e);
            this.container.innerHTML = `<pre class="mermaid">${code}</pre>`;
        }
    }
}

window.aegisMermaid = new MermaidViewer();
