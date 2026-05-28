# conftest.py — ensures the bundle root is on sys.path for pytest
import sys
from pathlib import Path

# Add the project root to sys.path so `soraya` is importable.
sys.path.insert(0, str(Path(__file__).parent))
