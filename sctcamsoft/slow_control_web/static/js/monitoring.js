/**
 * Monitoring Module
 * Handles real-time monitoring with Plotly.js (time-series) and Chart.js (gauges)
 * Now includes simulation mode for testing
 */

class MonitoringCharts {
    constructor() {
        this.tempData = { x: [], y: [] };
        this.voltageData = { x: [], y: [] };
        this.currentData = { x: [], y: [] };
        this.maxDataPoints = 100; // Keep last 100 points
        
        this.gauges = {};
        this.simulationMode = false;
        this.simulationInterval = null;
        this.simulationTime = 0;
        
        this.initializePlots();
        this.initializeGauges();
    }

    /**
     * Initialize Plotly time-series plots
     */
    initializePlots() {
        // Temperature plot
        const tempTrace = {
            x: [],
            y: [],
            mode: 'lines',
            name: 'Temperature',
            line: { color: '#ff6b6b', width: 2 }
        };
        
        const tempLayout = {
            title: 'Temperature vs Time',
            xaxis: { 
                title: 'Time',
                type: 'date'
            },
            yaxis: { 
                title: 'Temperature (°C)',
                range: [-20, 30]
            },
            paper_bgcolor: '#1e1e1e',
            plot_bgcolor: '#2d2d2d',
            font: { color: '#e0e0e0' },
            margin: { t: 40, r: 20, b: 40, l: 60 }
        };
        
        Plotly.newPlot('tempPlot', [tempTrace], tempLayout, {
            responsive: true,
            displayModeBar: false
        });

        // Power plot (voltage and current)
        const voltageTrace = {
            x: [],
            y: [],
            mode: 'lines',
            name: 'Voltage',
            line: { color: '#4ecdc4', width: 2 },
            yaxis: 'y'
        };
        
        const currentTrace = {
            x: [],
            y: [],
            mode: 'lines',
            name: 'Current',
            line: { color: '#ffe66d', width: 2 },
            yaxis: 'y2'
        };
        
        const powerLayout = {
            title: 'Voltage & Current vs Time',
            xaxis: { 
                title: 'Time',
                type: 'date'
            },
            yaxis: { 
                title: 'Voltage (V)',
                titlefont: { color: '#4ecdc4' },
                tickfont: { color: '#4ecdc4' },
                range: [0, 12]
            },
            yaxis2: {
                title: 'Current (A)',
                titlefont: { color: '#ffe66d' },
                tickfont: { color: '#ffe66d' },
                overlaying: 'y',
                side: 'right',
                range: [0, 5]
            },
            paper_bgcolor: '#1e1e1e',
            plot_bgcolor: '#2d2d2d',
            font: { color: '#e0e0e0' },
            margin: { t: 40, r: 60, b: 40, l: 60 },
            legend: { x: 0.5, y: 1.1, orientation: 'h' }
        };
        
        Plotly.newPlot('powerPlot', [voltageTrace, currentTrace], powerLayout, {
            responsive: true,
            displayModeBar: false
        });
    }

    /**
     * Initialize Chart.js gauge charts
     */
    initializeGauges() {
        // Temperature gauge
        this.gauges.temperature = this.createGauge('tempGauge', {
            min: -20,
            max: 30,
            label: '°C',
            color: '#ff6b6b',
            warningThreshold: 20,
            dangerThreshold: 25
        });

        // Voltage gauge
        this.gauges.voltage = this.createGauge('voltageGauge', {
            min: 0,
            max: 12,
            label: 'V',
            color: '#4ecdc4',
            warningThreshold: 10,
            dangerThreshold: 11
        });

        // Current gauge
        this.gauges.current = this.createGauge('currentGauge', {
            min: 0,
            max: 5,
            label: 'A',
            color: '#ffe66d',
            warningThreshold: 4,
            dangerThreshold: 4.5
        });
    }

    /**
     * Create a gauge chart
     * @param {string} canvasId - Canvas element ID
     * @param {Object} config - Gauge configuration
     * @returns {Chart} Chart.js instance
     */
    createGauge(canvasId, config) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        return new Chart(ctx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [0, config.max],
                    backgroundColor: [
                        config.color,
                        '#3a3a3a'
                    ],
                    borderWidth: 0,
                    circumference: 180,
                    rotation: 270
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                }
            }
        });
    }

    /**
     * Update gauge value
     * @param {string} gaugeName - Name of gauge (temperature, voltage, current)
     * @param {number} value - New value
     */
    updateGauge(gaugeName, value) {
        const gauge = this.gauges[gaugeName];
        if (!gauge) return;

        const config = {
            temperature: { min: -20, max: 30, unit: '°C' },
            voltage: { min: 0, max: 12, unit: 'V' },
            current: { min: 0, max: 5, unit: 'A' }
        }[gaugeName];

        if (!config) return;

        // Clamp value to range
        const clampedValue = Math.max(config.min, Math.min(config.max, value));
        const percentage = (clampedValue - config.min) / (config.max - config.min) * config.max;

        // Update chart
        gauge.data.datasets[0].data = [percentage, config.max - percentage];
        gauge.update('none'); // Update without animation

        // Update display value
        const valueElement = document.getElementById(`${gaugeName}Value`);
        if (valueElement) {
            valueElement.textContent = `${value.toFixed(2)} ${config.unit}`;
        }
    }

    /**
     * Add data point to time-series plot
     * @param {string} plotName - Plot name (temp, voltage, current)
     * @param {number} value - Data value
     * @param {Date} timestamp - Optional timestamp (defaults to now)
     */
    addDataPoint(plotName, value, timestamp = new Date()) {
        const dataObj = this[`${plotName}Data`];
        if (!dataObj) return;

        // Add new point
        dataObj.x.push(timestamp);
        dataObj.y.push(value);

        // Trim old data
        if (dataObj.x.length > this.maxDataPoints) {
            dataObj.x.shift();
            dataObj.y.shift();
        }

        // Update plot
        this.updatePlot(plotName);
    }

    /**
     * Update Plotly plot with new data
     * @param {string} plotName - Plot name
     */
    updatePlot(plotName) {
        if (plotName === 'temp') {
            Plotly.update('tempPlot', {
                x: [this.tempData.x],
                y: [this.tempData.y]
            }, {}, [0]);
        } else if (plotName === 'voltage') {
            Plotly.update('powerPlot', {
                x: [this.voltageData.x],
                y: [this.voltageData.y]
            }, {}, [0]);
        } else if (plotName === 'current') {
            Plotly.update('powerPlot', {
                x: [this.currentData.x],
                y: [this.currentData.y]
            }, {}, [1]);
        }
    }

    /**
     * Update all monitoring displays with device data
     * @param {Object} deviceData - Device data from server
     */
    updateFromDeviceData(deviceData) {
        const timestamp = new Date();

        // Update temperature
        if (deviceData.temperature !== undefined) {
            this.updateGauge('temperature', deviceData.temperature);
            this.addDataPoint('temp', deviceData.temperature, timestamp);
        }

        // Update voltage
        if (deviceData.voltage !== undefined) {
            this.updateGauge('voltage', deviceData.voltage);
            this.addDataPoint('voltage', deviceData.voltage, timestamp);
        }

        // Update current
        if (deviceData.current !== undefined) {
            this.updateGauge('current', deviceData.current);
            this.addDataPoint('current', deviceData.current, timestamp);
        }
    }

    /**
     * Toggle simulation mode
     */
    toggleSimulation() {
        this.simulationMode = !this.simulationMode;
        
        const btn = document.getElementById('monitoringSimBtn');
        const indicator = document.getElementById('monitoringSimIndicator');
        
        if (this.simulationMode) {
            btn.textContent = 'Disable Simulation';
            btn.classList.add('active');
            indicator.style.display = 'inline-block';
            this.startSimulation();
        } else {
            btn.textContent = 'Enable Simulation';
            btn.classList.remove('active');
            indicator.style.display = 'none';
            this.stopSimulation();
        }
    }

    /**
     * Start simulation mode
     */
    startSimulation() {
        this.simulationTime = 0;
        this.simulationInterval = setInterval(() => {
            this.simulationTime += 0.5;
            const data = this.generateSimulationData();
            this.updateFromDeviceData(data);
        }, 500); // Update twice per second
    }

    /**
     * Stop simulation mode
     */
    stopSimulation() {
        if (this.simulationInterval) {
            clearInterval(this.simulationInterval);
            this.simulationInterval = null;
        }
    }

    /**
     * Generate simulated sensor data
     * @returns {Object} Simulated data
     */
    generateSimulationData() {
        // Generate realistic-looking sensor data with trends and noise
        const temp = 20 + Math.sin(this.simulationTime * 0.1) * 5 + (Math.random() - 0.5) * 2;
        const voltage = 5.0 + Math.sin(this.simulationTime * 0.15) * 0.5 + (Math.random() - 0.5) * 0.2;
        const current = 2.5 + Math.cos(this.simulationTime * 0.12) * 1.0 + (Math.random() - 0.5) * 0.3;
        
        return {
            temperature: temp,
            voltage: voltage,
            current: current
        };
    }
}

// Initialize monitoring
let monitoring;

function initMonitoring() {
    monitoring = new MonitoringCharts();
}

function toggleMonitoringSimulation() {
    if (!monitoring) return;
    monitoring.toggleSimulation();
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMonitoring);
} else {
    initMonitoring();
}

// Export for use in main app
window.monitoring = monitoring;
