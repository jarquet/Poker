#!/usr/bin/env python3
"""
Web interface entry point for Texas Hold'em Poker.

Run from project root:
  python src/web_main.py

Then open http://localhost:8000 in your browser.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "web.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
