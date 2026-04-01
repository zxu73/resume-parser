"""
Vercel serverless entry point.
Re-exports the real FastAPI app from the backend.
"""

import os
import sys

# Add backend source to Python path
backend_src = os.path.join(os.path.dirname(__file__), '..', 'backend', 'src')
if backend_src not in sys.path:
    sys.path.insert(0, backend_src)

# Load .env from backend directory
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), '..', 'backend', '.env')
load_dotenv(env_path)

from agent.app import app
