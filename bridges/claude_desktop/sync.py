"""
Universal Claude Desktop credential synchronizer for Hermes.
Extracts active tokens on Windows, macOS, or Linux and propagates them into Hermes configuration stores.
"""

import os
import sys
import json
import logging
import platform
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from .extractor_windows import extract_windows_claude_credentials
from .extractor_macos import extract_macos_claude_credentials
from .extractor_linux import extract_linux_claude_credentials

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("hermes.bridges.claude_desktop.sync")


def get_hermes_home_dir() -> Path:
    """Resolve the Hermes configuration directory across platforms."""
    # 1. HERMES_HOME env var
    if os.environ.get("HERMES_HOME"):
        return Path(os.environ["HERMES_HOME"])

    # 2. Windows LocalAppData
    if platform.system() == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "hermes"

    # 3. macOS / Linux ~/.hermes
    return Path.home() / ".hermes"


def extract_claude_desktop_credentials() -> Optional[Dict[str, Any]]:
    """
    Auto-detect the operating system and extract Claude Desktop credentials.
    """
    sys_name = platform.system()
    if sys_name == "Windows":
        return extract_windows_claude_credentials()
    elif sys_name == "Darwin":
        return extract_macos_claude_credentials()
    elif sys_name == "Linux":
        return extract_linux_claude_credentials()
    else:
        logger.warning("Unsupported operating system: %s", sys_name)
        return None


def sync_claude_desktop_to_hermes(verbose: bool = True) -> bool:
    """
    Extract active Claude Desktop credentials and synchronize into all Hermes stores.
    """
    if verbose:
        print("==> Detecting Claude Desktop credentials...")

    creds = extract_claude_desktop_credentials()
    if not creds or not creds.get("accessToken"):
        if verbose:
            print("❌ Failed: No active Claude Desktop credentials found or could not be decrypted.")
            print("   Please ensure Claude Desktop is installed and you are logged into your account.")
        return False

    token = creds["accessToken"]
    refresh_token = creds.get("refreshToken", "")
    expires_at = creds.get("expiresAt", 0)
    source = creds.get("source", "unknown")

    exp_str = "Never / Unknown"
    if expires_at:
        try:
            exp_str = datetime.fromtimestamp(expires_at / 1000).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

    if verbose:
        print(f"    Active Token Found: {token[:16]}... (Expires: {exp_str}, Source: {source})")

    hermes_home = get_hermes_home_dir()
    hermes_home.mkdir(parents=True, exist_ok=True)

    # 1. Update .anthropic_oauth.json in Hermes Home
    anthropic_oauth_path = hermes_home / ".anthropic_oauth.json"
    oauth_payload = {
        "accessToken": token,
        "refreshToken": refresh_token,
        "expiresAt": expires_at,
        "source": source,
    }
    anthropic_oauth_path.write_text(json.dumps(oauth_payload, indent=2), encoding="utf-8")
    if verbose:
        print(f"    Synced: {anthropic_oauth_path}")

    # 2. Update ~/.claude/.credentials.json
    user_home = Path.home()
    claude_creds_dir = user_home / ".claude"
    claude_creds_dir.mkdir(parents=True, exist_ok=True)
    claude_creds_file = claude_creds_dir / ".credentials.json"
    claude_payload = {
        "claudeAiOauth": {
            "accessToken": token,
            "refreshToken": refresh_token,
            "expiresAt": expires_at,
        }
    }
    claude_creds_file.write_text(json.dumps(claude_payload, indent=2), encoding="utf-8")
    if verbose:
        print(f"    Synced: {claude_creds_file}")

    # 3. Update hermes .env file
    env_path = hermes_home / ".env"
    env_lines = []
    if env_path.exists():
        env_lines = env_path.read_text(encoding="utf-8").splitlines()

    new_lines = []
    found_token = False
    for line in env_lines:
        if line.startswith("ANTHROPIC_TOKEN="):
            new_lines.append(f"ANTHROPIC_TOKEN={token}")
            found_token = True
        else:
            new_lines.append(line)
    if not found_token:
        new_lines.append(f"ANTHROPIC_TOKEN={token}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    if verbose:
        print(f"    Updated ANTHROPIC_TOKEN in: {env_path}")

    # 4. Update auth.json credential pool
    auth_json_path = hermes_home / "auth.json"
    if auth_json_path.exists():
        try:
            auth_data = json.loads(auth_json_path.read_text(encoding="utf-8"))
            pool = auth_data.setdefault("credential_pool", {}).setdefault("anthropic", [])
            found = False
            for entry in pool:
                if entry.get("id") == "claude_desktop" or entry.get("label") == "Claude Desktop Pro":
                    entry["token"] = token
                    entry["refresh_token"] = refresh_token
                    entry["expires_at"] = expires_at
                    found = True
                    break
            if not found:
                pool.append({
                    "id": "claude_desktop",
                    "label": "Claude Desktop Pro",
                    "token": token,
                    "refresh_token": refresh_token,
                    "expires_at": expires_at,
                    "source": source,
                })
            auth_json_path.write_text(json.dumps(auth_data, indent=2), encoding="utf-8")
            if verbose:
                print(f"    Updated credential pool in: {auth_json_path}")
        except Exception as exc:
            logger.debug("Could not update auth.json: %s", exc)

    if verbose:
        print("✅ SUCCESS: Claude Desktop Pro credentials successfully synchronized to Hermes!")
    return True
