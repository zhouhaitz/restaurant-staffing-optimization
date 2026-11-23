"""Streamlit Community Cloud Entry Point

This is the main entry point for Streamlit Cloud deployment.
It sets up the Python path and imports the main application from gui/app.py
"""

import sys
from pathlib import Path

# Add project root and subdirectories to Python path
project_root = Path(__file__).parent
engine_path = project_root / "engine"
gui_path = project_root / "gui"

# Add to sys.path (similar to what gui/app.py does)
# CRITICAL: Add engine directory to path FIRST, before any other imports
# This ensures simulation.py finds engine/utils.py (which has generate_party_size)
if str(engine_path) in sys.path:
    sys.path.remove(str(engine_path))
sys.path.insert(0, str(engine_path))

# Also add gui directory for other imports
if str(gui_path) not in sys.path:
    sys.path.insert(0, str(gui_path))

# Import and run the main app
from gui.app import main

if __name__ == "__main__":
    main()

