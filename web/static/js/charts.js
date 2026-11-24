/**
 * AEGIS Dynamic Chart.js Controller
 */

class ChartViewer {
    constructor() {
        this.canvas = document.getElementById("aegisLiveChart");
        this.titleElem = document.getElementById("chartTitle");
        this.chartInstance = null;
        this.initDefault();
    }

    initDefault() {
        if (!this.canvas || !window.Chart) return;

        const defaultData = {
            type: "bar",
            title: "Supervision Risk & Safety Capabilities",
            data: {
                labels: ["Zero-Trust", "Safety Checks", "Truth Check", "Memory Retrieval", "Blast Radius"],
                datasets: [{
                    label: "System Confidence (%)",
                    data: [98, 100, 95, 92, 99],
                    backgroundColor: [
                        "rgba(0, 240, 255, 0.7)",
                        "rgba(16, 185, 129, 0.7)",
                        "rgba(139, 92, 246, 0.7)",
                        "rgba(245, 158, 11, 0.7)",
                        "rgba(239, 68, 68, 0.7)"
                    ],
                    borderColor: "#00f0ff",
                    borderWidth: 1
                }]
            }
        };

        this.render(defaultData);
    }

    render(config) {
        if (!this.canvas || !window.Chart) return;

        if (this.titleElem && config.title) {
            this.titleElem.innerHTML = `<i class="fa-solid fa-chart-line"></i> ${config.title}`;
        }

        if (this.chartInstance) {
            this.chartInstance.destroy();
        }

        const ctx = this.canvas.getContext("2d");
        const chartType = config.chart_type || config.type || "bar";

        this.chartInstance = new Chart(ctx, {
            type: chartType,
            data: config.data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: "#94a3b8", font: { family: "Plus Jakarta Sans" } }
                    }
                },
                scales: chartType !== "doughnut" && chartType !== "pie" ? {
                    x: {
                        ticks: { color: "#94a3b8" },
                        grid: { color: "rgba(255, 255, 255, 0.05)" }
                    },
                    y: {
                        ticks: { color: "#94a3b8" },
                        grid: { color: "rgba(255, 255, 255, 0.05)" }
                    }
                } : {}
            }
        });
    }
}

window.aegisChart = new ChartViewer();
