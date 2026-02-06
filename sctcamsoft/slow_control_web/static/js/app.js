/**
 * Main Application Script
 * 
 * Handles tab navigation and coordinates between camera visualization
 * and monitoring displays. Camera display is shared across temperature,
 * voltage, current, and status tabs by moving DOM elements.
 */

let socket;
let currentTab = 'system';
let cameraDisplayElement = null;

/**
 * Initialize application
 */
function initApp() {
    // Initialize WebSocket connection
    initWebSocket();
    
    // Show default tab
    showTab('system');
}

/**
 * Initialize WebSocket connection
 */
function initWebSocket() {
    socket = io();
    
    socket.on('connect', function() {
        updateConnectionStatus(true);
        console.log('Connected to server');
    });
    
    socket.on('disconnect', function() {
        updateConnectionStatus(false);
        console.log('Disconnected from server');
    });
    
    socket.on('device_update', function(data) {
        handleDeviceUpdate(data);
    });
    
    socket.on('alert', function(data) {
        showAlert(data.message, data.type);
    });
}

/**
 * Show a specific tab and move camera display if needed
 * 
 * @param {string} tabName - Tab identifier
 */
function showTab(tabName) {
    currentTab = tabName;
    
    // Hide all tabs
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => tab.classList.remove('active'));
    
    // Remove active class from all buttons
    const buttons = document.querySelectorAll('.tab-button');
    buttons.forEach(btn => btn.classList.remove('active'));
    
    // Show selected tab
    const selectedTab = document.getElementById(tabName + '-tab');
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    // Activate corresponding button
    const buttonText = tabName.charAt(0).toUpperCase() + tabName.slice(1);
    buttons.forEach(btn => {
        if (btn.textContent === buttonText) {
            btn.classList.add('active');
        }
    });
    
    // Camera tabs that use the shared camera display
    const cameraTabsWithDisplay = ['temperature', 'voltage', 'current', 'status'];
    
    if (cameraTabsWithDisplay.includes(tabName)) {
        // Initialize camera on first access to a camera tab
        if (typeof initCameraVisualization === 'function' && !window.cameraInitialized) {
            initCameraVisualization();
        }
        
        // Get or create reference to camera display
        if (!cameraDisplayElement) {
            cameraDisplayElement = document.querySelector('.camera-display');
        }
        
        // Move camera display to current tab if it exists
        if (cameraDisplayElement) {
            const targetContainer = document.querySelector(`#${tabName}-tab .visualization-container`);
            if (targetContainer && !targetContainer.querySelector('.camera-display')) {
                // Insert camera display at the beginning of the container (after h2)
                const h2 = targetContainer.querySelector('h2');
                if (h2 && h2.nextSibling) {
                    targetContainer.insertBefore(cameraDisplayElement, h2.nextSibling);
                } else {
                    targetContainer.appendChild(cameraDisplayElement);
                }
            }
        }
        
        // Update camera visualization data type
        if (window.cameraViz && window.cameraViz.initialized) {
            cameraViz.setDataType(tabName);
        }
    }
}

/**
 * Update connection status indicator
 * 
 * @param {boolean} connected - Connection state
 */
function updateConnectionStatus(connected) {
    const indicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    
    if (indicator && statusText) {
        if (connected) {
            indicator.classList.add('connected');
            indicator.classList.remove('disconnected');
            statusText.textContent = 'Connected';
        } else {
            indicator.classList.remove('connected');
            indicator.classList.add('disconnected');
            statusText.textContent = 'Disconnected';
        }
    }
}

/**
 * Handle device update from server
 * 
 * @param {Object} data - Device update data
 */
function handleDeviceUpdate(data) {
    console.log('Device update:', data);
    
    // Update monitoring displays if available
    if (window.monitoring && data.monitoring) {
        monitoring.updateFromDeviceData(data.monitoring);
    }
    
    // Update camera visualization if real data available
    if (window.cameraViz && !cameraViz.simulationMode && data.camera) {
        // TODO: Update camera with real data
    }
}

/**
 * Send command to server
 * 
 * @param {string} command - Command identifier
 * @param {Object} params - Command parameters
 */
function sendCommand(command, params = {}) {
    if (socket && socket.connected) {
        socket.emit('command', {
            command: command,
            params: params,
            timestamp: new Date().toISOString()
        });
        
        showAlert(`Command sent: ${command}`, 'info');
    } else {
        showAlert('Not connected to server', 'error');
    }
}

/**
 * Show alert message
 * 
 * @param {string} message - Alert message
 * @param {string} type - Alert type: 'info', 'success', 'warning', 'error'
 */
function showAlert(message, type = 'info') {
    const container = document.getElementById('alertContainer');
    if (!container) return;
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    
    container.appendChild(alert);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alert.classList.add('fade-out');
        setTimeout(() => alert.remove(), 300);
    }, 5000);
    
    // Click to dismiss
    alert.addEventListener('click', () => {
        alert.classList.add('fade-out');
        setTimeout(() => alert.remove(), 300);
    });
}

/**
 * Toggle monitoring simulation
 * Separate from camera simulation
 */
function toggleMonitoringSimulation() {
    if (window.monitoring) {
        monitoring.toggleSimulation();
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}
