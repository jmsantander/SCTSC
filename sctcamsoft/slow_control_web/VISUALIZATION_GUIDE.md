# Camera Visualization Integration Guide

Complete guide for using the web-based camera visualization system with Canvas, Plotly.js, and Chart.js.

## Overview

This visualization system replaces matplotlib with web-native technologies:

- **HTML5 Canvas**: Real-time camera image display with color scales
- **Plotly.js**: Interactive time-series monitoring plots
- **Chart.js**: Gauge displays for temperature, voltage, current

## Files Created

```
slow_control_web/
├── templates/
│   └── index_with_viz.html       # Enhanced HTML with visualization tabs
├── static/
│   ├── css/
│   │   └── visualization.css     # Visualization styles
│   └── js/
│       ├── camera_viz.js         # Canvas camera visualization
│       └── monitoring.js         # Plotly & Chart.js monitoring
└── camera_api.py                  # Flask API for camera data
```

## Quick Start

### 1. Update app.py to Use New Template

Modify your `app.py` to use the visualization template and register camera routes:

```python
from sctcamsoft.slow_control_web.camera_api import CameraAPI, register_camera_routes

# After creating your Flask app
app = Flask(__name__)

# Initialize camera API
camera_api = CameraAPI(camera_comm)  # Pass your camera_comm object

# Register camera routes
register_camera_routes(app, camera_api)

# Use visualization template
@app.route('/')
def index():
    return render_template('index_with_viz.html')
```

### 2. Install Dependencies

Add to your `requirements.txt`:

```txt
numpy>=1.24.0
```

The JavaScript libraries (Plotly.js, Chart.js, Socket.IO) are loaded via CDN.

### 3. Run the Application

```bash
python -m sctcamsoft.slow_control_web.app configs/slow_control_config.yaml configs/slow_control_commands.yaml --port 5003
```

## Features

### Camera View Tab

#### Canvas Display
- Real-time camera module image rendering
- Multiple color scales: Grayscale, Hot, Viridis
- Mouse hover shows pixel coordinates and values
- Module selector (0-10 for SCT camera)

#### Usage:

```javascript
// JavaScript API
cameraViz.updateImage(pixelArray, width, height);
cameraViz.setColorScale('hot');
cameraViz.selectModule(3);
```

#### Module Grid
- Hexagonal layout representing 11 camera modules
- Click to select and view module data
- Color-coded status (active, warning, error)

### Monitoring Tab

#### Gauge Charts (Chart.js)
- Temperature gauge (-20°C to 30°C)
- Voltage gauge (0-12V)
- Current gauge (0-5A)
- Color-coded thresholds

#### Time-Series Plots (Plotly.js)
- Temperature history
- Voltage/Current dual-axis plot
- Interactive zoom and pan
- Keeps last 100 data points
- Auto-scrolling time axis

#### Usage:

```javascript
// Update monitoring displays
monitoring.updateGauge('temperature', 25.3);
monitoring.addDataPoint('temp', 25.3);
monitoring.updateFromDeviceData({
    temperature: 25.3,
    voltage: 5.0,
    current: 2.5
});
```

## API Endpoints

### GET /api/camera/image

Get camera image for a module

**Parameters:**
- `module` (int): Module ID (0-10)

**Response:**
```json
{
    "success": true,
    "module_id": 0,
    "width": 48,
    "height": 48,
    "image": [0, 1, 2, ...],  // Array of pixel values (0-255)
    "timestamp": "2026-02-06T11:00:00"
}
```

### GET /api/camera/module/<module_id>

Get module info and image data

**Response:**
```json
{
    "info": {
        "id": 0,
        "status": "active",
        "temperature": 20.5,
        "voltage": 5.0,
        "x": 0,
        "y": 0
    },
    "image": [...],
    "width": 48,
    "height": 48
}
```

### GET /api/camera/modules

Get information about all modules

**Response:**
```json
{
    "modules": [
        {"id": 0, "status": "active", ...},
        {"id": 1, "status": "active", ...},
        ...
    ]
}
```

## Integrating Real Camera Data

### Update camera_api.py

Replace the test pattern with real camera data:

```python
def _get_real_module_data(self, module_id):
    """Get real data from camera hardware"""
    # Example: Query your camera communication system
    if self.camera_comm:
        # Request data from specific module
        raw_data = self.camera_comm.get_module_image(module_id)
        
        # Convert to numpy array if needed
        image_array = np.array(raw_data, dtype=np.uint8)
        
        # Reshape if necessary
        image_array = image_array.reshape((self.module_height, self.module_width))
        
        return image_array
    
    return self._generate_test_pattern(module_id)
```

### WebSocket Updates

For real-time updates, emit camera data via Socket.IO:

```python
# In your app.py
@socketio.on('request_camera_update')
def handle_camera_update(data):
    module_id = data.get('module_id', 0)
    image_data = camera_api.get_camera_image(module_id)
    emit('camera_update', image_data)
```

```javascript
// In camera_viz.js
socket.on('camera_update', function(data) {
    cameraViz.updateImage(
        new Uint8Array(data.image),
        data.width,
        data.height
    );
});
```

## Customization

### Add New Color Scales

In `camera_viz.js`, add to `applyColorScale()` method:

```javascript
case 'custom':
    // Your custom colormap
    const r = Math.floor(...);
    const g = Math.floor(...);
    const b = Math.floor(...);
    return { r, g, b };
```

### Modify Module Layout

Update hexagonal grid in `visualization.css`:

```css
.module-grid {
    grid-template-columns: repeat(4, 80px);  /* Adjust columns */
    /* Add custom positioning */
}
```

### Change Plot Ranges

In `monitoring.js`, modify plot layouts:

```javascript
yaxis: { 
    title: 'Temperature (°C)',
    range: [-30, 40]  // Adjust range
}
```

## Performance Tips

1. **Throttle Updates**: Don't update faster than display refresh rate
   ```javascript
   let lastUpdate = 0;
   const minInterval = 33; // ~30 FPS
   
   function updateCameraDisplay() {
       const now = Date.now();
       if (now - lastUpdate < minInterval) return;
       lastUpdate = now;
       // ... update logic
   }
   ```

2. **Use WebWorkers**: For heavy image processing
   ```javascript
   const worker = new Worker('image_processor.js');
   worker.postMessage({image: data});
   worker.onmessage = (e) => {
       cameraViz.updateImage(e.data);
   };
   ```

3. **Optimize Canvas**: Use `willReadFrequently` context attribute
   ```javascript
   const ctx = canvas.getContext('2d', { willReadFrequently: true });
   ```

## Troubleshooting

### Canvas Not Displaying
- Check browser console for JavaScript errors
- Verify Canvas element exists: `document.getElementById('cameraCanvas')`
- Check image data format (should be Uint8Array or regular array)

### Plots Not Updating
- Verify Plotly.js is loaded: `typeof Plotly !== 'undefined'`
- Check data format (x should be Date objects, y should be numbers)
- Look for errors in browser console

### Gauges Not Rendering
- Verify Chart.js is loaded: `typeof Chart !== 'undefined'`
- Check canvas elements exist
- Ensure values are within configured min/max ranges

### API Errors
- Check Flask logs for backend errors
- Verify API endpoints are registered: `flask routes`
- Test endpoints directly: `curl http://localhost:5003/api/camera/image?module=0`

## Testing

### Test with Sample Data

The system includes test pattern generators. To test:

1. Start the app without real camera connection
2. Navigate to Camera View tab
3. You should see generated test patterns
4. Try different modules and color scales

### Manual Testing

```bash
# Test API endpoints
curl http://localhost:5003/api/camera/image?module=0
curl http://localhost:5003/api/camera/modules

# Check response format
python3 -c "import requests; print(requests.get('http://localhost:5003/api/camera/image?module=0').json())"
```

## Examples

### Complete Integration Example

```python
# app.py
from flask import Flask, render_template
from flask_socketio import SocketIO
from sctcamsoft.slow_control_web.camera_api import CameraAPI, register_camera_routes
from sctcamsoft.lib_gui.camera_comm import CameraComm

app = Flask(__name__)
socketio = SocketIO(app)

# Initialize camera communication
camera_comm = CameraComm(host, input_port, output_port, header_length, commands)

# Initialize camera API
camera_api = CameraAPI(camera_comm)

# Register routes
register_camera_routes(app, camera_api)

@app.route('/')
def index():
    return render_template('index_with_viz.html')

# Real-time monitoring updates
@socketio.on('subscribe_monitoring')
def handle_monitoring_subscribe():
    while True:
        # Get current values from your system
        data = {
            'temperature': get_current_temperature(),
            'voltage': get_current_voltage(),
            'current': get_current_current()
        }
        socketio.emit('monitoring_update', data)
        socketio.sleep(1)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5003)
```

## Migration from Matplotlib

If you have existing matplotlib code:

### Before (matplotlib):
```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
ax.imshow(camera_data, cmap='hot')
plt.show()
```

### After (Web-based):
```python
# In Flask API
@app.route('/api/camera/image')
def get_image():
    return jsonify({
        'image': camera_data.tolist(),
        'width': camera_data.shape[1],
        'height': camera_data.shape[0]
    })
```

```javascript
// In browser
cameraViz.updateImage(imageData, width, height);
cameraViz.setColorScale('hot');
```

## Support

For issues or questions:
1. Check browser console for JavaScript errors
2. Check Flask logs for backend errors
3. Review API responses with browser DevTools Network tab
4. Test endpoints individually with curl

## License

Same license as parent SCT Camera Software project.
