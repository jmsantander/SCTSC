#!/usr/bin/env python3
"""
Camera API Module

Provides Flask endpoints for camera image data and module information.

SCT Camera Structure:
    - 9 backplanes arranged in 3x3 matrix
    - 25 modules per backplane in 5x5 matrix
    - Total: 225 modules (numbered 0-224)

Module Numbering:
    module_id = backplane_id * 25 + module_in_backplane
    
    Example:
        Module 0:   Backplane 0, Module 0 (top-left)
        Module 112: Backplane 4, Module 12 (center of center backplane)
        Module 224: Backplane 8, Module 24 (bottom-right)

API Endpoints:
    /api/camera/image              - Get image for specific module
    /api/camera/module/<id>        - Get module info and image
    /api/camera/modules            - Get all 225 modules info
    /api/camera/backplane/<id>     - Get all modules in backplane
    /api/camera/structure          - Get camera structure metadata

Author: SCT Camera Team
Version: 1.0.0

Example:
    >>> from camera_api import CameraAPI
    >>> api = CameraAPI()
    >>> 
    >>> # Get module info
    >>> info = api.get_module_info(112)
    >>> print(f"Temperature: {info['temperature']:.2f}°C")
    >>> 
    >>> # Get camera image
    >>> img_data = api.get_camera_image(112)
    >>> if img_data['success']:
    >>>     image = np.array(img_data['image'])
    >>>     print(f"Image shape: {image.shape}")
"""

import numpy as np
from flask import jsonify, request
import logging
from typing import Dict, List, Optional, Union, Any

logger = logging.getLogger(__name__)


class CameraAPI:
    """
    Camera data API handler.
    
    Manages camera module data retrieval and provides Flask endpoints
    for accessing module information, images, and temperature readings.
    
    Attributes:
        camera_comm: Optional camera communication interface
        num_backplanes (int): Total number of backplanes (9)
        modules_per_backplane (int): Modules per backplane (25)
        num_modules (int): Total modules (225)
        module_width (int): Module image width in pixels (48)
        module_height (int): Module image height in pixels (48)
    
    Example:
        >>> # Initialize with camera communication
        >>> from camera_comm import CameraComm
        >>> comm = CameraComm()
        >>> api = CameraAPI(camera_comm=comm)
        >>> 
        >>> # Get data for center module
        >>> data = api.get_camera_image(112)
        >>> print(data['success'])  # True
    """
    
    def __init__(self, camera_comm=None):
        """
        Initialize Camera API.
        
        Args:
            camera_comm: Optional camera communication interface.
                        If None, test patterns will be generated.
        
        Example:
            >>> api = CameraAPI()  # Without hardware
            >>> api = CameraAPI(my_camera_comm)  # With hardware
        """
        self.camera_comm = camera_comm
        
        # SCT Camera structure
        self.num_backplanes = 9  # 3x3 arrangement
        self.modules_per_backplane = 25  # 5x5 arrangement
        self.num_modules = 225  # Total modules
        self.module_width = 48  # pixels per module
        self.module_height = 48
        
    def get_camera_image(self, module_id: int = 0) -> Dict[str, Any]:
        """
        Get camera image data for a specific module.
        
        Retrieves a 48x48 pixel image from the specified module.
        If hardware is connected, fetches real data. Otherwise,
        generates a test pattern.
        
        Args:
            module_id: Module ID (0-224). Default is 0.
        
        Returns:
            Dictionary containing:
                success (bool): Whether operation succeeded
                module_id (int): Module ID
                backplane_id (int): Parent backplane ID
                module_in_backplane (int): Module index within backplane
                width (int): Image width (48)
                height (int): Image height (48)
                image (list): 2D array of pixel values (0-255)
                timestamp (str): ISO format timestamp
                error (str): Error message (only if success=False)
        
        Raises:
            No exceptions raised; errors returned in dict.
        
        Example:
            >>> api = CameraAPI()
            >>> data = api.get_camera_image(112)
            >>> if data['success']:
            >>>     print(f"Module {data['module_id']}")
            >>>     print(f"Backplane {data['backplane_id']}")
            >>>     print(f"Image size: {data['width']}x{data['height']}")
            >>>     image_array = np.array(data['image'])
        """
        try:
            # Validate module ID
            if module_id < 0 or module_id >= self.num_modules:
                return {
                    'success': False,
                    'error': f'Invalid module ID {module_id}. Must be 0-{self.num_modules-1}'
                }
            
            # Get image data (real or test pattern)
            if self.camera_comm:
                image_data = self._get_real_module_data(module_id)
            else:
                image_data = self._generate_test_pattern(module_id)
            
            # Calculate backplane and module info
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
    
    def get_module_info(self, module_id: int) -> Dict[str, Any]:
        """
        Get information about a specific module.
        
        Returns module location, status, and sensor readings including
        temperature, voltage, and current.
        
        Args:
            module_id: Module ID (0-224)
        
        Returns:
            Dictionary containing:
                id (int): Module ID
                backplane_id (int): Backplane ID (0-8)
                module_in_backplane (int): Module index within backplane (0-24)
                backplane_position (dict): {'row': int, 'col': int} in 3x3 grid
                module_position (dict): {'row': int, 'col': int} in 5x5 grid
                status (str): Module status ('active', 'inactive', 'error')
                temperature (float): Temperature in Celsius
                voltage (float): Voltage in Volts
                current (float): Current in Amperes
                error (str): Error message (only if error occurred)
        
        Example:
            >>> api = CameraAPI()
            >>> info = api.get_module_info(112)
            >>> print(f"Module {info['id']}:")
            >>> print(f"  Backplane: {info['backplane_id']} at {info['backplane_position']}")
            >>> print(f"  Position: {info['module_position']}")
            >>> print(f"  Temperature: {info['temperature']:.2f}°C")
            >>> print(f"  Voltage: {info['voltage']:.2f}V")
            >>> print(f"  Current: {info['current']:.2f}A")
        """
        try:
            # Validate module ID
            if module_id < 0 or module_id >= self.num_modules:
                return {'error': f'Invalid module ID {module_id}'}
            
            # Calculate positions
            backplane_id = module_id // self.modules_per_backplane
            module_in_bp = module_id % self.modules_per_backplane
            
            # Backplane position in 3x3 grid
            bp_row = backplane_id // 3
            bp_col = backplane_id % 3
            
            # Module position within backplane (5x5)
            mod_row = module_in_bp // 5
            mod_col = module_in_bp % 5
            
            # Generate simulated temperature (replace with real data)
            base_temp = 20.0
            temp_variation = np.random.randn() * 2
            
            # Some backplanes run hotter (simulate different power zones)
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
    
    def get_all_modules(self) -> List[Dict[str, Any]]:
        """
        Get information about all 225 modules.
        
        Returns:
            List of 225 module information dictionaries.
            See get_module_info() for dictionary structure.
        
        Example:
            >>> api = CameraAPI()
            >>> all_modules = api.get_all_modules()
            >>> print(f"Total modules: {len(all_modules)}")
            >>> 
            >>> # Find hottest module
            >>> hottest = max(all_modules, key=lambda m: m['temperature'])
            >>> print(f"Hottest module: {hottest['id']} at {hottest['temperature']:.2f}°C")
            >>> 
            >>> # Get average temperature
            >>> avg_temp = np.mean([m['temperature'] for m in all_modules])
            >>> print(f"Average temperature: {avg_temp:.2f}°C")
        """
        return [self.get_module_info(i) for i in range(self.num_modules)]
    
    def get_backplane_modules(self, backplane_id: int) -> Union[List[Dict[str, Any]], Dict[str, str]]:
        """
        Get all modules for a specific backplane.
        
        Args:
            backplane_id: Backplane ID (0-8)
        
        Returns:
            List of 25 module info dictionaries, or error dict if invalid ID.
        
        Example:
            >>> api = CameraAPI()
            >>> 
            >>> # Get all modules in center backplane
            >>> center_modules = api.get_backplane_modules(4)
            >>> if isinstance(center_modules, list):
            >>>     print(f"Backplane 4 has {len(center_modules)} modules")
            >>>     for mod in center_modules:
            >>>         print(f"  Module {mod['id']}: {mod['temperature']:.2f}°C")
        """
        # Validate backplane ID
        if backplane_id < 0 or backplane_id >= self.num_backplanes:
            return {'error': f'Invalid backplane ID {backplane_id}'}
        
        # Calculate module range for this backplane
        start_module = backplane_id * self.modules_per_backplane
        end_module = start_module + self.modules_per_backplane
        
        return [self.get_module_info(i) for i in range(start_module, end_module)]
    
    def _get_real_module_data(self, module_id: int) -> np.ndarray:
        """
        Get real data from camera hardware.
        
        Args:
            module_id: Module ID (0-224)
        
        Returns:
            48x48 numpy array of pixel values (uint8)
        
        Note:
            This is a placeholder. Implement actual hardware interface here.
        
        Example implementation:
            >>> backplane_id = module_id // 25
            >>> module_in_bp = module_id % 25
            >>> raw_data = self.camera_comm.get_module_data(backplane_id, module_in_bp)
            >>> return np.array(raw_data, dtype=np.uint8).reshape((48, 48))
        """
        # TODO: Implement actual camera data retrieval
        # This would interface with your camera_comm object
        # Example:
        # backplane_id = module_id // self.modules_per_backplane
        # module_in_bp = module_id % self.modules_per_backplane
        # raw_data = self.camera_comm.get_module_data(backplane_id, module_in_bp)
        # return np.array(raw_data, dtype=np.uint8).reshape((self.module_height, self.module_width))
        
        return self._generate_test_pattern(module_id)
    
    def _generate_test_pattern(self, module_id: int) -> np.ndarray:
        """
        Generate a test pattern for demonstration.
        
        Creates different patterns for different backplanes:
            - Pattern 0: Radial gradient from center
            - Pattern 1: Checkerboard
            - Pattern 2: Sine wave interference
            - Pattern 3: Diagonal gradient
        
        Args:
            module_id: Module ID (0-224)
        
        Returns:
            48x48 numpy array of pixel values (uint8, 0-255)
        
        Example:
            >>> api = CameraAPI()
            >>> pattern = api._generate_test_pattern(0)
            >>> print(pattern.shape)  # (48, 48)
            >>> print(pattern.dtype)  # uint8
            >>> print(f"Min: {pattern.min()}, Max: {pattern.max()}")
        """
        backplane_id = module_id // self.modules_per_backplane
        module_in_bp = module_id % self.modules_per_backplane
        
        # Create coordinate grids (-1 to 1)
        x = np.linspace(-1, 1, self.module_width)
        y = np.linspace(-1, 1, self.module_height)
        X, Y = np.meshgrid(x, y)
        
        # Different patterns for different backplanes
        pattern_type = backplane_id % 4
        
        if pattern_type == 0:
            # Radial gradient: bright in center, dark at edges
            R = np.sqrt(X**2 + Y**2)
            pattern = (1 - R) * 255
        elif pattern_type == 1:
            # Checkerboard pattern
            pattern = ((np.sin(X * 5) > 0) ^ (np.sin(Y * 5) > 0)).astype(float) * 255
        elif pattern_type == 2:
            # Sine wave interference
            pattern = (np.sin(X * 3) * np.cos(Y * 3) * 0.5 + 0.5) * 255
        else:
            # Diagonal gradient
            pattern = ((X + Y + 2) / 4) * 255
        
        # Add module-specific variation
        variation = (module_in_bp / self.modules_per_backplane) * 50
        pattern = pattern * 0.8 + variation
        
        # Add some noise for realism
        noise = np.random.randn(self.module_height, self.module_width) * 10
        pattern = np.clip(pattern + noise, 0, 255)
        
        return pattern.astype(np.uint8)


def register_camera_routes(app, camera_api: CameraAPI) -> None:
    """
    Register camera-related Flask routes.
    
    Adds all camera API endpoints to the Flask application.
    
    Args:
        app: Flask application instance
        camera_api: CameraAPI instance to handle requests
    
    Registered routes:
        GET /api/camera/image?module=<id>      - Get module image
        GET /api/camera/module/<id>            - Get module info + image
        GET /api/camera/modules                - Get all modules info
        GET /api/camera/backplane/<id>         - Get backplane modules
        GET /api/camera/structure              - Get camera structure
    
    Example:
        >>> from flask import Flask
        >>> app = Flask(__name__)
        >>> api = CameraAPI()
        >>> register_camera_routes(app, api)
        >>> app.run()
    """
    
    @app.route('/api/camera/image')
    def api_camera_image():
        """
        Get camera image for a specific module.
        
        Query Parameters:
            module (int): Module ID (0-224), default 0
        
        Returns:
            JSON response with image data
        
        Example:
            GET /api/camera/image?module=112
        """
        module_id = request.args.get('module', 0, type=int)
        data = camera_api.get_camera_image(module_id)
        return jsonify(data)
    
    @app.route('/api/camera/module/<int:module_id>')
    def api_module_info(module_id: int):
        """
        Get information about a specific module.
        
        Args:
            module_id: Module ID (0-224) from URL path
        
        Returns:
            JSON with module info and image, or 400 error
        
        Example:
            GET /api/camera/module/112
        """
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
        """
        Get information about all 225 modules.
        
        Returns:
            JSON with list of all modules and total count
        
        Example:
            GET /api/camera/modules
        """
        modules = camera_api.get_all_modules()
        return jsonify({'modules': modules, 'total': len(modules)})
    
    @app.route('/api/camera/backplane/<int:backplane_id>')
    def api_backplane_modules(backplane_id: int):
        """
        Get all modules for a specific backplane.
        
        Args:
            backplane_id: Backplane ID (0-8) from URL path
        
        Returns:
            JSON with modules list and count, or 400 error
        
        Example:
            GET /api/camera/backplane/4
        """
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
        """
        Get camera structure information.
        
        Returns:
            JSON with camera configuration metadata
        
        Example:
            GET /api/camera/structure
            
            Response:
            {
                "num_backplanes": 9,
                "backplane_arrangement": "3x3",
                "modules_per_backplane": 25,
                "module_arrangement": "5x5",
                "total_modules": 225,
                "module_dimensions": {"width": 48, "height": 48}
            }
        """
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
