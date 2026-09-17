"""
macOS Claude Desktop / Claude Code credential extractor.
Reads OAuth credentials from macOS Keychain or Application Support directory.
"""

import os
import sys
import json
import platform
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("hermes.bridges.claude_desktop.macos")


def is_macos() -> bool:
    return platform.system() == "Darwin"


def _read_macos_keychain(service: str, account: Optional[str] = None) -> Optional[str]:
    """Query generic password from macOS Keychain."""
    if not is_macos():
        return None
    try:
        cmd = ["/usr/bin/security", "find-generic-password", "-s", service, "-w"]
        if account:
            cmd.extend(["-a", account])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as exc:
        logger.debug("Keychain query for service %s failed: %s", service, exc)
    return None


def extract_macos_claude_credentials() -> Optional[Dict[str, Any]]:
    """
    Extract active Claude Desktop or Claude Code credentials on macOS.
    """
    if not is_macos():
        return None

    # Strategy 1: Claude Code keychain entry
    raw_keychain = _read_macos_keychain("Claude Code")
    if raw_keychain:
        try:
            parsed = json.loads(raw_keychain)
            # Standard Claude Code structure: { "claudeAiOauth": { "accessToken": ... } }
            oauth_entry = parsed.get("claudeAiOauth") or parsed
            if oauth_entry.get("accessToken") or oauth_entry.get("token"):
                token = oauth_entry.get("accessToken") or oauth_entry.get("token")
                return {
                    "accessToken": token,
                    "refreshToken": oauth_entry.get("refreshToken", ""),
                    "expiresAt": oauth_entry.get("expiresAt", 0),
                    "source": "claude_code_macos_keychain",
                }
        except Exception:
            # Bare token in keychain
            if raw_keychain.startswith("sk-ant-"):
                return {
                    "accessToken": raw_keychain,
                    "refreshToken": "",
                    "expiresAt": 0,
                    "source": "claude_code_macos_keychain_raw",
                }

    # Strategy 2: Claude Desktop Application Support
    home = Path.home()
    claude_app_support = home / "Library" / "Application Support" / "Claude"
    config_path = claude_app_support / "config.json"
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            if "oauth:tokenCacheV2" in data:
                logger.info("Encrypted Claude Desktop cache found in macOS Application Support.")
        except Exception as exc:
            logger.debug("Error reading macOS config.json: %s", exc)

    # Strategy 3: ~/.claude/.credentials.json
    dot_claude_creds = home / ".claude" / ".credentials.json"
    if dot_claude_creds.exists():
        try:
            data = json.loads(dot_claude_creds.read_text(encoding="utf-8"))
            oauth = data.get("claudeAiOauth") or {}
            token = oauth.get("accessToken")
            if token:
                return {
                    "accessToken": token,
                    "refreshToken": oauth.get("refreshToken", ""),
                    "expiresAt": oauth.get("expiresAt", 0),
                    "source": "claude_credentials_file_macos",
                }
        except Exception as exc:
            logger.debug("Error reading ~/.claude/.credentials.json: %s", exc)

    return None
