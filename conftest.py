import sys
from pathlib import Path

# Automatically add the root directory to sys.path for all tests
root_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(root_dir))
