# SCT Camera Structure Documentation

## Overview

The SCT (Schwarzschild-Couder Telescope) camera consists of 9 backplanes arranged in a 3×3 matrix, with each backplane containing 25 modules arranged in a 5×5 matrix, for a total of **225 modules**.

## Physical Structure

### Backplane Layout (3×3)

```
┌─────────┬─────────┬─────────┐
│   BP 0  │   BP 1  │   BP 2  │
│  (0,0)  │  (0,1)  │  (0,2)  │
├─────────┼─────────┼─────────┤
│   BP 3  │   BP 4  │   BP 5  │
│  (1,0)  │  (1,1)  │  (1,2)  │
├─────────┼─────────┼─────────┤
│   BP 6  │   BP 7  │   BP 8  │
│  (2,0)  │  (2,1)  │  (2,2)  │
└─────────┴─────────┴─────────┘
```

### Module Layout per Backplane (5×5)

Each backplane contains 25 modules:

```
┌───┬───┬───┬───┬───┐
│ 0 │ 1 │ 2 │ 3 │ 4 │
├───┼───┼───┼───┼───┤
│ 5 │ 6 │ 7 │ 8 │ 9 │
├───┼───┼───┼───┼───┤
│10 │11 │12 │13 │14 │
├───┼───┼───┼───┼───┤
│15 │16 │17 │18 │19 │
├───┼───┼───┼───┼───┤
│20 │21 │22 │23 │24 │
└───┴───┴───┴───┴───┘
```

## Module Numbering

### Global Module ID

Modules are numbered from **0 to 224** (225 total).

The global module ID is calculated as:
```
module_id = backplane_id × 25 + module_in_backplane
```

### Examples

| Global ID | Backplane | Module in BP | BP Position | Module Position |
|-----------|-----------|--------------|-------------|------------------|
| 0         | 0         | 0            | (0,0)       | (0,0)            |
| 12        | 0         | 12           | (0,0)       | (2,2) - center   |
| 24        | 0         | 24           | (0,0)       | (4,4)            |
| 25        | 1         | 0            | (0,1)       | (0,0)            |
| 112       | 4         | 12           | (1,1)       | (2,2) - center   |
| 224       | 8         | 24           | (2,2)       | (4,4)            |

## Visualization

### Canvas Display

The camera is displayed on an HTML5 canvas with:

- **Module size**: 48×48 pixels per module
- **Backplane gap**: 12 pixels between backplanes
- **Grid lines**: 1px thin lines between modules
- **Backplane borders**: 3px thick cyan (#4ecdc4) lines around each backplane
- **Total canvas size**: ~780×780 pixels

### Visual Features

1. **Clear backplane separation**: 12-pixel gaps make the 3×3 backplane structure obvious
2. **Module grid**: Thin gray lines show the 5×5 module arrangement within each backplane
3. **Interactive selection**: Click any module to select it (highlighted in yellow)
4. **Hover info**: Mouse over shows module ID, backplane info, position, and temperature

## Temperature Simulation

### Realistic Simulation Features

The simulation mode generates realistic temperature patterns:

1. **Spatial correlation**: Nearby modules have similar temperatures
2. **Temporal variation**: Temperatures change slowly over time (wave patterns)
3. **Hot backplanes**: Backplanes 1, 4, and 7 run 2-5°C hotter
4. **Center hotspots**: Module centers in hot backplanes are warmest
5. **Edge cooling**: Modules on backplane edges are ~1.5°C cooler
6. **Random noise**: ±0.5°C noise added for realism

### Temperature Range

- **Base temperature**: 20°C
- **Normal range**: 10°C to 30°C
- **Hot backplane centers**: Up to 28°C
- **Cool edges**: Down to 15°C

### Update Rate

- **Simulation FPS**: 20 frames per second
- **Temperature updates**: Smooth transitions (90% old + 10% new)

## API Endpoints

### Get Camera Structure

```bash
GET /api/camera/structure
```

Returns:
```json
{
  "num_backplanes": 9,
  "backplane_arrangement": "3x3",
  "modules_per_backplane": 25,
  "module_arrangement": "5x5",
  "total_modules": 225,
  "module_dimensions": {
    "width": 48,
    "height": 48
  }
}
```

### Get Module Info

```bash
GET /api/camera/module/<module_id>
```

Example for module 112:
```json
{
  "info": {
    "id": 112,
    "backplane_id": 4,
    "module_in_backplane": 12,
    "backplane_position": {"row": 1, "col": 1},
    "module_position": {"row": 2, "col": 2},
    "status": "active",
    "temperature": 22.5,
    "voltage": 5.0,
    "current": 2.5
  },
  "image": [...],
  "width": 48,
  "height": 48
}
```

### Get All Modules in Backplane

```bash
GET /api/camera/backplane/<backplane_id>
```

Returns all 25 modules for the specified backplane (0-8).

### Get All Modules

```bash
GET /api/camera/modules
```

Returns information for all 225 modules.

## Color Scales

Three color scales are available for temperature visualization:

### 1. Grayscale
- Cold (low values): Black
- Hot (high values): White
- Good for: High contrast, clear detail

### 2. Hot
- Cold: Black
- Warm: Red
- Warmer: Yellow  
- Hot: White
- Good for: Intuitive temperature visualization (like thermal camera)

### 3. Viridis
- Cold: Dark purple/blue
- Medium: Green
- Hot: Yellow
- Good for: Colorblind-friendly, perceptually uniform

## Module Selection

Modules can be selected in three ways:

1. **Click on canvas**: Click any module to select it
2. **Dropdown menu**: Use "Module" selector (shows all 225 modules)
3. **API call**: Programmatically select via JavaScript

### Selection Display

Selected module shows:
- **Yellow highlight border**: 3px yellow (#ffe66d) rectangle around module
- **Info display**: Module ID, backplane, position, and temperature
- **Dropdown sync**: Module selector updates automatically

## Usage Tips

### Finding a Specific Module

1. Use the dropdown: Shows format "Module X (BP Y, Mod Z)"
2. Calculate position:
   - Backplane = module_id ÷ 25
   - Module in BP = module_id mod 25
3. Visual location:
   - Backplane row = backplane_id ÷ 3
   - Backplane col = backplane_id mod 3

### Identifying Hot Modules

1. Enable simulation mode
2. Select "Hot" color scale
3. Look for yellow/white modules (hottest)
4. Click on hot module to see exact temperature
5. Note backplane and position for investigation

### Comparing Backplanes

1. Enable simulation
2. Watch for patterns:
   - Center backplane (BP 4) often hottest
   - Edge backplanes (0, 2, 6, 8) coolest
   - Backplanes 1, 4, 7 run warmer in simulation

## Integration with Real Hardware

To connect to real camera hardware:

1. Update `camera_api.py` method `_get_real_module_data()`
2. Fetch data from your camera communication system
3. Map backplane and module IDs to your hardware addressing
4. Return temperature as float in Celsius
5. Return module image as 48×48 numpy array

See `VISUALIZATION_GUIDE.md` for detailed integration examples.

## Performance

- **Canvas updates**: 20 FPS in simulation mode
- **Memory usage**: ~50KB for temperature array (225 floats)
- **Render time**: <5ms per frame on modern browsers
- **Smooth on**: Desktop, tablets, modern phones

## Browser Compatibility

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+
- ⚠️ Internet Explorer: Not supported

## Troubleshooting

### Canvas shows black screen
- Check browser console for errors
- Verify JavaScript files loaded
- Click "Enable Simulation" to test

### Wrong module count
- Should be 225 modules (0-224)
- Check dropdown has all modules
- Verify API returns correct structure

### Gaps too large/small
- Adjust `backplaneGap` in camera_viz.js (default: 12px)
- Adjust `moduleSize` for larger/smaller modules (default: 48px)

### Grid lines not visible
- Check color scale (some make grid hard to see)
- Adjust `gridLineWidth` in camera_viz.js (default: 1px)
- Increase contrast between module colors

## Future Enhancements

Potential additions:

- [ ] Temperature scale legend with min/max values
- [ ] Backplane-level controls (select entire backplane)
- [ ] History/playback of temperature over time
- [ ] Export temperature map as image
- [ ] Overlay module labels (toggleable)
- [ ] Custom temperature thresholds and alerts
- [ ] Comparison mode (two time points side-by-side)
