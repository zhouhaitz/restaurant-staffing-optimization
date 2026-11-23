"""Make the engine's flat modules importable (the same layout streamlit_app.py sets up)."""
import sys
from pathlib import Path

ENGINE = str(Path(__file__).resolve().parent.parent / "engine")
if ENGINE in sys.path:
    sys.path.remove(ENGINE)
sys.path.insert(0, ENGINE)
