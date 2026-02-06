#!/usr/bin/env python3
"""
Camera API Module
Provides Flask endpoints for camera image data and module information
"""

import numpy as np
from flask import jsonify, request
import logging

logger = logging.getLogger(__name__)

class CameraAPI:
    """Camera data API handler"""
    
    def __init__(self, camera_comm=None):
        self.camera_comm = camera_comm
        self.num_modules = 11  # SCT camera has 11 modules
        self.module_width = 48  # pixels per module
        self.module_height = 48
        
    def get_camera_image(self, module_id=0):
        """
        Get camera image data for a specific module
        
        Args:
            module_id (int): Module ID (0-10)
            
        Returns:
            dict: Image data with width, height, and pixel array
        """
        try:
            # If you have real camera data, fetch it here
            if self.camera_comm:
                # Example: Get real data from camera
                image_data = self._get_real_module_data(module_id)
            else:
                # Generate test pattern
                image_data = self._generate_test_pattern(module_id)
            
            return {
                'success': True,
                'module_id': module_id,
                'width': self.module_width,
                'height': self.module_height,
                'image': image_data.tolist(),  # Convert numpy array to list
                'timestamp': np.datetime64('now').astype(str)
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
            module_id (int): Module ID
            
        Returns:
            dict: Module information
        """
        try:
            # Replace with real module info
            return {
                'id': module_id,
                'status': 'active',
                'temperature': 20.0 + np.random.randn() * 2,
                'voltage': 5.0 + np.random.randn() * 0.1,
                'x': module_id % 4,
                'y': module_id // 4
            }
        except Exception as e:
            logger.error(f"Error getting module info: {e}")
            return {'error': str(e)}
    
    def get_all_modules(self):
        """
        Get information about all modules
        
        Returns:
            list: List of module information dicts
        """
        return [self.get_module_info(i) for i in range(self.num_modules)]
    
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
        # For now, return test pattern
        return self._generate_test_pattern(module_id)
    
    def _generate_test_pattern(self, module_id):
        """
        Generate a test pattern for demonstration
        
        Args:
            module_id (int): Module ID
            
        Returns:
            np.ndarray: Test pattern image data
        """
        # Create coordinate grids
        x = np.linspace(-1, 1, self.module_width)
        y = np.linspace(-1, 1, self.module_height)
        X, Y = np.meshgrid(x, y)
        
        # Generate different patterns for each module
        if module_id % 3 == 0:
            # Radial gradient
            R = np.sqrt(X**2 + Y**2)
            pattern = (1 - R) * 255
        elif module_id % 3 == 1:
            # Checkerboard
            pattern = ((np.sin(X * 5) > 0) ^ (np.sin(Y * 5) > 0)).astype(float) * 255
        else:
            # Sine wave
            pattern = (np.sin(X * 3) * np.cos(Y * 3) * 0.5 + 0.5) * 255
        
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
        
        if module_id < 0 or module_id >= camera_api.num_modules:
            return jsonify({'error': 'Invalid module ID'}), 400
        
        data = camera_api.get_camera_image(module_id)
        return jsonify(data)
    
    @app.route('/api/camera/module/<int:module_id>')
    def api_module_info(module_id):
        """Get information about a specific module"""
        if module_id < 0 or module_id >= camera_api.num_modules:
            return jsonify({'error': 'Invalid module ID'}), 400
        
        info = camera_api.get_module_info(module_id)
        image_data = camera_api.get_camera_image(module_id)
        
        return jsonify({
            'info': info,
            'image': image_data['image'],
            'width': image_data['width'],
            'height': image_data['height']
        })
    
    @app.route('/api/camera/modules')
    def api_all_modules():
        """Get information about all modules"""
        modules = camera_api.get_all_modules()
        return jsonify({'modules': modules})
