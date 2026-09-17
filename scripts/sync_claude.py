#!/usr/bin/env python3
"""
CLI entry point to synchronize Claude Desktop credentials into Hermes.
Extracts the active token cache and updates all Hermes credential stores.
"""

import sys
import os

# Ensure package root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bridges.claude_desktop.sync import sync_claude_desktop_to_hermes


def main():
    success = sync_claude_desktop_to_hermes(verbose=True)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
