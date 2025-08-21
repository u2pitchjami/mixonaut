"""
Setup function to add the current directory to the system path.
"""

import os
import sys


def setup():
    """
    Setup function to add the current directory to the system path.

    This function is used to ensure that the script can import modules from the same directory as it is running in.
    """
    root = os.path.dirname(os.path.abspath(__file__))
    if root not in sys.path:
        sys.path.insert(0, root)
