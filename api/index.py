"""
Vercel serverless function entry point for the FastAPI backend.
This file serves as the main entry point for Vercel deployment.
Uses pyproject.toml for dependency management.
"""

import sys
import os

# Add the backend source directory to the Python path
backend_src = os.path.join(os.path.dirname(__file__), '..', 'backend', 'src')
sys.path.insert(0, backend_src)

from agent.app import app

# Vercel expects the app to be named 'handler' or 'app'
handler = app

# Also export as app for compatibility
__all__ = ['handler', 'app']
