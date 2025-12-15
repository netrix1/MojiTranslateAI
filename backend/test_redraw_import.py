import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)

print("Attempting to import redraw_agent...")
try:
    from app.core.agents.redraw_agent import redraw_agent
    print("Import successful!")
except ImportError as e:
    print(f"Import FAILED: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error during import: {e}")
    sys.exit(1)

# Dummy test
img_path = Path("test_data/001.jpg") # Assuming this exists or simple path
if not img_path.exists():
    print(f"Warning: {img_path} not found, but import worked.")
    
print("Attempting to initialize LaMa (via get_lama in agent)...")
try:
    from app.core.agents.redraw_agent import get_lama
    model = get_lama()
    print("Model initialized successfully!")
except Exception as e:
    print(f"Model init FAILED: {e}")
    sys.exit(1)
