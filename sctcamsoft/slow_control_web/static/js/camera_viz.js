/**
 * Camera Visualization Module
 * 
 * Handles Canvas-based camera display with proper SCT structure.
 * Now supports multiple data types: temperature, voltage, current, and status.
 * Responsive canvas sizing.
 * Circular aperture created by removing corner modules.
 * 
 * @module CameraVisualization
 * @author SCT Camera Team
 * @version 2.3.0
 */

class CameraVisualization {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            console.warn('Camera canvas not found, delaying initialization');
            return;
        }
        
        this.ctx = this.canvas.getContext('2d');
        this.colorScale = 'hot';
        this.currentModule = 0;
        this.imageData = null;
        this.simulationMode = false;
        this.simulationInterval = null;
        this.simulationTime = 0;
        
        // Current data type being displayed
        this.dataType = 'temperature';
        
        // SCT Camera structure
        this.numBackplanes = 9;
        this.backplanesPerRow = 3;
        this.modulesPerBackplane = 25;
        this.modulesPerRow = 5;
        this.totalModules = 225;
        
        // Visual parameters - will be scaled based on container
        this.baseModuleSize = 64;
        this.baseBackplaneGap = 16;
        this.gridLineWidth = 1;
        this.backplaneLineWidth = 3;
        
        // Define which modules are inactive (removed for circular aperture)
        this.inactiveModules = this.defineInactiveModules();
        
        // Data arrays for each type
        this.temperatures = new Array(this.totalModules).fill(20);
        this.voltages = new Array(this.totalModules).fill(5.0);
        this.currents = new Array(this.totalModules).fill(2.5);
        this.statuses = new Array(this.totalModules).fill('active');
        
        // Value ranges for each data type
        this.ranges = {
            temperature: { min: 10, max: 30, unit: '°C', label: 'Temperature' },
            voltage: { min: 0, max: 12, unit: 'V', label: 'Voltage' },
            current: { min: 0, max: 5, unit: 'A', label: 'Current' },
            status: { values: ['active', 'warning', 'error', 'offline'], label: 'Status' }
        };
        
        this.tooltip = document.getElementById('cameraTooltip');
        
        this.setupCanvas();
        this.setupEventListeners();
        this.initTempScaleLegend();
        this.initialized = true;
        
        // Handle window resize
        window.addEventListener('resize', () => this.handleResize());
    }

    handleResize() {
        this.setupCanvas();
        this.drawCamera();
    }

    /**
     * Define which modules are inactive to create circular aperture
     */
    defineInactiveModules() {
        const inactive = new Set();
        
        const getModuleId = (backplaneId, row, col) => {
            return backplaneId * 25 + row * 5 + col;
        };
        
        // Top-left corner (backplane 0)
        for (let col = 0; col < 5; col++) inactive.add(getModuleId(0, 0, col));
        for (let col = 0; col < 3; col++) inactive.add(getModuleId(0, 1, col));
        for (let col = 0; col < 2; col++) inactive.add(getModuleId(0, 2, col));
        inactive.add(getModuleId(0, 3, 0));
        inactive.add(getModuleId(0, 4, 0));
        
        // Top-right corner (backplane 2)
        for (let col = 0; col < 5; col++) inactive.add(getModuleId(2, 0, col));
        for (let col = 2; col < 5; col++) inactive.add(getModuleId(2, 1, col));
        for (let col = 3; col < 5; col++) inactive.add(getModuleId(2, 2, col));
        inactive.add(getModuleId(2, 3, 4));
        inactive.add(getModuleId(2, 4, 4));
        
        // Bottom-left corner (backplane 6)
        inactive.add(getModuleId(6, 0, 0));
        inactive.add(getModuleId(6, 1, 0));
        for (let col = 0; col < 2; col++) inactive.add(getModuleId(6, 2, col));
        for (let col = 0; col < 3; col++) inactive.add(getModuleId(6, 3, col));
        for (let col = 0; col < 5; col++) inactive.add(getModuleId(6, 4, col));
        
        // Bottom-right corner (backplane 8)
        inactive.add(getModuleId(8, 0, 4));
        inactive.add(getModuleId(8, 1, 4));
        for (let col = 3; col < 5; col++) inactive.add(getModuleId(8, 2, col));
        for (let col = 2; col < 5; col++) inactive.add(getModuleId(8, 3, col));
        for (let col = 0; col < 5; col++) inactive.add(getModuleId(8, 4, col));
        
        return inactive;
    }

    isModuleActive(moduleId) {
        return !this.inactiveModules.has(moduleId);
    }

    setupCanvas() {
        // Get container width and calculate appropriate size
        const container = this.canvas.parentElement;
        const maxWidth = Math.min(container.clientWidth - 40, 900);
        
        // Calculate module size to fit container
        const modulesAcross = this.modulesPerRow * this.backplanesPerRow;
        const gapsAcross = this.backplanesPerRow - 1;
        
        this.moduleSize = Math.floor((maxWidth - (gapsAcross * this.baseBackplaneGap)) / modulesAcross);
        this.backplaneGap = this.baseBackplaneGap;
        
        const canvasSize = modulesAcross * this.moduleSize + gapsAcross * this.backplaneGap;
        
        // Set canvas resolution
        this.canvas.width = canvasSize;
        this.canvas.height = canvasSize;
        
        // Also set CSS size for crisp rendering
        this.canvas.style.width = canvasSize + 'px';
        this.canvas.style.height = canvasSize + 'px';
        
        this.width = canvasSize;
        this.height = canvasSize;
    }

    setupEventListeners() {
        this.canvas.addEventListener('mousemove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const x = Math.floor((e.clientX - rect.left) * this.canvas.width / rect.width);
            const y = Math.floor((e.clientY - rect.top) * this.canvas.height / rect.height);
            this.showTooltip(e.clientX, e.clientY, x, y);
        });
        
        this.canvas.addEventListener('mouseleave', () => {
            if (this.tooltip) {
                this.tooltip.style.display = 'none';
            }
        });
        
        this.canvas.addEventListener('click', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const x = Math.floor((e.clientX - rect.left) * this.canvas.width / rect.width);
            const y = Math.floor((e.clientY - rect.top) * this.canvas.height / rect.height);
            const moduleId = this.getModuleAtPosition(x, y);
            if (moduleId >= 0 && this.isModuleActive(moduleId)) {
                this.selectModule(moduleId);
            }
        });
    }

    setDataType(type) {
        this.dataType = type;
        
        const tooltipLabel = document.getElementById('tooltipValueLabel');
        if (tooltipLabel) {
            tooltipLabel.textContent = this.ranges[type].label + ':';
        }
        
        this.updateTempScaleLegend();
        this.drawCamera();
    }

    showTooltip(clientX, clientY, canvasX, canvasY) {
        const moduleId = this.getModuleAtPosition(canvasX, canvasY);
        
        if (!this.tooltip) return;
        
        if (moduleId >= 0 && moduleId < this.totalModules && this.isModuleActive(moduleId)) {
            const pos = this.getModulePosition(moduleId);
            const value = this.getCurrentValue(moduleId);
            const unit = this.ranges[this.dataType].unit || '';
            
            const moduleIdEl = document.getElementById('tooltipModuleId');
            const backplaneEl = document.getElementById('tooltipBackplane');
            const valueEl = document.getElementById('tooltipValue');
            
            if (moduleIdEl) moduleIdEl.textContent = moduleId;
            if (backplaneEl) backplaneEl.textContent = `${pos.backplaneId} (${pos.bpRow},${pos.bpCol})`;
            
            if (valueEl) {
                if (this.dataType === 'status') {
                    valueEl.textContent = value.toUpperCase();
                } else {
                    valueEl.textContent = `${value.toFixed(2)} ${unit}`;
                }
            }
            
            this.tooltip.style.display = 'block';
            this.tooltip.style.left = (clientX + 15) + 'px';
            this.tooltip.style.top = (clientY + 15) + 'px';
        } else {
            this.tooltip.style.display = 'none';
        }
    }

    getCurrentValue(moduleId) {
        switch (this.dataType) {
            case 'temperature': return this.temperatures[moduleId];
            case 'voltage': return this.voltages[moduleId];
            case 'current': return this.currents[moduleId];
            case 'status': return this.statuses[moduleId];
            default: return 0;
        }
    }

    initTempScaleLegend() {
        const scaleCanvas = document.getElementById('tempScaleCanvas');
        if (!scaleCanvas) {
            console.warn('Temperature scale canvas not found');
            return;
        }
        this.scaleCtx = scaleCanvas.getContext('2d');
        this.updateTempScaleLegend();
    }

    updateTempScaleLegend() {
        if (!this.scaleCtx) return;
        
        const canvas = document.getElementById('tempScaleCanvas');
        if (!canvas) return;
        
        const width = canvas.width;
        const height = canvas.height;
        const imageData = this.scaleCtx.createImageData(width, height);
        
        for (let x = 0; x < width; x++) {
            const value = Math.floor((x / width) * 255);
            const color = this.dataType === 'status' ? 
                this.getStatusColor(['active', 'warning', 'error', 'offline'][Math.floor((x / width) * 4)]) :
                this.applyColorScale(value);
            
            for (let y = 0; y < height; y++) {
                const idx = (y * width + x) * 4;
                imageData.data[idx] = color.r;
                imageData.data[idx + 1] = color.g;
                imageData.data[idx + 2] = color.b;
                imageData.data[idx + 3] = 255;
            }
        }
        
        this.scaleCtx.putImageData(imageData, 0, 0);
        
        const range = this.ranges[this.dataType];
        const minEl = document.getElementById('scaleMin');
        const midEl = document.getElementById('scaleMid');
        const maxEl = document.getElementById('scaleMax');
        
        if (this.dataType === 'status') {
            if (minEl) minEl.textContent = 'Active';
            if (midEl) midEl.textContent = 'Warning';
            if (maxEl) maxEl.textContent = 'Error';
        } else {
            const unit = range.unit;
            if (minEl) minEl.textContent = `${range.min.toFixed(0)}${unit}`;
            if (midEl) midEl.textContent = `${((range.min + range.max) / 2).toFixed(0)}${unit}`;
            if (maxEl) maxEl.textContent = `${range.max.toFixed(0)}${unit}`;
        }
    }

    getModuleAtPosition(x, y) {
        const sizeWithGap = this.modulesPerRow * this.moduleSize + this.backplaneGap;
        const bpCol = Math.floor(x / sizeWithGap);
        const bpRow = Math.floor(y / sizeWithGap);
        
        if (bpCol >= this.backplanesPerRow || bpRow >= this.backplanesPerRow) {
            return -1;
        }
        
        const xInBp = x - bpCol * sizeWithGap;
        const yInBp = y - bpRow * sizeWithGap;
        
        if (xInBp >= this.modulesPerRow * this.moduleSize || 
            yInBp >= this.modulesPerRow * this.moduleSize) {
            return -1;
        }
        
        const modCol = Math.floor(xInBp / this.moduleSize);
        const modRow = Math.floor(yInBp / this.moduleSize);
        const backplaneId = bpRow * this.backplanesPerRow + bpCol;
        const moduleInBp = modRow * this.modulesPerRow + modCol;
        
        return backplaneId * this.modulesPerBackplane + moduleInBp;
    }

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

    drawCamera() {
        if (!this.canvas) return;
        
        this.ctx.fillStyle = '#0a0a0a';
        this.ctx.fillRect(0, 0, this.width, this.height);
        
        for (let i = 0; i < this.totalModules; i++) {
            if (!this.isModuleActive(i)) {
                const pos = this.getModulePosition(i);
                this.ctx.fillStyle = '#050505';
                this.ctx.fillRect(pos.x, pos.y, this.moduleSize, this.moduleSize);
                continue;
            }
            
            const pos = this.getModulePosition(i);
            const value = this.getCurrentValue(i);
            const color = this.getColorForValue(value);
            
            this.ctx.fillStyle = `rgb(${color.r}, ${color.g}, ${color.b})`;
            this.ctx.fillRect(pos.x, pos.y, this.moduleSize, this.moduleSize);
        }
        
        this.drawGrid();
        this.highlightModule(this.currentModule);
    }

    getColorForValue(value) {
        if (this.dataType === 'status') {
            return this.getStatusColor(value);
        } else {
            const range = this.ranges[this.dataType];
            const normalized = (value - range.min) / (range.max - range.min);
            const colorValue = Math.floor(Math.max(0, Math.min(1, normalized)) * 255);
            return this.applyColorScale(colorValue);
        }
    }

    getStatusColor(status) {
        const colors = {
            active: { r: 78, g: 205, b: 196 },
            warning: { r: 255, g: 230, b: 109 },
            error: { r: 255, g: 107, b: 107 },
            offline: { r: 102, g: 102, b: 102 }
        };
        return colors[status] || colors.offline;
    }

    drawGrid() {
        this.ctx.strokeStyle = '#333';
        this.ctx.lineWidth = this.gridLineWidth;
        const sizeWithGap = this.modulesPerRow * this.moduleSize + this.backplaneGap;
        
        for (let bpRow = 0; bpRow < this.backplanesPerRow; bpRow++) {
            for (let bpCol = 0; bpCol < this.backplanesPerRow; bpCol++) {
                const bpX = bpCol * sizeWithGap;
                const bpY = bpRow * sizeWithGap;
                const bpSize = this.modulesPerRow * this.moduleSize;
                
                for (let i = 1; i < this.modulesPerRow; i++) {
                    const x = bpX + i * this.moduleSize;
                    this.ctx.beginPath();
                    this.ctx.moveTo(x, bpY);
                    this.ctx.lineTo(x, bpY + bpSize);
                    this.ctx.stroke();
                }
                
                for (let i = 1; i < this.modulesPerRow; i++) {
                    const y = bpY + i * this.moduleSize;
                    this.ctx.beginPath();
                    this.ctx.moveTo(bpX, y);
                    this.ctx.lineTo(bpX + bpSize, y);
                    this.ctx.stroke();
                }
            }
        }
        
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

    highlightModule(moduleId) {
        if (moduleId < 0 || moduleId >= this.totalModules || !this.isModuleActive(moduleId)) return;
        const pos = this.getModulePosition(moduleId);
        this.ctx.strokeStyle = '#ffe66d';
        this.ctx.lineWidth = 3;
        this.ctx.strokeRect(pos.x + 2, pos.y + 2, this.moduleSize - 4, this.moduleSize - 4);
    }

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
                return { r: Math.max(0, Math.min(255, r)), g: Math.max(0, Math.min(255, g)), b: Math.max(0, Math.min(255, b)) };
            
            default:
                return { r: value, g: value, b: value };
        }
    }

    setColorScale(scale) {
        this.colorScale = scale;
        this.updateTempScaleLegend();
        this.drawCamera();
    }

    selectModule(moduleId) {
        if (moduleId < 0 || moduleId >= this.totalModules || !this.isModuleActive(moduleId)) return;
        this.currentModule = moduleId;
        this.drawCamera();
    }

    toggleSimulation() {
        this.simulationMode = !this.simulationMode;
        
        if (this.simulationMode) {
            this.startSimulation();
        } else {
            this.stopSimulation();
        }
    }

    startSimulation() {
        this.simulationTime = 0;
        this.simulationInterval = setInterval(() => {
            this.simulationTime += 0.05;
            this.updateSimulation();
            this.drawCamera();
        }, 50);
    }

    stopSimulation() {
        if (this.simulationInterval) {
            clearInterval(this.simulationInterval);
            this.simulationInterval = null;
        }
    }

    updateSimulation() {
        for (let i = 0; i < this.totalModules; i++) {
            if (!this.isModuleActive(i)) continue;
            
            const pos = this.getModulePosition(i);
            const nx = (pos.bpCol * this.modulesPerRow + pos.modCol) / (this.modulesPerRow * this.backplanesPerRow);
            const ny = (pos.bpRow * this.modulesPerRow + pos.modRow) / (this.modulesPerRow * this.backplanesPerRow);
            
            // Temperature simulation
            let temp = 20;
            temp += Math.sin(nx * Math.PI * 2 + this.simulationTime) * 3;
            temp += Math.cos(ny * Math.PI * 2 + this.simulationTime * 0.7) * 2;
            if ([1, 4, 7].includes(pos.backplaneId)) {
                const dx = pos.modCol - 2;
                const dy = pos.modRow - 2;
                const distFromCenter = Math.sqrt(dx * dx + dy * dy);
                temp += (2.5 - distFromCenter) * 2;
            }
            if (pos.bpCol === 0 || pos.bpCol === 2 || pos.bpRow === 0 || pos.bpRow === 2) {
                temp -= 1.5;
            }
            temp += (Math.random() - 0.5) * 0.5;
            this.temperatures[i] = this.temperatures[i] * 0.9 + temp * 0.1;
            
            // Voltage simulation
            let volt = 5.0 + Math.sin(nx * Math.PI + this.simulationTime * 0.5) * 0.5;
            volt += (Math.random() - 0.5) * 0.1;
            this.voltages[i] = this.voltages[i] * 0.9 + volt * 0.1;
            
            // Current simulation
            let curr = 2.5 + Math.cos(ny * Math.PI + this.simulationTime * 0.3) * 0.5;
            curr += (Math.random() - 0.5) * 0.15;
            this.currents[i] = this.currents[i] * 0.9 + curr * 0.1;
            
            // Status simulation
            if (Math.random() < 0.001) {
                const statuses = ['active', 'warning', 'error', 'offline'];
                this.statuses[i] = statuses[Math.floor(Math.random() * statuses.length)];
            } else if (this.statuses[i] !== 'active' && Math.random() < 0.01) {
                this.statuses[i] = 'active';
            }
        }
    }
}

let cameraViz;

function initCameraVisualization() {
    const canvas = document.getElementById('cameraCanvas');
    if (canvas && !window.cameraInitialized) {
        cameraViz = new CameraVisualization('cameraCanvas');
        if (cameraViz.initialized) {
            cameraViz.drawCamera();
            window.cameraViz = cameraViz;
            window.cameraInitialized = true;
        }
    }
}
