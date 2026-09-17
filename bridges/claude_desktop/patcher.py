"""
Automated patch utility for Hermes Agent.
Ensures hermes-agent can read Claude Desktop credentials directly from Windows AppData
and registers modern Claude models in the static catalog.
"""

import os
import sys
import re
import logging
import platform
from pathlib import Path
from typing import Optional

logger = logging.getLogger("hermes.bridges.claude_desktop.patcher")


def find_hermes_agent_dir() -> Optional[Path]:
    """Find hermes-agent installation directory."""
    # Check env var
    if os.environ.get("HERMES_AGENT_DIR"):
        p = Path(os.environ["HERMES_AGENT_DIR"])
        if (p / "agent").exists():
            return p

    # Standard Windows install: %LOCALAPPDATA%\hermes\hermes-agent
    if platform.system() == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidate = Path(local_app_data) / "hermes" / "hermes-agent"
            if (candidate / "agent").exists():
                return candidate

    # Standard Unix install: ~/.hermes/hermes-agent
    candidate = Path.home() / ".hermes" / "hermes-agent"
    if (candidate / "agent").exists():
        return candidate

    return None


def patch_anthropic_credentials(hermes_agent_dir: Optional[Path] = None) -> bool:
    """
    Patch agent/anthropic_credentials.py to inject _read_claude_desktop_credentials_windows.
    """
    agent_dir = hermes_agent_dir or find_hermes_agent_dir()
    if not agent_dir:
        logger.warning("hermes-agent directory not found; skipping core patch.")
        return False

    target_file = agent_dir / "agent" / "anthropic_credentials.py"
    if not target_file.exists():
        logger.warning("%s not found.", target_file)
        return False

    content = target_file.read_text(encoding="utf-8")

    if "_read_claude_desktop_credentials_windows" in content:
        logger.info("anthropic_credentials.py is already patched.")
        return True

    windows_reader_code = '''

def _read_claude_desktop_credentials_windows() -> Optional[Dict[str, Any]]:
    """Read OAuth credentials from local Claude Desktop MSIX AppData on Windows."""
    if platform.system() != "Windows":
        return None
    try:
        import ctypes
        from ctypes import wintypes
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        class _DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

        def _decrypt_dpapi(encrypted_bytes: bytes) -> bytes:
            blob_in = _DATA_BLOB(
                len(encrypted_bytes),
                ctypes.cast(ctypes.create_string_buffer(encrypted_bytes), ctypes.POINTER(ctypes.c_byte)),
            )
            blob_out = _DATA_BLOB()
            crypt32 = ctypes.windll.crypt32
            if not crypt32.CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
                return b""
            out_ptr = ctypes.cast(blob_out.pbData, ctypes.POINTER(ctypes.c_char))
            data = ctypes.string_at(out_ptr, blob_out.cbData)
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)
            return data

        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            return None
        packages_dir = Path(local_app_data) / "Packages"
        if not packages_dir.exists():
            return None

        claude_dirs = list(packages_dir.glob("Claude_*"))
        if not claude_dirs:
            return None

        app_data = claude_dirs[0] / "LocalCache" / "Roaming" / "Claude"
        local_state_path = app_data / "Local State"
        config_path = app_data / "config.json"
        if not local_state_path.exists() or not config_path.exists():
            return None

        local_state = json.loads(local_state_path.read_text(encoding="utf-8"))
        encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
        if not encrypted_key.startswith(b"DPAPI"):
            return None
        aes_key = _decrypt_dpapi(encrypted_key[5:])
        if not aes_key:
            return None

        config = json.loads(config_path.read_text(encoding="utf-8"))
        token_cache_raw = config.get("oauth:tokenCacheV2")
        if not token_cache_raw:
            return None

        encrypted_token_cache = base64.b64decode(token_cache_raw)
        if not encrypted_token_cache.startswith(b"v10") or len(encrypted_token_cache) < 31:
            return None

        nonce = encrypted_token_cache[3:15]
        ciphertext = encrypted_token_cache[15:]
        aesgcm = AESGCM(aes_key)
        decrypted = aesgcm.decrypt(nonce, ciphertext, None)
        cache = json.loads(decrypted.decode("utf-8"))

        candidates = [v for k, v in cache.items() if "user:inference" in k and v.get("token")]
        if not candidates:
            return None

        target_entry = max(candidates, key=lambda x: x.get("expiresAt", 0))

        return {
            "accessToken": target_entry["token"],
            "refreshToken": target_entry.get("refreshToken", ""),
            "expiresAt": target_entry.get("expiresAt", 0),
            "source": "claude_desktop_windows",
        }
    except Exception as exc:
        logger.debug("Failed to read Windows Claude Desktop credentials: %s", exc)
        return None
'''

    marker = "def read_claude_code_credentials() -> Optional[Dict[str, Any]]:"
    if marker not in content:
        logger.warning("Function marker not found in %s", target_file)
        return False

    content = content.replace(marker, windows_reader_code + "\n\n" + marker)

    old_kc = "kc_creds = _read_claude_code_credentials_from_keychain()"
    new_kc = "kc_creds = _read_claude_code_credentials_from_keychain() or _read_claude_desktop_credentials_windows()"
    content = content.replace(old_kc, new_kc)

    target_file.write_text(content, encoding="utf-8")
    logger.info("Successfully patched anthropic_credentials.py!")
    return True


def patch_models_catalog(hermes_agent_dir: Optional[Path] = None) -> bool:
    """
    Ensure modern Claude models (claude-haiku-4-5, claude-sonnet-4-5, claude-opus-4-5)
    are present in hermes_cli/models_catalog_static.py.
    """
    agent_dir = hermes_agent_dir or find_hermes_agent_dir()
    if not agent_dir:
        return False

    target_file = agent_dir / "hermes_cli" / "models_catalog_static.py"
    if not target_file.exists():
        return False

    content = target_file.read_text(encoding="utf-8")
    needed_models = [
        "claude-haiku-4-5",
        "claude-haiku-4-5-20251001",
        "claude-sonnet-4-5",
        "claude-sonnet-4-5-20250929",
        "claude-opus-4-5",
    ]

    missing = [m for m in needed_models if f'"{m}"' not in content]
    if not missing:
        logger.info("models_catalog_static.py already contains all modern models.")
        return True

    # Find "anthropic": [ ... ]
    match = re.search(r'("anthropic"\s*:\s*\[)([^\]]+)(\])', content)
    if not match:
        return False

    prefix, models_str, suffix = match.groups()
    new_entries = ", ".join(f'"{m}"' for m in missing)
    updated_models = models_str.rstrip() + f", {new_entries}\n    "
    updated_block = f"{prefix}{updated_models}{suffix}"

    new_content = content[:match.start()] + updated_block + content[match.end():]
    target_file.write_text(new_content, encoding="utf-8")
    logger.info("Successfully added missing Claude models to models_catalog_static.py!")
    return True
