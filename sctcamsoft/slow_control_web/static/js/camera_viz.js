/**
 * Camera Visualization Module
 * 
 * Handles Canvas-based camera display with proper SCT structure.
 * Now supports multiple data types: temperature, voltage, current, and status.
 * The camera display is shared across tabs by moving DOM elements.
 * 
 * @module CameraVisualization
 * @author SCT Camera Team
 * @version 2.1.0
 */

class CameraVisualization {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.colorScale = 'hot';
        this.currentModule = 0;
        this.imageData = null;
        this.simulationMode = false;
        this.simulationInterval = null;
        this.simulationTime = 0;
        
        // Current data type being displayed
        this.dataType = 'temperature';  // 'temperature', 'voltage', 'current', 'status'
        
        // SCT Camera structure
        this.numBackplanes = 9;
        this.backplanesPerRow = 3;
        this.modulesPerBackplane = 25;
        this.modulesPerRow = 5;
        this.totalModules = 225;
        
        // Visual parameters
        this.moduleSize = 48;
        this.backplaneGap = 12;
        this.gridLineWidth = 1;
        this.backplaneLineWidth = 3;
        
        // Data arrays for each type
        this.temperatures = new Array(this.totalModules).fill(20);
        this.voltages = new Array(this.totalModules).fill(5.0);
        this.currents = new Array(this.totalModules).fill(2.5);
        this.statuses = new Array(this.totalModules).fill('active');  // 'active', 'warning', 'error', 'offline'
        
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
    }

    setupCanvas() {
        const modulesAcross = this.modulesPerRow * this.backplanesPerRow;
        const gapsAcross = this.backplanesPerRow - 1;
        this.canvas.width = modulesAcross * this.moduleSize + gapsAcross * this.backplaneGap;
        this.canvas.height = this.canvas.width;
        this.width = this.canvas.width;
        this.height = this.canvas.height;
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
            const infoElement = document.getElementById('pixelInfo');
            if (infoElement) {
                infoElement.textContent = 'Hover over modules for detailed information';
            }
        });
        
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
     * Set the data type to display
     * @param {string} type - 'temperature', 'voltage', 'current', or 'status'
     */
    setDataType(type) {
        this.dataType = type;
        
        // Update tooltip label
        const tooltipLabel = document.getElementById('tooltipValueLabel');
        if (tooltipLabel) {
            tooltipLabel.textContent = this.ranges[type].label + ':';
        }
        
        this.updateTempScaleLegend();
        this.drawCamera();
        this.updateStatistics();
    }

    showTooltip(clientX, clientY, canvasX, canvasY) {
        const moduleId = this.getModuleAtPosition(canvasX, canvasY);
        
        if (!this.tooltip) return;
        
        if (moduleId >= 0 && moduleId < this.totalModules) {
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
            
            const infoElement = document.getElementById('pixelInfo');
            if (infoElement) {
                const valueStr = this.dataType === 'status' ? value.toUpperCase() : `${value.toFixed(2)} ${unit}`;
                infoElement.textContent = `Module ${moduleId} | ` +
                    `Backplane ${pos.backplaneId} | ` +
                    `Position (${pos.modRow},${pos.modCol}) | ` +
                    `${this.ranges[this.dataType].label}: ${valueStr}`;
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
     * Get current value for a module based on active data type
     */
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
        if (!scaleCanvas) return;
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
        
        // Update labels
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
        this.ctx.fillStyle = '#1a1a1a';
        this.ctx.fillRect(0, 0, this.width, this.height);
        
        for (let i = 0; i < this.totalModules; i++) {
            const pos = this.getModulePosition(i);
            const value = this.getCurrentValue(i);
            const color = this.getColorForValue(value);
            
            this.ctx.fillStyle = `rgb(${color.r}, ${color.g}, ${color.b})`;
            this.ctx.fillRect(pos.x, pos.y, this.moduleSize, this.moduleSize);
        }
        
        this.drawGrid();
        this.highlightModule(this.currentModule);
    }

    /**
     * Get color for a value based on current data type
     */
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

    /**
     * Get color for status values
     */
    getStatusColor(status) {
        const colors = {
            active: { r: 78, g: 205, b: 196 },    // Cyan - #4ecdc4
            warning: { r: 255, g: 230, b: 109 },  // Yellow - #ffe66d
            error: { r: 255, g: 107, b: 107 },    // Red - #ff6b6b
            offline: { r: 102, g: 102, b: 102 }   // Gray - #666
        };
        return colors[status] || colors.offline;
    }

    drawGrid() {
        this.ctx.strokeStyle = '#666';
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
        if (moduleId < 0 || moduleId >= this.totalModules) return;
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
        if (moduleId < 0 || moduleId >= this.totalModules) return;
        this.currentModule = moduleId;
        const select = document.getElementById('moduleSelect');
        if (select) select.value = moduleId;
        this.drawCamera();
    }

    toggleSimulation() {
        this.simulationMode = !this.simulationMode;
        const btn = document.getElementById('simulationBtn');
        const indicator = document.getElementById('simulationIndicator');
        
        if (this.simulationMode) {
            if (btn) {
                btn.textContent = 'Disable Simulation';
                btn.classList.add('active');
            }
            if (indicator) indicator.style.display = 'inline-block';
            this.startSimulation();
        } else {
            if (btn) {
                btn.textContent = 'Enable Simulation';
                btn.classList.remove('active');
            }
            if (indicator) indicator.style.display = 'none';
            this.stopSimulation();
        }
    }

    startSimulation() {
        this.simulationTime = 0;
        this.simulationInterval = setInterval(() => {
            this.simulationTime += 0.05;
            this.updateSimulation();
            this.drawCamera();
            this.updateStatistics();
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
            
            // Status simulation (occasional errors)
            if (Math.random() < 0.001) {
                const statuses = ['active', 'warning', 'error', 'offline'];
                this.statuses[i] = statuses[Math.floor(Math.random() * statuses.length)];
            } else if (this.statuses[i] !== 'active' && Math.random() < 0.01) {
                this.statuses[i] = 'active';  // Recover to active
            }
        }
    }

    /**
     * Update statistics display for current data type
     */
    updateStatistics() {
        const prefix = this.dataType === 'temperature' ? 'temp' :
                      this.dataType === 'voltage' ? 'volt' :
                      this.dataType === 'current' ? 'current' : 'status';
        
        if (this.dataType === 'status') {
            // Count status types
            const counts = { active: 0, warning: 0, error: 0, offline: 0 };
            this.statuses.forEach(s => counts[s]++);
            
            const setVal = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.textContent = val;
            };
            
            setVal('statusActive', counts.active);
            setVal('statusWarning', counts.warning);
            setVal('statusError', counts.error);
            setVal('statusOffline', counts.offline);
        } else {
            // Calculate numeric statistics
            const data = this.dataType === 'temperature' ? this.temperatures :
                        this.dataType === 'voltage' ? this.voltages : this.currents;
            
            const avg = data.reduce((a, b) => a + b, 0) / data.length;
            const min = Math.min(...data);
            const max = Math.max(...data);
            const variance = data.reduce((sum, val) => sum + Math.pow(val - avg, 2), 0) / data.length;
            const stdDev = Math.sqrt(variance);
            
            const setVal = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.textContent = val.toFixed(2);
            };
            
            setVal(prefix + 'Avg', avg);
            setVal(prefix + 'Min', min);
            setVal(prefix + 'Max', max);
            setVal(prefix + 'StdDev', stdDev);
        }
    }
}

let cameraViz;

function initCameraVisualization() {
    cameraViz = new CameraVisualization('cameraCanvas');
    populateModuleSelector();
    cameraViz.drawCamera();
    cameraViz.updateStatistics();
}

function populateModuleSelector() {
    const select = document.getElementById('moduleSelect');
    if (!select) return;
    select.innerHTML = '';
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
        console.log('Fetching real camera data...');
    }
}

function updateColorScale() {
    if (!cameraViz) return;
    const select = document.getElementById('colorScale');
    if (select) cameraViz.setColorScale(select.value);
}

function selectModule() {
    if (!cameraViz) return;
    const select = document.getElementById('moduleSelect');
    if (select) cameraViz.selectModule(parseInt(select.value));
}

function toggleSimulation() {
    if (!cameraViz) return;
    cameraViz.toggleSimulation();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCameraVisualization);
} else {
    initCameraVisualization();
}
