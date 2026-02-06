// SCT Camera Slow Control Web Interface JavaScript

class SlowControlApp {
    constructor() {
        this.socket = null;
        this.connected = false;
        this.deviceStates = {};
        this.init();
    }

    init() {
        // Initialize Socket.IO connection
        this.socket = io();
        
        // Set up socket event handlers
        this.socket.on('connect', () => this.onConnect());
        this.socket.on('disconnect', () => this.onDisconnect());
        this.socket.on('connection_response', (data) => this.onConnectionResponse(data));
        this.socket.on('device_updates', (data) => this.onDeviceUpdates(data));
        
        // Set up periodic status updates
        this.startStatusUpdates();
        
        console.log('Slow Control App initialized');
    }

    onConnect() {
        console.log('Connected to server');
        this.connected = true;
        this.updateConnectionStatus('connected');
    }

    onDisconnect() {
        console.log('Disconnected from server');
        this.connected = false;
        this.updateConnectionStatus('disconnected');
    }

    onConnectionResponse(data) {
        console.log('Connection response:', data);
    }

    onDeviceUpdates(data) {
        console.log('Device updates received:', data);
        this.deviceStates = data;
        this.updateUI(data);
    }

    updateConnectionStatus(status) {
        const indicator = document.getElementById('statusIndicator');
        const text = document.getElementById('statusText');
        
        indicator.className = 'status-indicator ' + status;
        text.textContent = status === 'connected' ? 'Connected' : 'Disconnected';
        
        // Update system status
        const sysConnection = document.getElementById('sysConnection');
        if (sysConnection) {
            sysConnection.textContent = status === 'connected' ? 'Active' : 'Inactive';
        }
    }

    updateUI(deviceData) {
        // Update system last update time
        const lastUpdateEl = document.getElementById('sysLastUpdate');
        if (lastUpdateEl) {
            lastUpdateEl.textContent = new Date().toLocaleTimeString();
        }

        // Update device overview cards
        this.updateDeviceOverview(deviceData);
        
        // Update specific device tabs
        this.updateDeviceTabs(deviceData);
    }

    updateDeviceOverview(deviceData) {
        const overview = document.getElementById('deviceOverview');
        if (!overview) return;

        overview.innerHTML = '';
        
        for (const [deviceName, deviceState] of Object.entries(deviceData)) {
            const card = this.createDeviceCard(deviceName, deviceState);
            overview.appendChild(card);
        }
    }

    createDeviceCard(deviceName, deviceState) {
        const card = document.createElement('div');
        card.className = 'device-card';
        
        const title = document.createElement('h3');
        title.textContent = deviceName.replace('_', ' ');
        card.appendChild(title);

        const statusGrid = document.createElement('div');
        statusGrid.className = 'status-grid';

        if (deviceState.variables) {
            const varCount = Object.keys(deviceState.variables).length;
            const expiredCount = Object.values(deviceState.variables)
                .filter(v => v.expired).length;
            
            // Show variable count
            const countItem = this.createStatusItem(
                'Variables', 
                `${varCount} (${expiredCount} expired)`
            );
            statusGrid.appendChild(countItem);
            
            // Show first few variables
            let count = 0;
            for (const [varName, varData] of Object.entries(deviceState.variables)) {
                if (count >= 3) break;
                const item = this.createStatusItem(
                    varName,
                    this.formatValue(varData.value),
                    varData.expired
                );
                statusGrid.appendChild(item);
                count++;
            }
        }

        card.appendChild(statusGrid);
        return card;
    }

    createStatusItem(label, value, expired = false) {
        const item = document.createElement('div');
        item.className = 'status-item' + (expired ? ' expired' : '');
        
        const labelEl = document.createElement('span');
        labelEl.className = 'status-label';
        labelEl.textContent = label + ':';
        
        const valueEl = document.createElement('span');
        valueEl.className = 'status-value';
        valueEl.textContent = value;
        
        item.appendChild(labelEl);
        item.appendChild(valueEl);
        
        return item;
    }

    updateDeviceTabs(deviceData) {
        // Update power tab
        if (deviceData.power) {
            this.updatePowerTab(deviceData.power);
        }
        
        // Update module tab
        if (deviceData.module) {
            this.updateModuleTab(deviceData.module);
        }
        
        // Update temperature tab
        if (deviceData.fee_temp) {
            this.updateTemperatureTab(deviceData.fee_temp);
        }
        
        // Update chiller tab
        if (deviceData.chiller) {
            this.updateChillerTab(deviceData.chiller);
        }
        
        // Update other tabs as needed...
    }

    updatePowerTab(powerData) {
        const container = document.getElementById('powerControls');
        if (!container || !powerData.variables) return;
        
        container.innerHTML = '';
        
        for (const [varName, varData] of Object.entries(powerData.variables)) {
            const item = this.createStatusItem(
                varName,
                this.formatValue(varData.value),
                varData.expired
            );
            container.appendChild(item);
        }
    }

    updateModuleTab(moduleData) {
        const container = document.getElementById('moduleControls');
        if (!container || !moduleData.variables) return;
        
        container.innerHTML = '';
        
        for (const [varName, varData] of Object.entries(moduleData.variables)) {
            const item = this.createStatusItem(
                varName,
                this.formatValue(varData.value),
                varData.expired
            );
            container.appendChild(item);
        }
    }

    updateTemperatureTab(tempData) {
        const container = document.getElementById('temperatureDisplay');
        if (!container || !tempData.variables) return;
        
        container.innerHTML = '';
        
        for (const [varName, varData] of Object.entries(tempData.variables)) {
            const item = this.createStatusItem(
                varName,
                this.formatValue(varData.value) + (typeof varData.value === 'number' ? ' °C' : ''),
                varData.expired
            );
            container.appendChild(item);
        }
    }

    updateChillerTab(chillerData) {
        const container = document.getElementById('chillerControls');
        if (!container || !chillerData.variables) return;
        
        container.innerHTML = '';
        
        for (const [varName, varData] of Object.entries(chillerData.variables)) {
            const item = this.createStatusItem(
                varName,
                this.formatValue(varData.value),
                varData.expired
            );
            container.appendChild(item);
        }
    }

    formatValue(value) {
        if (typeof value === 'number') {
            return value.toFixed(2);
        }
        if (typeof value === 'boolean') {
            return value ? 'ON' : 'OFF';
        }
        return String(value);
    }

    startStatusUpdates() {
        // Poll for status every 2 seconds
        setInterval(() => {
            if (this.connected) {
                fetch('/api/status')
                    .then(response => response.json())
                    .then(data => {
                        if (data.devices) {
                            this.deviceStates = data.devices;
                            this.updateUI(data.devices);
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching status:', error);
                    });
            }
        }, 2000);
    }

    sendCommand(command, params = {}) {
        console.log('Sending command:', command, params);
        
        fetch('/api/command', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                command: command,
                params: params
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showAlert('Command sent: ' + command, 'success');
            } else {
                this.showAlert('Error: ' + data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error sending command:', error);
            this.showAlert('Failed to send command', 'error');
        });
    }

    showAlert(message, type = 'info') {
        const container = document.getElementById('alertContainer');
        if (!container) return;

        const alert = document.createElement('div');
        alert.className = 'alert ' + type;
        alert.textContent = message;
        
        container.appendChild(alert);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            alert.style.animation = 'slideIn 0.3s ease reverse';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    }
}

// Global functions for UI
function showTab(tabName) {
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
    const activeButton = Array.from(buttons).find(
        btn => btn.textContent.toLowerCase().includes(tabName.toLowerCase())
    );
    if (activeButton) {
        activeButton.classList.add('active');
    }
}

function sendCommand(command, params) {
    if (window.app) {
        window.app.sendCommand(command, params);
    }
}

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.app = new SlowControlApp();
    });
} else {
    window.app = new SlowControlApp();
}
