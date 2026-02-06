/**
 * Camera Visualization Module
 * Handles Canvas-based camera display with proper SCT structure:
 * - 9 backplanes arranged in 3x3 matrix
 * - 25 modules per backplane (5x5 matrix)
 * - Total: 225 modules
 * - Realistic temperature simulation
 * - Interactive tooltip
 * - Temperature scale legend
 */

class CameraVisualization {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.colorScale = 'grayscale';
        this.currentModule = 0;
        this.imageData = null;
        this.simulationMode = false;
        this.simulationInterval = null;
        this.simulationTime = 0;
        
        // SCT Camera structure
        this.numBackplanes = 9;  // 3x3 arrangement
        this.backplanesPerRow = 3;
        this.modulesPerBackplane = 25;  // 5x5 arrangement
        this.modulesPerRow = 5;
        this.totalModules = 225;
        
        // Visual parameters
        this.moduleSize = 48;  // pixels per module
        this.backplaneGap = 12;  // gap between backplanes
        this.gridLineWidth = 1;  // module grid lines
        this.backplaneLineWidth = 3;  // backplane separation lines
        
        // Temperature simulation parameters
        this.baseTemp = 20;  // Base temperature in Celsius
        this.tempVariation = 10;  // Temperature variation range
        this.minTemp = this.baseTemp - this.tempVariation;
        this.maxTemp = this.baseTemp + this.tempVariation;
        this.temperatures = new Array(this.totalModules).fill(this.baseTemp);
        
        // Tooltip
        this.tooltip = document.getElementById('cameraTooltip');
        
        this.setupCanvas();
        this.setupEventListeners();
        this.initTempScaleLegend();
    }

    setupCanvas() {
        // Calculate canvas size
        const modulesAcross = this.modulesPerRow * this.backplanesPerRow;
        const gapsAcross = this.backplanesPerRow - 1;
        this.canvas.width = modulesAcross * this.moduleSize + gapsAcross * this.backplaneGap;
        this.canvas.height = this.canvas.width;  // Square camera
        
        this.width = this.canvas.width;
        this.height = this.canvas.height;
    }

    setupEventListeners() {
        // Mouse hover for module info and tooltip
        this.canvas.addEventListener('mousemove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const x = Math.floor((e.clientX - rect.left) * this.canvas.width / rect.width);
            const y = Math.floor((e.clientY - rect.top) * this.canvas.height / rect.height);
            this.showTooltip(e.clientX, e.clientY, x, y);
        });
        
        // Hide tooltip when leaving canvas
        this.canvas.addEventListener('mouseleave', () => {
            if (this.tooltip) {
                this.tooltip.style.display = 'none';
            }
            const infoElement = document.getElementById('pixelInfo');
            if (infoElement) {
                infoElement.textContent = 'Hover over modules for detailed information';
            }
        });
        
        // Click to select module
        this.canvas.addEventListener('click', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const x = Math.floor((e.clientX - rect.left) * this.canvas.width / rect.width);
            const y = Math.floor((e.clientY - rect.top) * this.canvas.height / rect.height);
            const moduleId = this.getModuleAtPosition(x, y);
            if (moduleId >= 0) {
                this.selectModule(moduleId);
            }
        });
    }

    /**
     * Show tooltip with module information
     */
    showTooltip(clientX, clientY, canvasX, canvasY) {
        const moduleId = this.getModuleAtPosition(canvasX, canvasY);
        
        if (!this.tooltip) return;
        
        if (moduleId >= 0 && moduleId < this.totalModules) {
            const pos = this.getModulePosition(moduleId);
            const temp = this.temperatures[moduleId];
            
            // Update tooltip content
            document.getElementById('tooltipModuleId').textContent = moduleId;
            document.getElementById('tooltipBackplane').textContent = 
                `${pos.backplaneId} (${pos.bpRow},${pos.bpCol})`;
            document.getElementById('tooltipTemp').textContent = `${temp.toFixed(2)}°C`;
            
            // Position tooltip
            this.tooltip.style.display = 'block';
            this.tooltip.style.left = (clientX + 15) + 'px';
            this.tooltip.style.top = (clientY + 15) + 'px';
            
            // Update info bar
            const infoElement = document.getElementById('pixelInfo');
            if (infoElement) {
                infoElement.textContent = `Module ${moduleId} | ` +
                    `Backplane ${pos.backplaneId} | ` +
                    `Position (${pos.modRow},${pos.modCol}) | ` +
                    `Temp: ${temp.toFixed(2)}°C`;
            }
        } else {
            this.tooltip.style.display = 'none';
            const infoElement = document.getElementById('pixelInfo');
            if (infoElement) {
                infoElement.textContent = 'Hover over modules for detailed information';
            }
        }
    }

    /**
     * Initialize temperature scale legend
     */
    initTempScaleLegend() {
        const scaleCanvas = document.getElementById('tempScaleCanvas');
        if (!scaleCanvas) return;
        
        this.scaleCtx = scaleCanvas.getContext('2d');
        this.updateTempScaleLegend();
    }

    /**
     * Update temperature scale legend
     */
    updateTempScaleLegend() {
        if (!this.scaleCtx) return;
        
        const canvas = document.getElementById('tempScaleCanvas');
        const width = canvas.width;
        const height = canvas.height;
        
        // Draw gradient
        const imageData = this.scaleCtx.createImageData(width, height);
        
        for (let x = 0; x < width; x++) {
            const value = Math.floor((x / width) * 255);
            const color = this.applyColorScale(value);
            
            for (let y = 0; y < height; y++) {
                const idx = (y * width + x) * 4;
                imageData.data[idx] = color.r;
                imageData.data[idx + 1] = color.g;
                imageData.data[idx + 2] = color.b;
                imageData.data[idx + 3] = 255;
            }
        }
        
        this.scaleCtx.putImageData(imageData, 0, 0);
        
        // Update labels
        document.getElementById('tempMin').textContent = `${this.minTemp.toFixed(0)}°C`;
        document.getElementById('tempMid').textContent = `${this.baseTemp.toFixed(0)}°C`;
        document.getElementById('tempMax').textContent = `${this.maxTemp.toFixed(0)}°C`;
    }

    /**
     * Get module ID from canvas position
     */
    getModuleAtPosition(x, y) {
        const sizeWithGap = this.modulesPerRow * this.moduleSize + this.backplaneGap;
        
        // Which backplane (3x3)
        const bpCol = Math.floor(x / sizeWithGap);
        const bpRow = Math.floor(y / sizeWithGap);
        
        if (bpCol >= this.backplanesPerRow || bpRow >= this.backplanesPerRow) {
            return -1;  // In gap
        }
        
        // Position within backplane
        const xInBp = x - bpCol * sizeWithGap;
        const yInBp = y - bpRow * sizeWithGap;
        
        // Check if in gap
        if (xInBp >= this.modulesPerRow * this.moduleSize || 
            yInBp >= this.modulesPerRow * this.moduleSize) {
            return -1;
        }
        
        // Which module within backplane (5x5)
        const modCol = Math.floor(xInBp / this.moduleSize);
        const modRow = Math.floor(yInBp / this.moduleSize);
        
        const backplaneId = bpRow * this.backplanesPerRow + bpCol;
        const moduleInBp = modRow * this.modulesPerRow + modCol;
        
        return backplaneId * this.modulesPerBackplane + moduleInBp;
    }

    /**
     * Get canvas position for a module
     */
    getModulePosition(moduleId) {
        const backplaneId = Math.floor(moduleId / this.modulesPerBackplane);
        const moduleInBp = moduleId % this.modulesPerBackplane;
        
        const bpRow = Math.floor(backplaneId / this.backplanesPerRow);
        const bpCol = backplaneId % this.backplanesPerRow;
        
        const modRow = Math.floor(moduleInBp / this.modulesPerRow);
        const modCol = moduleInBp % this.modulesPerRow;
        
        const sizeWithGap = this.modulesPerRow * this.moduleSize + this.backplaneGap;
        
        const x = bpCol * sizeWithGap + modCol * this.moduleSize;
        const y = bpRow * sizeWithGap + modRow * this.moduleSize;
        
        return { x, y, backplaneId, bpRow, bpCol, modRow, modCol };
    }

    /**
     * Draw the entire camera with temperature data
     */
    drawCamera() {
        // Clear canvas
        this.ctx.fillStyle = '#1a1a1a';
        this.ctx.fillRect(0, 0, this.width, this.height);
        
        // Draw all modules with their temperatures
        for (let i = 0; i < this.totalModules; i++) {
            const pos = this.getModulePosition(i);
            const temp = this.temperatures[i];
            
            // Map temperature to 0-255 range for colormap
            const normalized = (temp - this.minTemp) / (this.maxTemp - this.minTemp);
            const value = Math.floor(Math.max(0, Math.min(1, normalized)) * 255);
            
            // Get color
            const color = this.applyColorScale(value);
            this.ctx.fillStyle = `rgb(${color.r}, ${color.g}, ${color.b})`;
            this.ctx.fillRect(pos.x, pos.y, this.moduleSize, this.moduleSize);
        }
        
        // Draw grid lines between modules
        this.drawGrid();
        
        // Highlight selected module
        this.highlightModule(this.currentModule);
    }

    /**
     * Draw grid lines
     */
    drawGrid() {
        this.ctx.strokeStyle = '#666';
        this.ctx.lineWidth = this.gridLineWidth;
        
        const sizeWithGap = this.modulesPerRow * this.moduleSize + this.backplaneGap;
        
        // Draw module grid lines within each backplane
        for (let bpRow = 0; bpRow < this.backplanesPerRow; bpRow++) {
            for (let bpCol = 0; bpCol < this.backplanesPerRow; bpCol++) {
                const bpX = bpCol * sizeWithGap;
                const bpY = bpRow * sizeWithGap;
                const bpSize = this.modulesPerRow * this.moduleSize;
                
                // Vertical lines
                for (let i = 1; i < this.modulesPerRow; i++) {
                    const x = bpX + i * this.moduleSize;
                    this.ctx.beginPath();
                    this.ctx.moveTo(x, bpY);
                    this.ctx.lineTo(x, bpY + bpSize);
                    this.ctx.stroke();
                }
                
                // Horizontal lines
                for (let i = 1; i < this.modulesPerRow; i++) {
                    const y = bpY + i * this.moduleSize;
                    this.ctx.beginPath();
                    this.ctx.moveTo(bpX, y);
                    this.ctx.lineTo(bpX + bpSize, y);
                    this.ctx.stroke();
                }
            }
        }
        
        // Draw thick lines around backplanes
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
     * Highlight selected module
     */
    highlightModule(moduleId) {
        if (moduleId < 0 || moduleId >= this.totalModules) return;
        
        const pos = this.getModulePosition(moduleId);
        
        // Draw highlight border
        this.ctx.strokeStyle = '#ffe66d';
        this.ctx.lineWidth = 3;
        this.ctx.strokeRect(pos.x + 2, pos.y + 2, this.moduleSize - 4, this.moduleSize - 4);
    }

    /**
     * Apply color scale to value
     */
    applyColorScale(value) {
        const normalized = value / 255;
        
        switch (this.colorScale) {
            case 'grayscale':
                return { r: value, g: value, b: value };
            
            case 'hot':
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
     * Set color scale
     */
    setColorScale(scale) {
        this.colorScale = scale;
        this.updateTempScaleLegend();
        this.drawCamera();
    }

    /**
     * Select a module
     */
    selectModule(moduleId) {
        if (moduleId < 0 || moduleId >= this.totalModules) return;
        
        this.currentModule = moduleId;
        
        // Update selector
        const select = document.getElementById('moduleSelect');
        if (select) {
            select.value = moduleId;
        }
        
        this.drawCamera();
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
     * Start simulation
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
     * Stop simulation
     */
    stopSimulation() {
        if (this.simulationInterval) {
            clearInterval(this.simulationInterval);
            this.simulationInterval = null;
        }
    }

    /**
     * Update temperature simulation
     * Creates realistic temperature patterns with:
     * - Spatial correlation (nearby modules have similar temps)
     * - Temporal variation (slow changes)
     * - Random noise
     * - Hotspots on some backplanes
     */
    updateSimulation() {
        for (let i = 0; i < this.totalModules; i++) {
            const pos = this.getModulePosition(i);
            
            // Normalized positions (0-1)
            const nx = (pos.bpCol * this.modulesPerRow + pos.modCol) / (this.modulesPerRow * this.backplanesPerRow);
            const ny = (pos.bpRow * this.modulesPerRow + pos.modRow) / (this.modulesPerRow * this.backplanesPerRow);
            
            // Base temperature with gradient
            let temp = this.baseTemp;
            
            // Add spatial patterns
            temp += Math.sin(nx * Math.PI * 2 + this.simulationTime) * 3;
            temp += Math.cos(ny * Math.PI * 2 + this.simulationTime * 0.7) * 2;
            
            // Hotspot on specific backplanes
            const hotBackplanes = [1, 4, 7];  // Some backplanes run hotter
            if (hotBackplanes.includes(pos.backplaneId)) {
                // Hotspot in center of backplane
                const dx = pos.modCol - 2;  // Distance from center
                const dy = pos.modRow - 2;
                const distFromCenter = Math.sqrt(dx * dx + dy * dy);
                temp += (2.5 - distFromCenter) * 2;
            }
            
            // Edge cooling effect
            if (pos.bpCol === 0 || pos.bpCol === 2 || pos.bpRow === 0 || pos.bpRow === 2) {
                temp -= 1.5;
            }
            
            // Add some noise
            temp += (Math.random() - 0.5) * 0.5;
            
            // Smooth transition
            this.temperatures[i] = this.temperatures[i] * 0.9 + temp * 0.1;
        }
    }
}

// Global instance
let cameraViz;

function initCameraVisualization() {
    cameraViz = new CameraVisualization('cameraCanvas');
    populateModuleSelector();
    
    // Initial draw
    cameraViz.drawCamera();
}

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

function updateCameraDisplay() {
    if (!cameraViz) return;
    
    if (!cameraViz.simulationMode) {
        // Fetch from server (to be implemented)
        console.log('Fetching real camera data...');
    }
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
