"""
Test configuration for the healthbilling project.

Ensures the project root is on sys.path so tests can import `app.*` modules.
"""
import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

