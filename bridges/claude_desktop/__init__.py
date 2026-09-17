"""
Claude Desktop bridge package for extracting credentials and syncing with Hermes.
"""

from .sync import sync_claude_desktop_to_hermes, extract_claude_desktop_credentials

__all__ = [
    "sync_claude_desktop_to_hermes",
    "extract_claude_desktop_credentials",
]
