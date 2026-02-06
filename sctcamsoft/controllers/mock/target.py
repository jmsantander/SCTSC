"""target Mock DeviceController

Monkey-patches mock classes for the hardware-dependent
target libraries, then exposes the class as is."""

__all__ = ['TargetController', ]

import sys
import unittest
from unittest.mock import MagicMock, patch
from random import choices

orig_target_driver = sys.modules.get('target_driver')
orig_target_io = sys.modules.get('target_io')
orig_tune_modules = sys.modules.get('tuneModule')

target_driver_mock = MagicMock()
target_module_mock = target_driver_mock.TargetModule()
def get_random_state_string(): 
    return choices(
        ['Not Present', 'Not Powered', 'Not Responding', 
        'Not yet contacted', 'Safe', 'Pre-sync', 'Ready'], 
        weights=[0, 1, 1, 1, 10, 5, 20])[0]
# target_module_mock.GetStateString.return_value = 'Ready'
target_module_mock.GetStateString = get_random_state_string
# target_driver_mock.reset_mock()
sys.modules['target_driver'] = target_driver_mock

target_io_mock = MagicMock()
sys.modules['target_io'] = target_io_mock

tuneModule_mock = MagicMock()
sys.modules['tuneModule'] = tuneModule_mock

from sctcamsoft.controllers.target import TargetController as tg
TargetController = tg

if orig_target_driver is not None:
    sys.modules['target_driver'] = orig_target_driver

if orig_target_io is not None:
    sys.modules['target_io'] = orig_target_io

if orig_tune_modules is not None:
    sys.modules['tuneModule'] = orig_tune_modules
