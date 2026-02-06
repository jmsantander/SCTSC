/**
 * Monitoring Module
 * 
 * Handles real-time monitoring visualization with:
 * - Plotly.js time-series charts (temperature, voltage, current history)
 * - Chart.js gauge displays (current readings)
 * - Simulation mode for testing without hardware
 * - Automatic data buffering and trimming
 * 
 * @module Monitoring
 * @requires plotly.js
 * @requires chart.js
 * @author SCT Camera Team
 * @version 1.0.0
 * 
 * @example
 * // Initialize monitoring
 * const monitoring = new MonitoringCharts();
 * 
 * // Update with device data
 * monitoring.updateFromDeviceData({
 *   temperature: 22.5,
 *   voltage: 5.0,
 *   current: 2.5
 * });
 * 
 * // Enable simulation
 * monitoring.toggleSimulation();
 */

/**
 * Main class for monitoring charts and gauges
 * 
 * Manages all monitoring visualizations including time-series plots
 * for historical data and gauge charts for current readings.
 */
class MonitoringCharts {
    /**
     * Create a monitoring charts instance
     * 
     * Initializes:
     * - Empty data buffers for time-series
     * - Plotly temperature and power plots
     * - Chart.js gauge displays
     * - Simulation timer (if enabled)
     */
    constructor() {
        // Time-series data buffers
        this.tempData = { x: [], y: [] };  // Temperature history
        this.voltageData = { x: [], y: [] };  // Voltage history
        this.currentData = { x: [], y: [] };  // Current history
        this.maxDataPoints = 100;  // Keep last 100 points (prevents memory growth)
        
        // Gauge chart instances (Chart.js)
        this.gauges = {};
        
        // Simulation control
        this.simulationMode = false;  // Whether simulation is active
        this.simulationInterval = null;  // Interval timer for updates
        this.simulationTime = 0;  // Elapsed simulation time (seconds)
        
        // Initialize all charts
        this.initializePlots();
        this.initializeGauges();
    }

    /**
     * Initialize Plotly time-series plots
     * 
     * Creates two plots:
     * 1. Temperature vs Time - Single trace showing temperature history
     * 2. Voltage & Current vs Time - Dual Y-axis plot for power monitoring
     */
    initializePlots() {
        // ========================================
        // Temperature Plot
        // ========================================
        const tempTrace = {
            x: [],  // Timestamps
            y: [],  // Temperature values
            mode: 'lines',
            name: 'Temperature',
            line: { color: '#ff6b6b', width: 2 }
        };
        
        const tempLayout = {
            title: 'Temperature vs Time',
            xaxis: { 
                title: 'Time',
                type: 'date'  // Automatic time formatting
            },
            yaxis: { 
                title: 'Temperature (°C)',
                range: [-20, 30]  // Fixed range for stability
            },
            paper_bgcolor: '#1e1e1e',  // Dark theme
            plot_bgcolor: '#2d2d2d',
            font: { color: '#e0e0e0' },
            margin: { t: 40, r: 20, b: 40, l: 60 }
        };
        
        Plotly.newPlot('tempPlot', [tempTrace], tempLayout, {
            responsive: true,
            displayModeBar: false  // Hide Plotly toolbar
        });

        // ========================================
        // Power Plot (Voltage & Current)
        // ========================================
        const voltageTrace = {
            x: [],
            y: [],
            mode: 'lines',
            name: 'Voltage',
            line: { color: '#4ecdc4', width: 2 },
            yaxis: 'y'  // Left Y-axis
        };
        
        const currentTrace = {
            x: [],
            y: [],
            mode: 'lines',
            name: 'Current',
            line: { color: '#ffe66d', width: 2 },
            yaxis: 'y2'  // Right Y-axis
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
                overlaying: 'y',  // Overlay on same plot
                side: 'right',  // Position on right
                range: [0, 5]
            },
            paper_bgcolor: '#1e1e1e',
            plot_bgcolor: '#2d2d2d',
            font: { color: '#e0e0e0' },
            margin: { t: 40, r: 60, b: 40, l: 60 },
            legend: { x: 0.5, y: 1.1, orientation: 'h' }  // Horizontal legend on top
        };
        
        Plotly.newPlot('powerPlot', [voltageTrace, currentTrace], powerLayout, {
            responsive: true,
            displayModeBar: false
        });
    }

    /**
     * Initialize Chart.js gauge charts
     * 
     * Creates three semi-circular gauge displays for:
     * - Temperature (-20°C to 30°C)
     * - Voltage (0V to 12V)
     * - Current (0A to 5A)
     * 
     * Each gauge has warning and danger thresholds for visual alerts.
     */
    initializeGauges() {
        // Temperature gauge
        this.gauges.temperature = this.createGauge('tempGauge', {
            min: -20,
            max: 30,
            label: '°C',
            color: '#ff6b6b',
            warningThreshold: 20,  // Yellow warning above this
            dangerThreshold: 25  // Red danger above this
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
     * 
     * Uses Chart.js doughnut chart configured as a semi-circular gauge.
     * 
     * @param {string} canvasId - Canvas element ID
     * @param {Object} config - Gauge configuration
     * @param {number} config.min - Minimum value
     * @param {number} config.max - Maximum value
     * @param {string} config.label - Unit label (e.g., '°C', 'V', 'A')
     * @param {string} config.color - Gauge color (hex)
     * @param {number} config.warningThreshold - Warning level
     * @param {number} config.dangerThreshold - Danger level
     * @returns {Chart|null} Chart.js instance or null if canvas not found
     * 
     * @example
     * const tempGauge = createGauge('myCanvas', {
     *   min: -20, max: 30, label: '°C', color: '#ff6b6b',
     *   warningThreshold: 20, dangerThreshold: 25
     * });
     */
    createGauge(canvasId, config) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        return new Chart(ctx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [0, config.max],  // [filled, empty]
                    backgroundColor: [
                        config.color,  // Filled portion
                        '#3a3a3a'  // Empty portion (dark gray)
                    ],
                    borderWidth: 0,
                    circumference: 180,  // Semi-circle (180°)
                    rotation: 270  // Start from bottom
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
     * Update gauge value and display
     * 
     * @param {string} gaugeName - Gauge name: 'temperature', 'voltage', or 'current'
     * @param {number} value - New value to display
     * 
     * @example
     * monitoring.updateGauge('temperature', 23.5);
     */
    updateGauge(gaugeName, value) {
        const gauge = this.gauges[gaugeName];
        if (!gauge) return;

        // Get config for this gauge
        const config = {
            temperature: { min: -20, max: 30, unit: '°C' },
            voltage: { min: 0, max: 12, unit: 'V' },
            current: { min: 0, max: 5, unit: 'A' }
        }[gaugeName];

        if (!config) return;

        // Clamp value to valid range
        const clampedValue = Math.max(config.min, Math.min(config.max, value));
        
        // Calculate percentage for gauge fill
        const percentage = (clampedValue - config.min) / (config.max - config.min) * config.max;

        // Update chart data (filled vs empty portions)
        gauge.data.datasets[0].data = [percentage, config.max - percentage];
        gauge.update('none');  // Update without animation for smoothness

        // Update text display below gauge
        const valueElement = document.getElementById(`${gaugeName}Value`);
        if (valueElement) {
            valueElement.textContent = `${value.toFixed(2)} ${config.unit}`;
        }
    }

    /**
     * Add data point to time-series plot
     * 
     * Automatically trims old data when buffer exceeds maxDataPoints.
     * 
     * @param {string} plotName - Plot name: 'temp', 'voltage', or 'current'
     * @param {number} value - Data value
     * @param {Date} [timestamp=new Date()] - Optional timestamp (defaults to now)
     * 
     * @example
     * // Add temperature reading with current time
     * monitoring.addDataPoint('temp', 22.5);
     * 
     * // Add voltage reading with specific time
     * monitoring.addDataPoint('voltage', 5.0, new Date('2026-02-06T12:00:00'));
     */
    addDataPoint(plotName, value, timestamp = new Date()) {
        const dataObj = this[`${plotName}Data`];
        if (!dataObj) return;

        // Add new point
        dataObj.x.push(timestamp);
        dataObj.y.push(value);

        // Trim old data to prevent memory growth
        if (dataObj.x.length > this.maxDataPoints) {
            dataObj.x.shift();  // Remove oldest timestamp
            dataObj.y.shift();  // Remove oldest value
        }

        // Update the Plotly plot
        this.updatePlot(plotName);
    }

    /**
     * Update Plotly plot with new data
     * 
     * @param {string} plotName - Plot name: 'temp', 'voltage', or 'current'
     * 
     * @private
     */
    updatePlot(plotName) {
        if (plotName === 'temp') {
            // Update temperature plot
            Plotly.update('tempPlot', {
                x: [this.tempData.x],
                y: [this.tempData.y]
            }, {}, [0]);
        } else if (plotName === 'voltage') {
            // Update voltage trace on power plot
            Plotly.update('powerPlot', {
                x: [this.voltageData.x],
                y: [this.voltageData.y]
            }, {}, [0]);
        } else if (plotName === 'current') {
            // Update current trace on power plot
            Plotly.update('powerPlot', {
                x: [this.currentData.x],
                y: [this.currentData.y]
            }, {}, [1]);
        }
    }

    /**
     * Update all monitoring displays with device data
     * 
     * Updates both gauges and time-series plots with new readings.
     * 
     * @param {Object} deviceData - Device data from server or simulation
     * @param {number} [deviceData.temperature] - Temperature in Celsius
     * @param {number} [deviceData.voltage] - Voltage in Volts
     * @param {number} [deviceData.current] - Current in Amperes
     * 
     * @example
     * // Update from real device
     * monitoring.updateFromDeviceData({
     *   temperature: 22.5,
     *   voltage: 5.0,
     *   current: 2.3
     * });
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
     * Toggle simulation mode on/off
     * 
     * Starts or stops generating simulated sensor data.
     * Updates button appearance and shows/hides simulation indicator.
     */
    toggleSimulation() {
        this.simulationMode = !this.simulationMode;
        
        const btn = document.getElementById('monitoringSimBtn');
        const indicator = document.getElementById('monitoringSimIndicator');
        
        if (this.simulationMode) {
            // Simulation ON
            btn.textContent = 'Disable Simulation';
            btn.classList.add('active');
            indicator.style.display = 'inline-block';
            this.startSimulation();
        } else {
            // Simulation OFF
            btn.textContent = 'Enable Simulation';
            btn.classList.remove('active');
            indicator.style.display = 'none';
            this.stopSimulation();
        }
    }

    /**
     * Start simulation mode
     * 
     * Begins generating simulated data at 2 Hz (twice per second).
     * Simulation time increments by 0.5 seconds per update.
     */
    startSimulation() {
        this.simulationTime = 0;
        this.simulationInterval = setInterval(() => {
            this.simulationTime += 0.5;
            const data = this.generateSimulationData();
            this.updateFromDeviceData(data);
        }, 500); // Update twice per second (2 Hz)
    }

    /**
     * Stop simulation mode
     * 
     * Clears the simulation interval timer.
     */
    stopSimulation() {
        if (this.simulationInterval) {
            clearInterval(this.simulationInterval);
            this.simulationInterval = null;
        }
    }

    /**
     * Generate simulated sensor data
     * 
     * Creates realistic-looking sensor data using:
     * - Sinusoidal waves for smooth trends
     * - Random Gaussian noise for realism
     * - Different frequencies for each sensor
     * 
     * Temperature: Oscillates around 20°C with ±5°C amplitude + ±1°C noise
     * Voltage: Oscillates around 5.0V with ±0.5V amplitude + ±0.1V noise
     * Current: Oscillates around 2.5A with ±1.0A amplitude + ±0.15A noise
     * 
     * @returns {Object} Simulated data
     * @returns {number} return.temperature - Temperature in Celsius
     * @returns {number} return.voltage - Voltage in Volts
     * @returns {number} return.current - Current in Amperes
     * 
     * @example
     * const data = monitoring.generateSimulationData();
     * console.log(`Temp: ${data.temperature.toFixed(2)}°C`);
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

// ============================================================================
// GLOBAL FUNCTIONS
// ============================================================================

/**
 * Global monitoring instance
 * @type {MonitoringCharts}
 */
let monitoring;

/**
 * Initialize monitoring charts on page load
 * 
 * Creates the MonitoringCharts instance and initializes all visualizations.
 */
function initMonitoring() {
    monitoring = new MonitoringCharts();
}

/**
 * Toggle monitoring simulation mode
 * 
 * Called when user clicks the simulation button on monitoring tab.
 */
function toggleMonitoringSimulation() {
    if (!monitoring) return;
    monitoring.toggleSimulation();
}

// ============================================================================
// INITIALIZATION
// ============================================================================

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMonitoring);
} else {
    initMonitoring();
}

// Export for use in main app
window.monitoring = monitoring;
