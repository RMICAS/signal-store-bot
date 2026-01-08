#!/usr/bin/env python3
"""
Start the Admin Dashboard
Run this to start the Flask web server for the admin dashboard
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from dashboard.app import app
import logging

logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':
    PORT = 5001
    print("🚀 Starting Admin Dashboard...")
    print(f"📊 Dashboard available at: http://localhost:{PORT}")
    print("🛑 Press Ctrl+C to stop")
    app.run(debug=True, host='0.0.0.0', port=PORT)

