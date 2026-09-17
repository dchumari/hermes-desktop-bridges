"""
Windows Claude Desktop credential extractor.
Deciphers DPAPI-protected Chromium master key and AES-256-GCM token cache from Claude Desktop MSIX AppData.
"""

import os
import sys
import json
import base64
import platform
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("hermes.bridges.claude_desktop.windows")


def is_windows() -> bool:
    return platform.system() == "Windows"


def _decrypt_dpapi_blob(encrypted_bytes: bytes) -> bytes:
    """Decrypt a DPAPI blob using CryptUnprotectData on Windows."""
    if not is_windows():
        return b""
    try:
        import ctypes
        from ctypes import wintypes

        class _DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

        blob_in = _DATA_BLOB(
            len(encrypted_bytes),
            ctypes.cast(ctypes.create_string_buffer(encrypted_bytes), ctypes.POINTER(ctypes.c_byte)),
        )
        blob_out = _DATA_BLOB()
        crypt32 = ctypes.windll.crypt32
        if not crypt32.CryptUnprotectData(
            ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)
        ):
            return b""
        out_ptr = ctypes.cast(blob_out.pbData, ctypes.POINTER(ctypes.c_char))
        data = ctypes.string_at(out_ptr, blob_out.cbData)
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        return data
    except Exception as exc:
        logger.debug("DPAPI decryption failed: %s", exc)
        return b""


def find_claude_desktop_appdata_dir() -> Optional[Path]:
    """Locate the Claude Desktop config directory on Windows (MSIX package or Roaming)."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    app_data = os.environ.get("APPDATA")

    candidates = []

    # 1. MSIX package store (most common modern Windows install)
    if local_app_data:
        pkg_dir = Path(local_app_data) / "Packages"
        if pkg_dir.exists():
            for claude_dir in pkg_dir.glob("Claude_*"):
                candidate = claude_dir / "LocalCache" / "Roaming" / "Claude"
                if candidate.exists():
                    candidates.append(candidate)

    # 2. Standard Roaming app data
    if app_data:
        roaming_candidate = Path(app_data) / "Claude"
        if roaming_candidate.exists():
            candidates.append(roaming_candidate)

    for c in candidates:
        if (c / "Local State").exists() and (c / "config.json").exists():
            return c

    return None


def extract_windows_claude_credentials() -> Optional[Dict[str, Any]]:
    """
    Extract active Claude Desktop OAuth credentials on Windows.
    Returns:
        dict with accessToken, refreshToken, expiresAt, source; or None if not found/decryptable.
    """
    if not is_windows():
        return None

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        logger.warning("'cryptography' package is required for AES-GCM decryption.")
        return None

    app_data_dir = find_claude_desktop_appdata_dir()
    if not app_data_dir:
        logger.debug("Claude Desktop AppData directory not found on Windows.")
        return None

    local_state_path = app_data_dir / "Local State"
    config_path = app_data_dir / "config.json"

    if not local_state_path.exists() or not config_path.exists():
        return None

    try:
        # Step 1: Extract master AES key from Local State via DPAPI
        local_state = json.loads(local_state_path.read_text(encoding="utf-8"))
        encrypted_key_b64 = local_state.get("os_crypt", {}).get("encrypted_key")
        if not encrypted_key_b64:
            return None

        encrypted_key = base64.b64decode(encrypted_key_b64)
        if not encrypted_key.startswith(b"DPAPI"):
            return None

        aes_key = _decrypt_dpapi_blob(encrypted_key[5:])
        if not aes_key:
            return None

        # Step 2: Extract & decrypt oauth:tokenCacheV2 from config.json
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

        # Step 3: Prioritize the longest-lived inference token (Key 3 valid through 2027)
        candidates = [v for k, v in cache.items() if "user:inference" in k and v.get("token")]
        if not candidates:
            # Fallback to any token in cache
            candidates = [v for k, v in cache.items() if v.get("token")]

        if not candidates:
            return None

        best_entry = max(candidates, key=lambda x: x.get("expiresAt", 0))

        return {
            "accessToken": best_entry["token"],
            "refreshToken": best_entry.get("refreshToken", ""),
            "expiresAt": best_entry.get("expiresAt", 0),
            "source": "claude_desktop_windows",
        }
    except Exception as exc:
        logger.debug("Failed to extract Windows Claude Desktop credentials: %s", exc)
        return None
