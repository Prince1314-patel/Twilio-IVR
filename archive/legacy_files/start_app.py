 """
Application Startup Script
==========================

This script provides an easy way to start both the FastAPI backend
and Streamlit frontend applications.

Usage:
    python start_app.py

Author: Advanced AI Systems Team
Last Modified: 2025-01-27
"""

import subprocess
import sys
import time
import os
from pathlib import Path

def check_dependencies():
    """Check if all required dependencies are installed."""
    try:
        import fastapi
        import streamlit
        import uvicorn
        import requests
        print("✅ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def start_fastapi():
    """Start the FastAPI backend server."""
    print("🚀 Starting FastAPI backend server...")
    try:
        # Change to the project directory
        os.chdir(Path(__file__).parent)
        
        # Start FastAPI server
        subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ])
        print("✅ FastAPI server started on http://localhost:8000")
        return True
    except Exception as e:
        print(f"❌ Failed to start FastAPI server: {e}")
        return False

def start_streamlit():
    """Start the Streamlit frontend application."""
    print("🚀 Starting Streamlit frontend...")
    try:
        # Wait a moment for FastAPI to start
        time.sleep(3)
        
        # Start Streamlit app
        subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", 
            "streamlit_app.py", 
            "--server.port", "8501",
            "--server.address", "0.0.0.0"
        ])
        print("✅ Streamlit app started on http://localhost:8501")
        return True
    except Exception as e:
        print(f"❌ Failed to start Streamlit app: {e}")
        return False

def main():
    """Main startup function."""
    print("🏥 Healthcare AI Assistant - Starting Application")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Start FastAPI backend
    if not start_fastapi():
        sys.exit(1)
    
    # Start Streamlit frontend
    if not start_streamlit():
        sys.exit(1)
    
    print("\n🎉 Application started successfully!")
    print("\n📱 Access Points:")
    print("   • Streamlit UI: http://localhost:8501")
    print("   • FastAPI API: http://localhost:8000")
    print("   • API Docs: http://localhost:8000/docs")
    print("\n💡 Tips:")
    print("   • Use Ctrl+C to stop the applications")
    print("   • Check the terminal for any error messages")
    print("   • Make sure your .env file is configured properly")
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Shutting down applications...")
        sys.exit(0)

if __name__ == "__main__":
    main()


