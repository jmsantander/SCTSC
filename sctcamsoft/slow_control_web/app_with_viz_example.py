#!/usr/bin/env python3
"""
Example: Flask app with camera visualization integrated

This is an example showing how to integrate the visualization system
into your existing app.py. Copy the relevant sections to your app.py.
"""

import argparse
import yaml
import os
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import time
from datetime import datetime, timezone

# Import camera visualization
from sctcamsoft.lib_gui.camera_comm import CameraComm
from sctcamsoft.slow_control_web.device_manager import DeviceManager
from sctcamsoft.slow_control_web.camera_api import CameraAPI, register_camera_routes

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sct-slowcontrol-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
camera_comm = None
device_manager = None
config = None
commands = None
camera_api = None  # NEW: Camera API

@app.route('/')
def index():
    """Render the main control interface with visualization."""
    # Use the visualization-enabled template
    return render_template('index_with_viz.html')  # Changed from 'index.html'

@app.route('/api/status')
def get_status():
    """Get overall system status."""
    if device_manager is None:
        return jsonify({'status': 'disconnected'})
    
    return jsonify({
        'status': 'connected' if camera_comm else 'disconnected',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'devices': device_manager.get_all_device_states()
    })

@app.route('/api/device/<device_name>')
def get_device_status(device_name):
    """Get status of a specific device."""
    if device_manager is None:
        return jsonify({'error': 'Device manager not initialized'}), 500
    
    state = device_manager.get_device_state(device_name)
    if state is None:
        return jsonify({'error': f'Device {device_name} not found'}), 404
    
    return jsonify(state)

@app.route('/api/command', methods=['POST'])
def send_command():
    """Send a command to the camera server."""
    if camera_comm is None:
        return jsonify({'error': 'Camera communication not initialized'}), 500
    
    data = request.get_json()
    command = data.get('command')
    params = data.get('params', {})
    
    if not command:
        return jsonify({'error': 'No command specified'}), 400
    
    try:
        camera_comm.send_command(command, **params)
        return jsonify({'success': True, 'command': command})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# NEW: Camera visualization endpoints are registered via camera_api
# (See register_camera_routes call in main())

@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print(f'Client connected: {request.sid}')
    emit('connection_response', {'status': 'connected'})
    
@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    print(f'Client disconnected: {request.sid}')

@socketio.on('subscribe')
def handle_subscribe(data):
    """Subscribe to device updates."""
    device_name = data.get('device')
    print(f'Client {request.sid} subscribed to {device_name}')
    emit('subscribe_response', {'device': device_name, 'subscribed': True})

# NEW: WebSocket handler for real-time monitoring updates
@socketio.on('subscribe_monitoring')
def handle_monitoring_subscribe():
    """Subscribe to real-time monitoring updates."""
    print(f'Client {request.sid} subscribed to monitoring')
    emit('monitoring_subscribed', {'success': True})

def broadcast_updates():
    """Background thread to broadcast device updates to all clients."""
    while True:
        if device_manager:
            updates = device_manager.get_all_device_states()
            
            # Broadcast device updates
            socketio.emit('device_updates', updates)
            
            # NEW: Broadcast monitoring data
            # Extract monitoring data from device states
            monitoring_data = extract_monitoring_data(updates)
            if monitoring_data:
                socketio.emit('monitoring_update', monitoring_data)
        
        time.sleep(1)  # Update every second

def extract_monitoring_data(device_states):
    """
    Extract monitoring data from device states.
    
    Args:
        device_states (dict): All device states
    
    Returns:
        dict: Monitoring data with temperature, voltage, current
    """
    # This is an example - adjust to match your device structure
    data = {}
    
    # Extract temperature (example)
    if 'temperature' in device_states:
        temp_device = device_states['temperature']
        if 'variables' in temp_device:
            # Get first temperature reading
            for var_name, var_data in temp_device['variables'].items():
                if not var_data.get('expired', True):
                    data['temperature'] = float(var_data.get('value', 0))
                    break
    
    # Extract voltage (example)
    if 'power' in device_states:
        power_device = device_states['power']
        if 'variables' in power_device:
            for var_name, var_data in power_device['variables'].items():
                if 'voltage' in var_name.lower() and not var_data.get('expired', True):
                    data['voltage'] = float(var_data.get('value', 0))
                elif 'current' in var_name.lower() and not var_data.get('expired', True):
                    data['current'] = float(var_data.get('value', 0))
    
    return data if data else None

def init_camera_comm(config, commands):
    """Initialize camera communication."""
    global camera_comm, device_manager, camera_api
    
    ui_config = config['user_interface']
    
    # Create camera communication object
    camera_comm = CameraComm(
        ui_config['host'],
        ui_config['input_port'],
        ui_config['output_port'],
        ui_config['header_length'],
        commands
    )
    
    # Initialize in a separate thread
    comm_thread = threading.Thread(target=camera_comm.init, daemon=True)
    comm_thread.start()
    
    # Create device manager
    device_manager = DeviceManager(camera_comm, config)
    
    # NEW: Initialize camera API for visualization
    camera_api = CameraAPI(camera_comm)
    
    # Register connection state changes
    if hasattr(camera_comm, 'on_connec_state_changed'):
        camera_comm.on_connec_state_changed.connect(
            lambda state: print(f'Connection state changed: {state}')
        )

def main():
    parser = argparse.ArgumentParser(description='SCT Camera Slow Control Web Interface with Visualization')
    parser.add_argument('config_file', help='Path to slow control config file')
    parser.add_argument('commands_file', help='Path to slow control commands file')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to (default: 5000)')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    args = parser.parse_args()
    
    # Load configuration
    global config, commands
    with open(args.config_file, 'r') as config_file:
        config = yaml.load(config_file, Loader=yaml.SafeLoader)
    
    with open(args.commands_file, 'r') as commands_file:
        commands = yaml.load(commands_file, Loader=yaml.SafeLoader)
    
    # Initialize camera communication
    init_camera_comm(config, commands)
    
    # NEW: Register camera visualization routes
    register_camera_routes(app, camera_api)
    
    # Start background update thread
    update_thread = threading.Thread(target=broadcast_updates, daemon=True)
    update_thread.start()
    
    # Run Flask app
    print(f'Starting SCT Slow Control Web Interface with Visualization')
    print(f'Server running at http://{args.host}:{args.port}')
    print(f'Features:')
    print(f'  - Camera View: Real-time camera module display')
    print(f'  - Monitoring: Time-series plots and gauges')
    print(f'  - Device Control: Full slow control interface')
    
    socketio.run(app, host=args.host, port=args.port, debug=args.debug)

if __name__ == '__main__':
    main()
