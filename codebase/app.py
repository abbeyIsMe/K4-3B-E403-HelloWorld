"""Submission entrypoint for the VLearn NotebookLM prototype.

The canonical source remains at the repository root because the application
resolves gitignored lecture artifacts from the repository root. This launcher
keeps the required codebase/ submission structure without duplicating app.py.
"""

import runpy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
runpy.run_path(str(ROOT / "app.py"), run_name="__main__")
