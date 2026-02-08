/**
 * Main Application Script
 * Single-page layout with camera view switching via tabs
 */

let socket;
let currentView = 'current';

/**
 * Initialize application
 */
function initApp() {
    // Initialize WebSocket connection
    initWebSocket();
    
    // Initialize camera visualization
    if (typeof initCameraVisualization === 'function') {
        initCameraVisualization();
    }
    
    // Set initial view
    switchCameraView('current');
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
 * Switch camera view (current, voltage, presence, temperature, status)
 */
function switchCameraView(viewType) {
    currentView = viewType;
    
    // Update active tab
    document.querySelectorAll('.camera-tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Find and activate the clicked button
    const buttons = document.querySelectorAll('.camera-tab-button');
    buttons.forEach(btn => {
        const btnText = btn.textContent.toLowerCase();
        if (
            (viewType === 'current' && btnText.includes('current')) ||
            (viewType === 'voltage' && btnText.includes('voltage')) ||
            (viewType === 'presence' && btnText.includes('presence')) ||
            (viewType === 'temperature' && btnText.includes('temp')) ||
            (viewType === 'status' && btnText.includes('state'))
        ) {
            btn.classList.add('active');
        }
    });
    
    // Map view types to data types
    const dataTypeMap = {
        'current': 'current',
        'voltage': 'voltage',
        'presence': 'status',
        'temperature': 'temperature',
        'status': 'status'
    };
    
    // Update camera visualization
    if (window.cameraViz && window.cameraViz.initialized) {
        cameraViz.setDataType(dataTypeMap[viewType]);
    }
}

/**
 * Toggle simulation mode
 */
function toggleSimulation() {
    if (!window.cameraViz) {
        console.error('Camera visualization not initialized');
        return;
    }
    
    cameraViz.toggleSimulation();
    
    // Update UI
    const btn = document.getElementById('simulationBtn');
    const indicator = document.getElementById('simulationIndicator');
    
    if (cameraViz.simulationMode) {
        if (btn) {
            btn.textContent = 'Disable Simulation';
            btn.classList.add('active');
        }
        if (indicator) {
            indicator.classList.add('active');
        }
    } else {
        if (btn) {
            btn.textContent = 'Enable Simulation';
            btn.classList.remove('active');
        }
        if (indicator) {
            indicator.classList.remove('active');
        }
    }
}

/**
 * Update connection status indicator
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
            statusText.textContent = 'No connection';
        }
    }
}

/**
 * Handle device update from server
 */
function handleDeviceUpdate(data) {
    console.log('Device update:', data);
    
    // Update camera visualization if real data available
    if (window.cameraViz && !cameraViz.simulationMode && data.camera) {
        // TODO: Update camera with real data
    }
    
    // Update control panel values
    if (data.fan) {
        updateField('fanVoltage', data.fan.voltage);
        updateField('fanCurrent', data.fan.current);
    }
    
    if (data.chiller) {
        updateField('chillerPressure', data.chiller.pressure);
        updateField('chillerTemp', data.chiller.temperature);
    }
    
    if (data.network) {
        updateField('eth6Status', data.network.eth6);
        updateField('eth7Status', data.network.eth7);
        updateField('eth8Status', data.network.eth8);
        updateField('eth9Status', data.network.eth9);
    }
    
    if (data.power) {
        updateField('supplyCurrent', data.power.supplyCurrent);
        updateField('hvCurrent', data.power.hvCurrent);
        updateField('supplyNomVolts', data.power.supplyNomVolts);
        updateField('hvNomVolts', data.power.hvNomVolts);
        updateField('supplyMeasVolts', data.power.supplyMeasVolts);
        updateField('hvMeasVolts', data.power.hvMeasVolts);
    }
    
    if (data.shutter) {
        updateField('shutterStatus', data.shutter.motorStatus);
        updateField('shutterClosedStatus', data.shutter.closedStatus);
    }
}

/**
 * Update a field value in the UI
 */
function updateField(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value !== undefined && value !== null ? value : 'None';
    }
}

/**
 * Send command to server
 */
function sendCommand(command, params = {}) {
    if (socket && socket.connected) {
        socket.emit('command', {
            command: command,
            params: params,
            timestamp: new Date().toISOString()
        });
        
        console.log(`Command sent: ${command}`);
    } else {
        console.error('Not connected to server');
        alert('Not connected to server');
    }
}

/**
 * Check network activity
 */
function checkNetworkActivity() {
    sendCommand('check_network_activity');
}

/**
 * Execute backplane command
 */
function executeBackplaneCommand() {
    const select = document.getElementById('backplaneSelect');
    if (select) {
        sendCommand('backplane_command', { command: select.value });
    }
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info') {
    alert(message);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}
