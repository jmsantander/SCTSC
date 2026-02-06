#!/usr/bin/env python3
"""Flask-based web interface for SCT Camera Slow Control.

Replaces the PyQt desktop application with a modern web-based interface.
Provides real-time monitoring and control through WebSockets.
"""

import argparse
import yaml
import os
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import time
from datetime import datetime, timezone

from sctcamsoft.lib_gui.camera_comm import CameraComm
from sctcamsoft.slow_control_web.device_manager import DeviceManager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sct-slowcontrol-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
camera_comm = None
device_manager = None
config = None
commands = None

@app.route('/')
def index():
    """Render the main control interface."""
    return render_template('index.html')

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
    # Add subscription logic if needed
    emit('subscribe_response', {'device': device_name, 'subscribed': True})

def broadcast_updates():
    """Background thread to broadcast device updates to all clients."""
    while True:
        if device_manager:
            updates = device_manager.get_all_device_states()
            socketio.emit('device_updates', updates)
        time.sleep(1)  # Update every second

def init_camera_comm(config, commands):
    """Initialize camera communication."""
    global camera_comm, device_manager
    
    ui_config = config['user_interface']
    
    # Create camera communication object
    camera_comm = CameraComm(
        ui_config['host'],
        ui_config['input_port'],
        ui_config['output_port'],
        ui_config['header_length'],
        commands
    )
    
    # Initialize in a separate thread (Flask doesn't use QThread)
    comm_thread = threading.Thread(target=camera_comm.init, daemon=True)
    comm_thread.start()
    
    # Create device manager
    device_manager = DeviceManager(camera_comm, config)
    
    # Register connection state changes
    if hasattr(camera_comm, 'on_connec_state_changed'):
        camera_comm.on_connec_state_changed.connect(
            lambda state: print(f'Connection state changed: {state}')
        )

def main():
    parser = argparse.ArgumentParser(description='SCT Camera Slow Control Web Interface')
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
    
    # Start background update thread
    update_thread = threading.Thread(target=broadcast_updates, daemon=True)
    update_thread.start()
    
    # Run Flask app
    print(f'Starting SCT Slow Control Web Interface on http://{args.host}:{args.port}')
    socketio.run(app, host=args.host, port=args.port, debug=args.debug)

if __name__ == '__main__':
    main()
