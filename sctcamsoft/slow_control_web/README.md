# SCT Camera Slow Control Web Interface

A modern, Flask-based web interface for the SCT Camera Slow Control system, replacing the PyQt desktop application with a browser-based solution.

## Features

- **Real-time Monitoring**: Live updates of all camera subsystems via WebSockets
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Modern UI**: Clean, dark-themed interface with intuitive navigation
- **Device Management**: Monitor and control all camera devices:
  - System initialization and shutdown
  - Power supplies
  - Temperature sensors
  - Chiller system
  - Shutter control
  - Backplane status
  - Target positioning
  - Module management
  - Fan controls

## Architecture

The web interface maintains the same architecture as the PyQt application:

- **Flask Backend**: Handles HTTP requests and WebSocket connections
- **Device Manager**: Manages device states and provides thread-safe access
- **Camera Communication**: Reuses existing `CameraComm` from `lib_gui`
- **Real-time Updates**: Socket.IO for bidirectional communication

## Installation

### Requirements

```bash
pip install -r requirements.txt
```

Required packages:
- Flask (>=2.3.0)
- Flask-SocketIO (>=5.3.0)
- python-socketio (>=5.9.0)
- PyYAML (>=6.0)

### Setup

1. Ensure the parent `sctcamsoft` package is installed or in your PYTHONPATH
2. Verify you have the required config and commands YAML files
3. Install dependencies as shown above

## Usage

### Starting the Server

```bash
python app.py <config_file> <commands_file>
```

#### Options:

- `config_file`: Path to slow control configuration YAML file
- `commands_file`: Path to slow control commands YAML file
- `--host`: Host to bind to (default: 0.0.0.0)
- `--port`: Port to bind to (default: 5000)
- `--debug`: Run in debug mode

#### Example:

```bash
python app.py ../configs/slow_control_config.yaml ../configs/slow_control_commands.yaml --port 5000
```

### Accessing the Interface

Once the server is running, open your web browser and navigate to:

```
http://localhost:5000
```

Or from another device on the network:

```
http://<server-ip>:5000
```

## Interface Overview

### Main Tabs

1. **System**: System-wide controls and device overview
   - Initialize System button
   - Shutdown button
   - Overview cards for all devices

2. **Power**: Power supply monitoring and control
   - Voltage readings
   - Current measurements
   - Power state indicators

3. **Modules**: Camera module status
   - Module states
   - Configuration status
   - Module-specific controls

4. **Temperature**: Temperature monitoring
   - FEE temperature readings
   - Multiple sensor locations
   - Temperature alerts

5. **Chiller**: Chiller system controls
   - Temperature setpoints
   - Flow rates
   - Status indicators

6. **Shutter**: Shutter control
   - Open/close commands
   - Position feedback

7. **Backplane**: Backplane status monitoring
   - Connection states
   - Communication status

8. **Target**: Target positioning controls
   - Position commands
   - Current position feedback

### Status Indicators

- **Green**: Normal operation, fresh data
- **Gray/Faded**: Stale data (expired timeout)
- **Connection indicator**: Shows server connection status

## API Endpoints

### REST API

#### GET /api/status
Get overall system status including all devices

**Response:**
```json
{
  "status": "connected",
  "timestamp": "2026-02-06T10:18:00.000Z",
  "devices": {
    "power": { ... },
    "module": { ... }
  }
}
```

#### GET /api/device/<device_name>
Get status of a specific device

**Response:**
```json
{
  "device_name": "power",
  "variables": {
    "voltage_1": {
      "value": 5.0,
      "expired": false,
      "updated": "2026-02-06T10:18:00.000Z"
    }
  },
  "timestamp": "2026-02-06T10:18:00.000Z"
}
```

#### POST /api/command
Send a command to the camera server

**Request:**
```json
{
  "command": "initialize_system",
  "params": {}
}
```

**Response:**
```json
{
  "success": true,
  "command": "initialize_system"
}
```

### WebSocket Events

#### Client -> Server
- `connect`: Client connection
- `subscribe`: Subscribe to device updates
  ```json
  {"device": "power"}
  ```

#### Server -> Client
- `connection_response`: Connection acknowledgment
- `device_updates`: Real-time device state updates (sent every 1 second)
  ```json
  {
    "power": { ... },
    "module": { ... }
  }
  ```

## Configuration

The web interface uses the same configuration files as the PyQt application:

### Config File (YAML)
```yaml
user_interface:
  host: "camera-server-hostname"
  input_port: 5001
  output_port: 5002
  header_length: 64
```

### Commands File (YAML)
Defines available commands for camera control (same format as PyQt version)

## Comparison with PyQt Version

### Advantages of Web Interface

1. **Cross-platform**: Works on any device with a web browser
2. **No Installation**: Users don't need to install PyQt or Python
3. **Remote Access**: Control from anywhere on the network
4. **Multiple Clients**: Multiple users can monitor simultaneously
5. **Mobile Support**: Responsive design works on phones/tablets
6. **Easy Updates**: Update UI without redistributing application

### Maintained Features

- All device controls and monitoring
- Real-time updates
- Command sending capability
- Alert/status notifications
- Same backend communication protocols

## Development

### Project Structure

```
slow_control_web/
├── app.py                 # Main Flask application
├── device_manager.py      # Device state management
├── __init__.py            # Package initialization
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── static/
│   ├── css/
│   │   └── style.css      # Application styles
│   └── js/
│       └── app.js         # Frontend JavaScript
└── templates/
    └── index.html         # Main HTML template
```

### Adding New Device Controls

1. Update `device_manager.py` to include the new device in the `devices` list
2. Add a new tab in `templates/index.html`
3. Implement update methods in `static/js/app.js`
4. Add styling in `static/css/style.css` if needed

### Debugging

Run with debug mode:
```bash
python app.py config.yaml commands.yaml --debug
```

Check browser console for JavaScript errors and Flask terminal for backend logs.

## Security Considerations

**Important**: This application is designed for internal network use.

For production deployment:
1. Use HTTPS (configure with reverse proxy like nginx)
2. Add authentication (Flask-Login or similar)
3. Implement rate limiting
4. Restrict CORS origins
5. Use production WSGI server (gunicorn, uWSGI)

## Troubleshooting

### Connection Issues

- Verify camera server is running and accessible
- Check firewall settings
- Confirm config file has correct host/port

### No Real-time Updates

- Check browser console for WebSocket errors
- Verify Socket.IO client library is loading
- Check network connectivity

### Command Not Working

- Verify command exists in commands YAML file
- Check Flask logs for error messages
- Confirm camera server is accepting commands

## License

Same license as parent SCT Camera Software project.

## Authors

Based on the original PyQt slow control GUI.
Web interface created: February 2026
