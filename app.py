"""Vercel entrypoint.

Vercel looks for a FastAPI instance named `app` in a root-level app.py. The
real app lives in src/web/app.py and imports the game modules (game, betting,
...) as top-level modules from src/, so put src/ on the import path first.

For local runs, use `python src/web_main.py` instead.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from web.app import app  # noqa: E402,F401
