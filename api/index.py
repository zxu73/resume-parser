"""
Vercel serverless function entry point for the FastAPI backend.
This file serves as the main entry point for Vercel deployment.
"""

import sys
import os

# Add the backend source directory to the Python path
backend_src = os.path.join(os.path.dirname(__file__), '..', 'backend', 'src')
if backend_src not in sys.path:
    sys.path.insert(0, backend_src)

try:
    from agent.app import app
except ImportError as e:
    print(f"Import error: {e}")
    # Fallback minimal app for debugging
    from fastapi import FastAPI
    app = FastAPI()
    
    @app.get("/")
    def root():
        return {"message": "Backend import failed", "error": str(e)}

# Export the app for Vercel
app = app
