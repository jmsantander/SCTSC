/**
 * Camera Visualization Module
 * Handles Canvas-based camera display with color scales and module views
 * Now includes simulation mode for testing without hardware
 */

class CameraVisualization {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.width = this.canvas.width;
        this.height = this.canvas.height;
        this.colorScale = 'grayscale';
        this.currentModule = 0;
        this.imageData = null;
        this.simulationMode = false;
        this.simulationInterval = null;
        this.simulationTime = 0;
        
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Mouse hover for pixel info
        this.canvas.addEventListener('mousemove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const x = Math.floor((e.clientX - rect.left) * this.canvas.width / rect.width);
            const y = Math.floor((e.clientY - rect.top) * this.canvas.height / rect.height);
            this.showPixelInfo(x, y);
        });
    }

    /**
     * Update camera display with new image data
     * @param {Uint8Array|Array} data - Image pixel data
     * @param {number} width - Image width
     * @param {number} height - Image height
     */
    updateImage(data, width, height) {
        // Resize canvas if needed
        if (this.canvas.width !== width || this.canvas.height !== height) {
            this.canvas.width = width;
            this.canvas.height = height;
            this.width = width;
            this.height = height;
        }

        // Store raw data
        this.imageData = data;
        
        // Create ImageData object
        const imgData = this.ctx.createImageData(width, height);
        
        // Apply color scale
        for (let i = 0; i < data.length; i++) {
            const value = data[i];
            const color = this.applyColorScale(value);
            const idx = i * 4;
            imgData.data[idx] = color.r;
            imgData.data[idx + 1] = color.g;
            imgData.data[idx + 2] = color.b;
            imgData.data[idx + 3] = 255; // Alpha
        }
        
        // Draw to canvas
        this.ctx.putImageData(imgData, 0, 0);
    }

    /**
     * Apply color scale to value
     * @param {number} value - Pixel value (0-255)
     * @returns {Object} RGB color object
     */
    applyColorScale(value) {
        const normalized = value / 255;
        
        switch (this.colorScale) {
            case 'grayscale':
                return { r: value, g: value, b: value };
            
            case 'hot':
                // Hot colormap (black -> red -> yellow -> white)
                if (normalized < 0.33) {
                    const t = normalized / 0.33;
                    return { r: Math.floor(255 * t), g: 0, b: 0 };
                } else if (normalized < 0.67) {
                    const t = (normalized - 0.33) / 0.34;
                    return { r: 255, g: Math.floor(255 * t), b: 0 };
                } else {
                    const t = (normalized - 0.67) / 0.33;
                    return { r: 255, g: 255, b: Math.floor(255 * t) };
                }
            
            case 'viridis':
                // Simplified viridis colormap
                const r = Math.floor(255 * (0.267 + 0.529 * normalized - 0.796 * normalized * normalized));
                const g = Math.floor(255 * (-0.138 + 1.472 * normalized - 0.334 * normalized * normalized));
                const b = Math.floor(255 * (0.329 - 0.196 * normalized + 0.867 * normalized * normalized));
                return { r: Math.max(0, Math.min(255, r)), 
                        g: Math.max(0, Math.min(255, g)), 
                        b: Math.max(0, Math.min(255, b)) };
            
            default:
                return { r: value, g: value, b: value };
        }
    }

    /**
     * Show pixel value information
     * @param {number} x - X coordinate
     * @param {number} y - Y coordinate
     */
    showPixelInfo(x, y) {
        if (!this.imageData || x < 0 || y < 0 || x >= this.width || y >= this.height) {
            return;
        }
        
        const idx = y * this.width + x;
        const value = this.imageData[idx];
        
        const infoElement = document.getElementById('pixelInfo');
        if (infoElement) {
            infoElement.textContent = `Pixel (${x}, ${y}): ${value}`;
        }
    }

    /**
     * Set color scale
     * @param {string} scale - Color scale name
     */
    setColorScale(scale) {
        this.colorScale = scale;
        // Redraw with new color scale
        if (this.imageData) {
            this.updateImage(this.imageData, this.width, this.height);
        }
    }

    /**
     * Draw hexagonal module layout
     * @param {Array} modules - Array of module objects with {id, x, y, status}
     */
    drawModuleLayout(modules) {
        const moduleGrid = document.getElementById('moduleGrid');
        if (!moduleGrid) return;
        
        moduleGrid.innerHTML = '';
        
        modules.forEach(module => {
            const hexagon = this.createHexagon(module);
            moduleGrid.appendChild(hexagon);
        });
    }

    /**
     * Create hexagonal module element
     * @param {Object} module - Module data
     * @returns {HTMLElement} Hexagon element
     */
    createHexagon(module) {
        const hex = document.createElement('div');
        hex.className = `module-hexagon ${module.status}`;
        hex.dataset.moduleId = module.id;
        hex.style.gridColumn = module.x;
        hex.style.gridRow = module.y;
        
        hex.innerHTML = `
            <div class="hex-content">
                <div class="module-id">${module.id}</div>
                <div class="module-status-text">${module.status}</div>
            </div>
        `;
        
        hex.onclick = () => this.selectModule(module.id);
        
        return hex;
    }

    /**
     * Select a module to display
     * @param {number} moduleId - Module ID
     */
    selectModule(moduleId) {
        this.currentModule = moduleId;
        console.log(`Selected module: ${moduleId}`);
        
        if (this.simulationMode) {
            // Generate simulation data immediately
            const data = this.generateSimulationData();
            this.updateImage(data, this.width, this.height);
        } else {
            // Request module data from server
            fetch(`/api/camera/module/${moduleId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.image) {
                        this.updateImage(data.image, data.width, data.height);
                    }
                })
                .catch(error => console.error('Error loading module data:', error));
        }
    }

    /**
     * Toggle simulation mode
     */
    toggleSimulation() {
        this.simulationMode = !this.simulationMode;
        
        const btn = document.getElementById('simulationBtn');
        const indicator = document.getElementById('simulationIndicator');
        
        if (this.simulationMode) {
            btn.textContent = 'Disable Simulation';
            btn.classList.add('active');
            indicator.style.display = 'inline-block';
            this.startSimulation();
        } else {
            btn.textContent = 'Enable Simulation';
            btn.classList.remove('active');
            indicator.style.display = 'none';
            this.stopSimulation();
        }
    }

    /**
     * Start simulation mode
     */
    startSimulation() {
        this.simulationTime = 0;
        this.simulationInterval = setInterval(() => {
            this.simulationTime += 0.1;
            const data = this.generateSimulationData();
            this.updateImage(data, this.width, this.height);
        }, 100); // Update 10 times per second
    }

    /**
     * Stop simulation mode
     */
    stopSimulation() {
        if (this.simulationInterval) {
            clearInterval(this.simulationInterval);
            this.simulationInterval = null;
        }
    }

    /**
     * Generate animated simulation data
     * @returns {Uint8Array} Simulated pixel data
     */
    generateSimulationData() {
        const data = new Uint8Array(this.width * this.height);
        
        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                const idx = y * this.width + x;
                
                // Normalized coordinates (-1 to 1)
                const nx = (x / this.width) * 2 - 1;
                const ny = (y / this.height) * 2 - 1;
                
                // Different patterns based on module
                let value;
                switch (this.currentModule % 4) {
                    case 0:
                        // Animated radial waves
                        const r = Math.sqrt(nx * nx + ny * ny);
                        value = (Math.sin(r * 10 - this.simulationTime * 5) + 1) * 0.5;
                        break;
                    
                    case 1:
                        // Moving interference pattern
                        value = (Math.sin(nx * 8 + this.simulationTime) * 
                                Math.cos(ny * 8 + this.simulationTime) + 1) * 0.5;
                        break;
                    
                    case 2:
                        // Rotating spiral
                        const angle = Math.atan2(ny, nx);
                        const radius = Math.sqrt(nx * nx + ny * ny);
                        value = (Math.sin(angle * 5 + radius * 10 - this.simulationTime * 3) + 1) * 0.5;
                        break;
                    
                    case 3:
                        // Plasma effect
                        value = (Math.sin(nx * 5 + this.simulationTime) +
                                Math.sin(ny * 6 + this.simulationTime * 1.3) +
                                Math.sin((nx + ny) * 4 + this.simulationTime * 0.8) +
                                Math.sin(Math.sqrt(nx * nx + ny * ny) * 8 + this.simulationTime * 2)) / 4 * 0.5 + 0.5;
                        break;
                    
                    default:
                        value = 0.5;
                }
                
                // Add some noise
                value += (Math.random() - 0.5) * 0.1;
                
                // Clamp and convert to 0-255
                data[idx] = Math.floor(Math.max(0, Math.min(1, value)) * 255);
            }
        }
        
        return data;
    }
}

// Initialize camera visualization
let cameraViz;

function initCameraVisualization() {
    cameraViz = new CameraVisualization('cameraCanvas');
    
    // Populate module selector
    populateModuleSelector();
    
    // Set up periodic updates (only when not in simulation mode)
    setInterval(() => {
        if (!cameraViz.simulationMode) {
            updateCameraDisplay();
        }
    }, 1000);
}

function populateModuleSelector() {
    const select = document.getElementById('moduleSelect');
    if (!select) return;
    
    // Example: 11 modules for SCT camera
    for (let i = 0; i < 11; i++) {
        const option = document.createElement('option');
        option.value = i;
        option.textContent = `Module ${i}`;
        select.appendChild(option);
    }
}

function updateCameraDisplay() {
    if (!cameraViz) return;
    
    if (cameraViz.simulationMode) {
        // Already updating in simulation mode
        return;
    }
    
    // Fetch latest camera image
    fetch(`/api/camera/image?module=${cameraViz.currentModule}`)
        .then(response => response.json())
        .then(data => {
            if (data.image) {
                cameraViz.updateImage(
                    new Uint8Array(data.image),
                    data.width,
                    data.height
                );
            }
        })
        .catch(error => console.error('Error updating camera:', error));
}

function updateColorScale() {
    if (!cameraViz) return;
    const select = document.getElementById('colorScale');
    if (select) {
        cameraViz.setColorScale(select.value);
    }
}

function selectModule() {
    if (!cameraViz) return;
    const select = document.getElementById('moduleSelect');
    if (select) {
        cameraViz.selectModule(parseInt(select.value));
    }
}

function toggleSimulation() {
    if (!cameraViz) return;
    cameraViz.toggleSimulation();
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCameraVisualization);
} else {
    initCameraVisualization();
}
