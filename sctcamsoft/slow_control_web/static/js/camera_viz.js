/**
 * Camera Visualization Module
 * 
 * Handles Canvas-based camera display with proper SCT structure:
 * - 9 backplanes arranged in 3x3 matrix
 * - 25 modules per backplane (5x5 matrix)
 * - Total: 225 modules (numbered 0-224)
 * - Realistic temperature simulation with spatial/temporal patterns
 * - Interactive tooltip showing module info
 * - Temperature scale legend with color mapping
 * 
 * @module CameraVisualization
 * @author SCT Camera Team
 * @version 1.0.0
 * 
 * @example
 * // Initialize the camera visualization
 * const cameraViz = new CameraVisualization('cameraCanvas');
 * 
 * // Enable simulation mode
 * cameraViz.toggleSimulation();
 * 
 * // Change color scale
 * cameraViz.setColorScale('hot');
 * 
 * // Select a specific module
 * cameraViz.selectModule(112); // Center module of center backplane
 */

/**
 * Main class for camera visualization
 * 
 * Manages the entire camera display including rendering, interaction,
 * and simulation of temperature data across all 225 modules.
 */
class CameraVisualization {
    /**
     * Create a camera visualization instance
     * 
     * @param {string} canvasId - HTML ID of the canvas element to render on
     * 
     * @example
     * const viz = new CameraVisualization('cameraCanvas');
     */
    constructor(canvasId) {
        // Canvas and rendering context
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        
        // Visualization settings
        this.colorScale = 'grayscale';  // Current color scale: 'grayscale', 'hot', or 'viridis'
        this.currentModule = 0;  // Currently selected module ID
        this.imageData = null;  // Cached image data (future use)
        
        // Simulation control
        this.simulationMode = false;  // Whether simulation is active
        this.simulationInterval = null;  // Interval timer for animation
        this.simulationTime = 0;  // Elapsed simulation time in seconds
        
        // SCT Camera physical structure
        this.numBackplanes = 9;  // Total backplanes (3x3 arrangement)
        this.backplanesPerRow = 3;  // Backplanes per row/column
        this.modulesPerBackplane = 25;  // Modules per backplane (5x5 arrangement)
        this.modulesPerRow = 5;  // Modules per row/column within backplane
        this.totalModules = 225;  // Total number of modules
        
        // Visual rendering parameters (pixels)
        this.moduleSize = 48;  // Width/height of each module square
        this.backplaneGap = 12;  // Gap between backplanes for visual separation
        this.gridLineWidth = 1;  // Thin lines between modules
        this.backplaneLineWidth = 3;  // Thick cyan lines around backplanes
        
        // Temperature simulation parameters (Celsius)
        this.baseTemp = 20;  // Baseline temperature
        this.tempVariation = 10;  // Max deviation from baseline (+/-)
        this.minTemp = this.baseTemp - this.tempVariation;  // Minimum temp (10°C)
        this.maxTemp = this.baseTemp + this.tempVariation;  // Maximum temp (30°C)
        this.temperatures = new Array(this.totalModules).fill(this.baseTemp);  // Temperature array
        
        // UI elements
        this.tooltip = document.getElementById('cameraTooltip');  // Tooltip DOM element
        
        // Initialize
        this.setupCanvas();
        this.setupEventListeners();
        this.initTempScaleLegend();
    }

    /**
     * Setup canvas dimensions based on camera structure
     * 
     * Calculates the total canvas size needed to display all 225 modules
     * arranged in 9 backplanes with appropriate gaps.
     * 
     * Canvas size = (15 modules × 48px) + (2 gaps × 12px) = 780×780 px
     */
    setupCanvas() {
        // Calculate canvas size
        const modulesAcross = this.modulesPerRow * this.backplanesPerRow;  // 15 modules total
        const gapsAcross = this.backplanesPerRow - 1;  // 2 gaps between 3 backplanes
        
        this.canvas.width = modulesAcross * this.moduleSize + gapsAcross * this.backplaneGap;
        this.canvas.height = this.canvas.width;  // Square camera
        
        this.width = this.canvas.width;
        this.height = this.canvas.height;
    }

    /**
     * Setup mouse event listeners for interaction
     * 
     * Handles:
     * - Mouse move: Shows tooltip and updates info display
     * - Mouse leave: Hides tooltip
     * - Click: Selects module
     */
    setupEventListeners() {
        // Mouse hover for module info and tooltip
        this.canvas.addEventListener('mousemove', (e) => {
            // Convert screen coordinates to canvas coordinates
            const rect = this.canvas.getBoundingClientRect();
            const x = Math.floor((e.clientX - rect.left) * this.canvas.width / rect.width);
            const y = Math.floor((e.clientY - rect.top) * this.canvas.height / rect.height);
            
            // Show tooltip at cursor position
            this.showTooltip(e.clientX, e.clientY, x, y);
        });
        
        // Hide tooltip when leaving canvas
        this.canvas.addEventListener('mouseleave', () => {
            if (this.tooltip) {
                this.tooltip.style.display = 'none';
            }
            
            // Reset info display
            const infoElement = document.getElementById('pixelInfo');
            if (infoElement) {
                infoElement.textContent = 'Hover over modules for detailed information';
            }
        });
        
        // Click to select module
        this.canvas.addEventListener('click', (e) => {
            // Convert screen coordinates to canvas coordinates
            const rect = this.canvas.getBoundingClientRect();
            const x = Math.floor((e.clientX - rect.left) * this.canvas.width / rect.width);
            const y = Math.floor((e.clientY - rect.top) * this.canvas.height / rect.height);
            
            // Get module at click position and select it
            const moduleId = this.getModuleAtPosition(x, y);
            if (moduleId >= 0) {
                this.selectModule(moduleId);
            }
        });
    }

    /**
     * Show tooltip with module information at cursor position
     * 
     * @param {number} clientX - Mouse X position in viewport coordinates
     * @param {number} clientY - Mouse Y position in viewport coordinates
     * @param {number} canvasX - Mouse X position in canvas coordinates
     * @param {number} canvasY - Mouse Y position in canvas coordinates
     * 
     * @example
     * // Called automatically by mousemove event listener
     * this.showTooltip(500, 300, 240, 180);
     */
    showTooltip(clientX, clientY, canvasX, canvasY) {
        const moduleId = this.getModuleAtPosition(canvasX, canvasY);
        
        if (!this.tooltip) return;
        
        // If hovering over a valid module
        if (moduleId >= 0 && moduleId < this.totalModules) {
            const pos = this.getModulePosition(moduleId);
            const temp = this.temperatures[moduleId];
            
            // Update tooltip content
            document.getElementById('tooltipModuleId').textContent = moduleId;
            document.getElementById('tooltipBackplane').textContent = 
                `${pos.backplaneId} (${pos.bpRow},${pos.bpCol})`;
            document.getElementById('tooltipTemp').textContent = `${temp.toFixed(2)}°C`;
            
            // Position tooltip near cursor (offset to avoid covering module)
            this.tooltip.style.display = 'block';
            this.tooltip.style.left = (clientX + 15) + 'px';
            this.tooltip.style.top = (clientY + 15) + 'px';
            
            // Update info bar at bottom
            const infoElement = document.getElementById('pixelInfo');
            if (infoElement) {
                infoElement.textContent = `Module ${moduleId} | ` +
                    `Backplane ${pos.backplaneId} | ` +
                    `Position (${pos.modRow},${pos.modCol}) | ` +
                    `Temp: ${temp.toFixed(2)}°C`;
            }
        } else {
            // Hovering over gap between backplanes - hide tooltip
            this.tooltip.style.display = 'none';
            
            const infoElement = document.getElementById('pixelInfo');
            if (infoElement) {
                infoElement.textContent = 'Hover over modules for detailed information';
            }
        }
    }

    /**
     * Initialize temperature scale legend canvas
     * 
     * Sets up the temperature scale gradient bar that shows the
     * color mapping from minimum to maximum temperature.
     */
    initTempScaleLegend() {
        const scaleCanvas = document.getElementById('tempScaleCanvas');
        if (!scaleCanvas) return;
        
        this.scaleCtx = scaleCanvas.getContext('2d');
        this.updateTempScaleLegend();
    }

    /**
     * Update temperature scale legend with current color scale
     * 
     * Renders a horizontal gradient bar showing the full range of colors
     * from the current color scale (grayscale, hot, or viridis).
     * Also updates the temperature labels (min, mid, max).
     */
    updateTempScaleLegend() {
        if (!this.scaleCtx) return;
        
        const canvas = document.getElementById('tempScaleCanvas');
        const width = canvas.width;
        const height = canvas.height;
        
        // Draw gradient by rendering each column with appropriate color
        const imageData = this.scaleCtx.createImageData(width, height);
        
        for (let x = 0; x < width; x++) {
            // Map X position to 0-255 value range
            const value = Math.floor((x / width) * 255);
            const color = this.applyColorScale(value);
            
            // Fill entire column with this color
            for (let y = 0; y < height; y++) {
                const idx = (y * width + x) * 4;
                imageData.data[idx] = color.r;
                imageData.data[idx + 1] = color.g;
                imageData.data[idx + 2] = color.b;
                imageData.data[idx + 3] = 255;  // Full opacity
            }
        }
        
        this.scaleCtx.putImageData(imageData, 0, 0);
        
        // Update temperature labels below gradient
        document.getElementById('tempMin').textContent = `${this.minTemp.toFixed(0)}°C`;
        document.getElementById('tempMid').textContent = `${this.baseTemp.toFixed(0)}°C`;
        document.getElementById('tempMax').textContent = `${this.maxTemp.toFixed(0)}°C`;
    }

    /**
     * Get module ID from canvas pixel position
     * 
     * Converts canvas coordinates to module ID, accounting for the
     * 9 backplane structure and gaps between them.
     * 
     * @param {number} x - X coordinate in canvas pixels
     * @param {number} y - Y coordinate in canvas pixels
     * @returns {number} Module ID (0-224), or -1 if position is in a gap
     * 
     * @example
     * // Get module at canvas position (100, 100)
     * const moduleId = viz.getModuleAtPosition(100, 100);
     * if (moduleId >= 0) {
     *   console.log('Module', moduleId, 'is at this position');
     * }
     */
    getModuleAtPosition(x, y) {
        const sizeWithGap = this.modulesPerRow * this.moduleSize + this.backplaneGap;
        
        // Determine which backplane (3x3 grid)
        const bpCol = Math.floor(x / sizeWithGap);
        const bpRow = Math.floor(y / sizeWithGap);
        
        // Check if position is outside backplane grid
        if (bpCol >= this.backplanesPerRow || bpRow >= this.backplanesPerRow) {
            return -1;  // In gap
        }
        
        // Position within the backplane
        const xInBp = x - bpCol * sizeWithGap;
        const yInBp = y - bpRow * sizeWithGap;
        
        // Check if in gap between backplanes
        if (xInBp >= this.modulesPerRow * this.moduleSize || 
            yInBp >= this.modulesPerRow * this.moduleSize) {
            return -1;  // In gap
        }
        
        // Determine which module within backplane (5x5 grid)
        const modCol = Math.floor(xInBp / this.moduleSize);
        const modRow = Math.floor(yInBp / this.moduleSize);
        
        // Calculate global module ID
        const backplaneId = bpRow * this.backplanesPerRow + bpCol;
        const moduleInBp = modRow * this.modulesPerRow + modCol;
        
        return backplaneId * this.modulesPerBackplane + moduleInBp;
    }

    /**
     * Get canvas position and metadata for a module
     * 
     * Converts module ID to canvas position and calculates all related
     * position information (backplane location, position within backplane, etc.)
     * 
     * @param {number} moduleId - Module ID (0-224)
     * @returns {Object} Position information
     * @returns {number} return.x - Canvas X coordinate (pixels)
     * @returns {number} return.y - Canvas Y coordinate (pixels)
     * @returns {number} return.backplaneId - Backplane ID (0-8)
     * @returns {number} return.bpRow - Backplane row in 3x3 grid (0-2)
     * @returns {number} return.bpCol - Backplane column in 3x3 grid (0-2)
     * @returns {number} return.modRow - Module row within backplane (0-4)
     * @returns {number} return.modCol - Module column within backplane (0-4)
     * 
     * @example
     * // Get position of module 112 (center of center backplane)
     * const pos = viz.getModulePosition(112);
     * console.log(`Module at (${pos.x}, ${pos.y})`);
     * console.log(`Backplane ${pos.backplaneId} at (${pos.bpRow}, ${pos.bpCol})`);
     */
    getModulePosition(moduleId) {
        // Determine which backplane this module belongs to
        const backplaneId = Math.floor(moduleId / this.modulesPerBackplane);
        const moduleInBp = moduleId % this.modulesPerBackplane;
        
        // Backplane position in 3x3 grid
        const bpRow = Math.floor(backplaneId / this.backplanesPerRow);
        const bpCol = backplaneId % this.backplanesPerRow;
        
        // Module position within backplane's 5x5 grid
        const modRow = Math.floor(moduleInBp / this.modulesPerRow);
        const modCol = moduleInBp % this.modulesPerRow;
        
        // Calculate canvas pixel position
        const sizeWithGap = this.modulesPerRow * this.moduleSize + this.backplaneGap;
        const x = bpCol * sizeWithGap + modCol * this.moduleSize;
        const y = bpRow * sizeWithGap + modRow * this.moduleSize;
        
        return { x, y, backplaneId, bpRow, bpCol, modRow, modCol };
    }

    /**
     * Draw the entire camera with temperature data
     * 
     * Main rendering function that:
     * 1. Clears the canvas
     * 2. Draws all 225 modules with temperature-based colors
     * 3. Draws grid lines between modules
     * 4. Draws backplane borders
     * 5. Highlights the selected module
     */
    drawCamera() {
        // Clear canvas with dark background
        this.ctx.fillStyle = '#1a1a1a';
        this.ctx.fillRect(0, 0, this.width, this.height);
        
        // Draw all modules with their temperatures
        for (let i = 0; i < this.totalModules; i++) {
            const pos = this.getModulePosition(i);
            const temp = this.temperatures[i];
            
            // Map temperature to 0-255 range for colormap
            const normalized = (temp - this.minTemp) / (this.maxTemp - this.minTemp);
            const value = Math.floor(Math.max(0, Math.min(1, normalized)) * 255);
            
            // Get color from current color scale
            const color = this.applyColorScale(value);
            this.ctx.fillStyle = `rgb(${color.r}, ${color.g}, ${color.b})`;
            this.ctx.fillRect(pos.x, pos.y, this.moduleSize, this.moduleSize);
        }
        
        // Draw grid lines between modules
        this.drawGrid();
        
        // Highlight selected module with yellow border
        this.highlightModule(this.currentModule);
    }

    /**
     * Draw grid lines between modules and around backplanes
     * 
     * Draws two types of lines:
     * 1. Thin gray lines between modules within each backplane
     * 2. Thick cyan lines around each backplane border
     */
    drawGrid() {
        const sizeWithGap = this.modulesPerRow * this.moduleSize + this.backplaneGap;
        
        // Draw thin module grid lines within each backplane
        this.ctx.strokeStyle = '#666';
        this.ctx.lineWidth = this.gridLineWidth;
        
        for (let bpRow = 0; bpRow < this.backplanesPerRow; bpRow++) {
            for (let bpCol = 0; bpCol < this.backplanesPerRow; bpCol++) {
                const bpX = bpCol * sizeWithGap;
                const bpY = bpRow * sizeWithGap;
                const bpSize = this.modulesPerRow * this.moduleSize;
                
                // Draw vertical lines between columns
                for (let i = 1; i < this.modulesPerRow; i++) {
                    const x = bpX + i * this.moduleSize;
                    this.ctx.beginPath();
                    this.ctx.moveTo(x, bpY);
                    this.ctx.lineTo(x, bpY + bpSize);
                    this.ctx.stroke();
                }
                
                // Draw horizontal lines between rows
                for (let i = 1; i < this.modulesPerRow; i++) {
                    const y = bpY + i * this.moduleSize;
                    this.ctx.beginPath();
                    this.ctx.moveTo(bpX, y);
                    this.ctx.lineTo(bpX + bpSize, y);
                    this.ctx.stroke();
                }
            }
        }
        
        // Draw thick cyan lines around backplanes
        this.ctx.strokeStyle = '#4ecdc4';
        this.ctx.lineWidth = this.backplaneLineWidth;
        
        for (let bpRow = 0; bpRow < this.backplanesPerRow; bpRow++) {
            for (let bpCol = 0; bpCol < this.backplanesPerRow; bpCol++) {
                const x = bpCol * sizeWithGap;
                const y = bpRow * sizeWithGap;
                const size = this.modulesPerRow * this.moduleSize;
                
                this.ctx.strokeRect(x, y, size, size);
            }
        }
    }

    /**
     * Highlight selected module with yellow border
     * 
     * @param {number} moduleId - Module ID to highlight (0-224)
     */
    highlightModule(moduleId) {
        if (moduleId < 0 || moduleId >= this.totalModules) return;
        
        const pos = this.getModulePosition(moduleId);
        
        // Draw yellow highlight border with slight inset
        this.ctx.strokeStyle = '#ffe66d';
        this.ctx.lineWidth = 3;
        this.ctx.strokeRect(pos.x + 2, pos.y + 2, this.moduleSize - 4, this.moduleSize - 4);
    }

    /**
     * Apply color scale to value
     * 
     * Converts a 0-255 value to RGB color based on the current color scale.
     * 
     * @param {number} value - Value from 0-255 (0=cold, 255=hot)
     * @returns {Object} RGB color object
     * @returns {number} return.r - Red component (0-255)
     * @returns {number} return.g - Green component (0-255)
     * @returns {number} return.b - Blue component (0-255)
     * 
     * @example
     * const color = viz.applyColorScale(127); // Middle temperature
     * console.log(`RGB(${color.r}, ${color.g}, ${color.b})`);
     */
    applyColorScale(value) {
        const normalized = value / 255;  // 0-1 range
        
        switch (this.colorScale) {
            case 'grayscale':
                // Simple linear grayscale: black (0) to white (255)
                return { r: value, g: value, b: value };
            
            case 'hot':
                // Hot colormap: black -> red -> yellow -> white
                if (normalized < 0.33) {
                    // Black to red
                    const t = normalized / 0.33;
                    return { r: Math.floor(255 * t), g: 0, b: 0 };
                } else if (normalized < 0.67) {
                    // Red to yellow
                    const t = (normalized - 0.33) / 0.34;
                    return { r: 255, g: Math.floor(255 * t), b: 0 };
                } else {
                    // Yellow to white
                    const t = (normalized - 0.67) / 0.33;
                    return { r: 255, g: 255, b: Math.floor(255 * t) };
                }
            
            case 'viridis':
                // Viridis colormap: perceptually uniform, colorblind-friendly
                // Approximation using quadratic functions
                const r = Math.floor(255 * (0.267 + 0.529 * normalized - 0.796 * normalized * normalized));
                const g = Math.floor(255 * (-0.138 + 1.472 * normalized - 0.334 * normalized * normalized));
                const b = Math.floor(255 * (0.329 - 0.196 * normalized + 0.867 * normalized * normalized));
                return { 
                    r: Math.max(0, Math.min(255, r)), 
                    g: Math.max(0, Math.min(255, g)), 
                    b: Math.max(0, Math.min(255, b)) 
                };
            
            default:
                // Fallback to grayscale
                return { r: value, g: value, b: value };
        }
    }

    /**
     * Set color scale and update display
     * 
     * @param {string} scale - Color scale name: 'grayscale', 'hot', or 'viridis'
     * 
     * @example
     * viz.setColorScale('hot'); // Use hot colormap
     */
    setColorScale(scale) {
        this.colorScale = scale;
        this.updateTempScaleLegend();  // Update legend gradient
        this.drawCamera();  // Redraw with new colors
    }

    /**
     * Select a module and update UI
     * 
     * @param {number} moduleId - Module ID to select (0-224)
     * 
     * @example
     * viz.selectModule(112); // Select center module
     */
    selectModule(moduleId) {
        if (moduleId < 0 || moduleId >= this.totalModules) return;
        
        this.currentModule = moduleId;
        
        // Update dropdown selector
        const select = document.getElementById('moduleSelect');
        if (select) {
            select.value = moduleId;
        }
        
        // Redraw to show new selection highlight
        this.drawCamera();
    }

    /**
     * Toggle simulation mode on/off
     * 
     * Starts or stops the temperature simulation animation.
     * Updates button appearance and shows/hides simulation indicator.
     */
    toggleSimulation() {
        this.simulationMode = !this.simulationMode;
        
        const btn = document.getElementById('simulationBtn');
        const indicator = document.getElementById('simulationIndicator');
        
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
     * Start simulation animation
     * 
     * Begins updating temperatures at 20 FPS (every 50ms).
     * Simulation time increments by 0.05 seconds per frame.
     */
    startSimulation() {
        this.simulationTime = 0;
        this.simulationInterval = setInterval(() => {
            this.simulationTime += 0.05;
            this.updateSimulation();
            this.drawCamera();
        }, 50); // 20 FPS
    }

    /**
     * Stop simulation animation
     * 
     * Clears the animation interval timer.
     */
    stopSimulation() {
        if (this.simulationInterval) {
            clearInterval(this.simulationInterval);
            this.simulationInterval = null;
        }
    }

    /**
     * Update temperature simulation for all modules
     * 
     * Creates realistic temperature patterns with:
     * - Spatial correlation: Nearby modules have similar temperatures
     * - Temporal variation: Sinusoidal waves that evolve slowly over time
     * - Hot backplanes: Backplanes 1, 4, and 7 run 2-5°C warmer
     * - Center hotspots: Centers of hot backplanes are warmest
     * - Edge cooling: Edge modules are ~1.5°C cooler
     * - Random noise: ±0.5°C Gaussian noise for realism
     * - Smooth transitions: Exponential moving average (90% old + 10% new)
     * 
     * The simulation uses:
     * - Sin/cos waves for global temperature patterns
     * - Radial distance for hotspot effects
     * - Position-based adjustments for edge cooling
     */
    updateSimulation() {
        for (let i = 0; i < this.totalModules; i++) {
            const pos = this.getModulePosition(i);
            
            // Normalized positions (0-1) across entire camera
            const nx = (pos.bpCol * this.modulesPerRow + pos.modCol) / (this.modulesPerRow * this.backplanesPerRow);
            const ny = (pos.bpRow * this.modulesPerRow + pos.modRow) / (this.modulesPerRow * this.backplanesPerRow);
            
            // Start with base temperature
            let temp = this.baseTemp;
            
            // Add spatial patterns using sine waves
            temp += Math.sin(nx * Math.PI * 2 + this.simulationTime) * 3;
            temp += Math.cos(ny * Math.PI * 2 + this.simulationTime * 0.7) * 2;
            
            // Hotspot on specific backplanes (simulates higher power dissipation)
            const hotBackplanes = [1, 4, 7];  // Some backplanes run hotter
            if (hotBackplanes.includes(pos.backplaneId)) {
                // Create hotspot in center of backplane
                const dx = pos.modCol - 2;  // Distance from center (0-4 scale)
                const dy = pos.modRow - 2;
                const distFromCenter = Math.sqrt(dx * dx + dy * dy);
                temp += (2.5 - distFromCenter) * 2;  // Hotter in center
            }
            
            // Edge cooling effect (heat dissipation to surroundings)
            if (pos.bpCol === 0 || pos.bpCol === 2 || pos.bpRow === 0 || pos.bpRow === 2) {
                temp -= 1.5;  // Edge backplanes are cooler
            }
            
            // Add random noise for realism
            temp += (Math.random() - 0.5) * 0.5;
            
            // Smooth transition using exponential moving average
            // This prevents jarring temperature jumps
            this.temperatures[i] = this.temperatures[i] * 0.9 + temp * 0.1;
        }
    }
}

// ============================================================================
// GLOBAL FUNCTIONS
// ============================================================================

/**
 * Global camera visualization instance
 * @type {CameraVisualization}
 */
let cameraViz;

/**
 * Initialize camera visualization on page load
 * 
 * Creates the CameraVisualization instance, populates the module selector
 * dropdown, and performs initial render.
 */
function initCameraVisualization() {
    cameraViz = new CameraVisualization('cameraCanvas');
    populateModuleSelector();
    
    // Initial draw
    cameraViz.drawCamera();
}

/**
 * Populate module selector dropdown with all 225 modules
 * 
 * Creates options showing module ID, backplane ID, and module position
 * within the backplane.
 */
function populateModuleSelector() {
    const select = document.getElementById('moduleSelect');
    if (!select) return;
    
    select.innerHTML = '';
    
    // Add all 225 modules
    for (let i = 0; i < 225; i++) {
        const backplane = Math.floor(i / 25);
        const moduleInBp = i % 25;
        
        const option = document.createElement('option');
        option.value = i;
        option.textContent = `Module ${i} (BP ${backplane}, Mod ${moduleInBp})`;
        select.appendChild(option);
    }
}

/**
 * Update camera display with real data from server
 * 
 * Fetches current temperature data from the backend API and updates
 * the visualization. Only active when simulation mode is OFF.
 * 
 * @todo Implement API call to /api/camera/modules endpoint
 */
function updateCameraDisplay() {
    if (!cameraViz) return;
    
    if (!cameraViz.simulationMode) {
        // Fetch from server (to be implemented)
        console.log('Fetching real camera data...');
        // TODO: Implement fetch('/api/camera/modules')
    }
}

/**
 * Update color scale from dropdown selection
 * 
 * Called when user changes the color scale dropdown.
 */
function updateColorScale() {
    if (!cameraViz) return;
    const select = document.getElementById('colorScale');
    if (select) {
        cameraViz.setColorScale(select.value);
    }
}

/**
 * Select module from dropdown
 * 
 * Called when user changes the module selector dropdown.
 */
function selectModule() {
    if (!cameraViz) return;
    const select = document.getElementById('moduleSelect');
    if (select) {
        cameraViz.selectModule(parseInt(select.value));
    }
}

/**
 * Toggle simulation mode on/off
 * 
 * Called when user clicks the simulation button.
 */
function toggleSimulation() {
    if (!cameraViz) return;
    cameraViz.toggleSimulation();
}

// ============================================================================
// INITIALIZATION
// ============================================================================

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCameraVisualization);
} else {
    initCameraVisualization();
}
