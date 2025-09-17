"""
Configuration for pytest.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
# Add the tests directory to the Python path for test_utils
sys.path.insert(0, os.path.dirname(__file__))
