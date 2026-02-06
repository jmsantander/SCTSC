#!/usr/bin/env python3
"""
Camera API Module
Provides Flask endpoints for camera image data and module information
SCT Camera: 9 backplanes (3x3) with 25 modules each (5x5) = 225 total modules
"""

import numpy as np
from flask import jsonify, request
import logging

logger = logging.getLogger(__name__)

class CameraAPI:
    """Camera data API handler"""
    
    def __init__(self, camera_comm=None):
        self.camera_comm = camera_comm
        
        # SCT Camera structure
        self.num_backplanes = 9  # 3x3 arrangement
        self.modules_per_backplane = 25  # 5x5 arrangement
        self.num_modules = 225  # Total modules
        self.module_width = 48  # pixels per module
        self.module_height = 48
        
    def get_camera_image(self, module_id=0):
        """
        Get camera image data for a specific module
        
        Args:
            module_id (int): Module ID (0-224)
            
        Returns:
            dict: Image data with width, height, and pixel array
        """
        try:
            if module_id < 0 or module_id >= self.num_modules:
                return {
                    'success': False,
                    'error': f'Invalid module ID {module_id}. Must be 0-{self.num_modules-1}'
                }
            
            # If you have real camera data, fetch it here
            if self.camera_comm:
                image_data = self._get_real_module_data(module_id)
            else:
                # Generate test pattern
                image_data = self._generate_test_pattern(module_id)
            
            # Get backplane and module info
            backplane_id = module_id // self.modules_per_backplane
            module_in_bp = module_id % self.modules_per_backplane
            
            return {
                'success': True,
                'module_id': module_id,
                'backplane_id': backplane_id,
                'module_in_backplane': module_in_bp,
                'width': self.module_width,
                'height': self.module_height,
                'image': image_data.tolist(),
                'timestamp': str(np.datetime64('now'))
            }
            
        except Exception as e:
            logger.error(f"Error getting camera image: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_module_info(self, module_id):
        """
        Get information about a specific module
        
        Args:
            module_id (int): Module ID (0-224)
            
        Returns:
            dict: Module information including backplane location
        """
        try:
            if module_id < 0 or module_id >= self.num_modules:
                return {'error': f'Invalid module ID {module_id}'}
            
            backplane_id = module_id // self.modules_per_backplane
            module_in_bp = module_id % self.modules_per_backplane
            
            # Backplane position in 3x3 grid
            bp_row = backplane_id // 3
            bp_col = backplane_id % 3
            
            # Module position within backplane (5x5)
            mod_row = module_in_bp // 5
            mod_col = module_in_bp % 5
            
            # Simulate temperature (replace with real data)
            base_temp = 20.0
            temp_variation = np.random.randn() * 2
            
            # Some backplanes run hotter
            if backplane_id in [1, 4, 7]:
                temp_variation += 3.0
            
            return {
                'id': module_id,
                'backplane_id': backplane_id,
                'module_in_backplane': module_in_bp,
                'backplane_position': {'row': bp_row, 'col': bp_col},
                'module_position': {'row': mod_row, 'col': mod_col},
                'status': 'active',
                'temperature': base_temp + temp_variation,
                'voltage': 5.0 + np.random.randn() * 0.1,
                'current': 2.5 + np.random.randn() * 0.2
            }
        except Exception as e:
            logger.error(f"Error getting module info: {e}")
            return {'error': str(e)}
    
    def get_all_modules(self):
        """
        Get information about all 225 modules
        
        Returns:
            list: List of module information dicts
        """
        return [self.get_module_info(i) for i in range(self.num_modules)]
    
    def get_backplane_modules(self, backplane_id):
        """
        Get all modules for a specific backplane
        
        Args:
            backplane_id (int): Backplane ID (0-8)
            
        Returns:
            list: List of 25 module info dicts
        """
        if backplane_id < 0 or backplane_id >= self.num_backplanes:
            return {'error': f'Invalid backplane ID {backplane_id}'}
        
        start_module = backplane_id * self.modules_per_backplane
        end_module = start_module + self.modules_per_backplane
        
        return [self.get_module_info(i) for i in range(start_module, end_module)]
    
    def _get_real_module_data(self, module_id):
        """
        Get real data from camera hardware
        
        Args:
            module_id (int): Module ID
            
        Returns:
            np.ndarray: Image data
        """
        # TODO: Implement actual camera data retrieval
        # This would interface with your camera_comm object
        # Example:
        # backplane_id = module_id // self.modules_per_backplane
        # module_in_bp = module_id % self.modules_per_backplane
        # raw_data = self.camera_comm.get_module_data(backplane_id, module_in_bp)
        # return np.array(raw_data, dtype=np.uint8).reshape((self.module_height, self.module_width))
        
        return self._generate_test_pattern(module_id)
    
    def _generate_test_pattern(self, module_id):
        """
        Generate a test pattern for demonstration
        
        Args:
            module_id (int): Module ID
            
        Returns:
            np.ndarray: Test pattern image data
        """
        backplane_id = module_id // self.modules_per_backplane
        module_in_bp = module_id % self.modules_per_backplane
        
        # Create coordinate grids
        x = np.linspace(-1, 1, self.module_width)
        y = np.linspace(-1, 1, self.module_height)
        X, Y = np.meshgrid(x, y)
        
        # Different patterns for different backplanes
        pattern_type = backplane_id % 4
        
        if pattern_type == 0:
            # Radial gradient
            R = np.sqrt(X**2 + Y**2)
            pattern = (1 - R) * 255
        elif pattern_type == 1:
            # Checkerboard
            pattern = ((np.sin(X * 5) > 0) ^ (np.sin(Y * 5) > 0)).astype(float) * 255
        elif pattern_type == 2:
            # Sine wave
            pattern = (np.sin(X * 3) * np.cos(Y * 3) * 0.5 + 0.5) * 255
        else:
            # Diagonal gradient
            pattern = ((X + Y + 2) / 4) * 255
        
        # Add module-specific variation
        variation = (module_in_bp / self.modules_per_backplane) * 50
        pattern = pattern * 0.8 + variation
        
        # Add some noise
        noise = np.random.randn(self.module_height, self.module_width) * 10
        pattern = np.clip(pattern + noise, 0, 255)
        
        return pattern.astype(np.uint8)


def register_camera_routes(app, camera_api):
    """
    Register camera-related Flask routes
    
    Args:
        app: Flask application
        camera_api: CameraAPI instance
    """
    
    @app.route('/api/camera/image')
    def api_camera_image():
        """Get camera image for a specific module"""
        module_id = request.args.get('module', 0, type=int)
        data = camera_api.get_camera_image(module_id)
        return jsonify(data)
    
    @app.route('/api/camera/module/<int:module_id>')
    def api_module_info(module_id):
        """Get information about a specific module"""
        info = camera_api.get_module_info(module_id)
        if 'error' in info:
            return jsonify(info), 400
        
        image_data = camera_api.get_camera_image(module_id)
        
        return jsonify({
            'info': info,
            'image': image_data.get('image', []),
            'width': image_data.get('width', 0),
            'height': image_data.get('height', 0)
        })
    
    @app.route('/api/camera/modules')
    def api_all_modules():
        """Get information about all 225 modules"""
        modules = camera_api.get_all_modules()
        return jsonify({'modules': modules, 'total': len(modules)})
    
    @app.route('/api/camera/backplane/<int:backplane_id>')
    def api_backplane_modules(backplane_id):
        """Get all modules for a specific backplane"""
        modules = camera_api.get_backplane_modules(backplane_id)
        if isinstance(modules, dict) and 'error' in modules:
            return jsonify(modules), 400
        return jsonify({
            'backplane_id': backplane_id,
            'modules': modules,
            'count': len(modules)
        })
    
    @app.route('/api/camera/structure')
    def api_camera_structure():
        """Get camera structure information"""
        return jsonify({
            'num_backplanes': camera_api.num_backplanes,
            'backplane_arrangement': '3x3',
            'modules_per_backplane': camera_api.modules_per_backplane,
            'module_arrangement': '5x5',
            'total_modules': camera_api.num_modules,
            'module_dimensions': {
                'width': camera_api.module_width,
                'height': camera_api.module_height
            }
        })
