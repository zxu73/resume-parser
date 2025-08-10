#!/usr/bin/env python3
"""
Script to set up the authentication database.
Run this script to create the initial database migration and apply it.
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path


async def setup_database():
    """Set up the authentication database with Alembic."""
    print("🚀 Setting up authentication database...")
    
    # Change to backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    try:
        # Step 1: Install dependencies if not already installed
        print("📦 Installing dependencies...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "asyncpg", "psycopg2-binary", "passlib", "python-jose", "python-multipart"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"⚠️  Warning: Failed to install some dependencies: {result.stderr}")
        
        # Step 2: Create migration
        print("📝 Creating initial migration...")
        result = subprocess.run([
            "alembic", "revision", "--autogenerate", "-m", "Create user table"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Error creating migration: {result.stderr}")
            return False
        
        print("✅ Migration created successfully!")
        print(result.stdout)
        
        # Step 3: Apply migration (commented out as it requires a database)
        print("📋 To apply the migration, run:")
        print("   alembic upgrade head")
        print("")
        print("🔧 Make sure to:")
        print("   1. Set up your PostgreSQL database")
        print("   2. Set the DATABASE_URL environment variable")
        print("   3. Run: alembic upgrade head")
        
        return True
        
    except FileNotFoundError:
        print("❌ Error: Alembic not found. Make sure it's installed.")
        print("Run: pip install alembic")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(setup_database())