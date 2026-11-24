"""Project 2: positions and valuation. Reuses Project 1 for the database and dates."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent / "01-data-pipeline"))
