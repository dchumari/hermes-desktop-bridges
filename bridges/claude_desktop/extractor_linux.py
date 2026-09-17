"""
Linux Claude Desktop / Claude Code credential extractor.
Reads OAuth credentials from FreeDesktop Secret Service or Linux configuration files.
"""

import os
import sys
import json
import platform
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("hermes.bridges.claude_desktop.linux")


def is_linux() -> bool:
    return platform.system() == "Linux"


def extract_linux_claude_credentials() -> Optional[Dict[str, Any]]:
    """
    Extract active Claude Desktop or Claude Code credentials on Linux.
    """
    if not is_linux():
        return None

    home = Path.home()

    # Strategy 1: ~/.claude/.credentials.json
    creds_file = home / ".claude" / ".credentials.json"
    if creds_file.exists():
        try:
            data = json.loads(creds_file.read_text(encoding="utf-8"))
            oauth = data.get("claudeAiOauth") or {}
            token = oauth.get("accessToken")
            if token:
                return {
                    "accessToken": token,
                    "refreshToken": oauth.get("refreshToken", ""),
                    "expiresAt": oauth.get("expiresAt", 0),
                    "source": "claude_credentials_file_linux",
                }
        except Exception as exc:
            logger.debug("Failed reading Linux Claude credentials file: %s", exc)

    # Strategy 2: ~/.config/Claude/config.json
    config_file = home / ".config" / "Claude" / "config.json"
    if config_file.exists():
        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
            if "oauth:tokenCacheV2" in data:
                logger.info("Encrypted Claude Desktop token cache detected on Linux.")
        except Exception as exc:
            logger.debug("Failed reading Linux Claude config.json: %s", exc)

    return None
