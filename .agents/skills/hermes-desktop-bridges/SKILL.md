---
name: hermes-desktop-bridges
description: >-
  Connect, reverse-engineer, decrypt, and configure local desktop AI subscriptions
  (Claude Desktop, Google Antigravity, and other local desktop apps) into Hermes Agent
  and Hermes Desktop without requiring additional API keys or paid API subscriptions.
---

# Hermes Desktop Bridges Skill

A comprehensive operational manual and reverse-engineering guide for extracting, decrypting, and connecting local desktop AI subscriptions (**Claude Desktop Pro/Team** and **Google Antigravity / Google AI Pro**) into **Hermes Agent** and **Hermes Desktop** across Windows, macOS, and Linux.

---

## 1. When to Use This Skill

Activate this skill when:
1. The user wants to use their existing **Claude Desktop** subscription (Claude Pro, Team, Enterprise) in Hermes without paying for Anthropic API credits.
2. The user wants to connect **Google Antigravity** (Google Cloud Code Assist / Google AI Pro) to Hermes Agent or Hermes Desktop.
3. The user wants to run multiple frontier providers (Claude, Gemini, Antigravity, Nous) side-by-side without routing conflicts or interception issues.
4. The user encounters token expiration errors (`HTTP 401: OAuth access token has been revoked`), rate limits (`HTTP 429`), or schema validation errors (`anyOf` without `type`) with Hermes.
5. You need to inspect, patch, or synchronize credentials from Windows DPAPI, macOS Keychain, or Linux Secret Service into Hermes credential pools.

---

## 2. Core Architectural Philosophy

1. **Zero Added API Cost**:
   Tap into existing local desktop credentials rather than requesting third-party API keys.
2. **Provider Coexistence**:
   Ensure plugins (such as `antigravity-provider`) explicitly check model IDs and do **not** blindly intercept requests intended for other providers like Anthropic Claude or OpenAI.
3. **Long-Lived vs. Short-Lived Tokens**:
   Desktop applications often store multiple tokens in their local cache. Never select a 1-hour session token when a multi-year desktop inference token is available.
4. **Non-Destructive Synchronization**:
   Always merge credentials into Hermes stores (`auth.json`, `.env`, `.anthropic_oauth.json`) without wiping existing pools or breaking other configured providers.

---

## 3. Claude Desktop Credential Extraction Runbook

### Windows (DPAPI + AES-256-GCM)

On Windows, Claude Desktop is distributed via MSIX and stores its cache in:
`%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\`

#### Step 1: Master Key Decryption
- File: `Local State`
- Extract JSON path: `os_crypt.encrypted_key` (base64-encoded).
- Verify the decoded bytes begin with `b"DPAPI"`.
- Pass `encrypted_key[5:]` to Windows DPAPI `CryptUnprotectData` via `ctypes.windll.crypt32.CryptUnprotectData`.
- Result: 256-bit AES master key.

```python
import ctypes, base64
from ctypes import wintypes

class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

def decrypt_dpapi(encrypted_bytes: bytes) -> bytes:
    blob_in = _DATA_BLOB(
        len(encrypted_bytes),
        ctypes.cast(ctypes.create_string_buffer(encrypted_bytes), ctypes.POINTER(ctypes.c_byte))
    )
    blob_out = _DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        return b""
    out_ptr = ctypes.cast(blob_out.pbData, ctypes.POINTER(ctypes.c_char))
    data = ctypes.string_at(out_ptr, blob_out.cbData)
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return data
```

#### Step 2: Decrypt Token Cache
- File: `config.json`
- Extract `oauth:tokenCacheV2` (base64-encoded).
- Verify header `b"v10"`.
- Slice Nonce: bytes `[3:15]` (12 bytes).
- Slice Ciphertext: bytes `[15:]`.
- Decrypt using `cryptography.hazmat.primitives.ciphers.aead.AESGCM(aes_key)`.

#### Step 3: CRITICAL Token Scope Selection
The decrypted JSON contains multiple session objects.
- **Key with `user:sessions:claude_code`**: Has `expiresAt` within ~1 hour. If used, requests will fail with `HTTP 401: OAuth access token has been revoked`.
- **Key with `user:inference user:file_upload user:profile`**: Has `expiresAt` in **2027+**.
- **Rule**: Always filter for `user:inference` and select the entry with `max(expiresAt)`:

```python
candidates = [v for k, v in cache.items() if "user:inference" in k and v.get("token")]
target_entry = max(candidates, key=lambda x: x.get("expiresAt", 0))
```

---

### macOS (Keychain & App Support)
- **Keychain Command**:
  ```bash
  /usr/bin/security find-generic-password -s "Claude Code" -w
  ```
- **Application Support Directory**:
  `~/Library/Application Support/Claude/`
- **Fallback Path**:
  `~/.claude/.credentials.json`

---

### Linux (Secret Service & Config)
- **Config Directory**:
  `~/.config/Claude/config.json`
- **Credentials Path**:
  `~/.claude/.credentials.json`

---

## 4. Hermes Credential Store Propagation

To make the decrypted Claude token accessible to all Hermes subsystems, write it to the following four locations:

1. **`$HERMES_HOME/.anthropic_oauth.json`**:
   ```json
   {
     "accessToken": "sk-ant-oat01-...",
     "refreshToken": "sk-ant-ort01-...",
     "expiresAt": 1818838722297,
     "source": "claude_desktop_windows"
   }
   ```
2. **`~/.claude/.credentials.json`**:
   ```json
   {
     "claudeAiOauth": {
       "accessToken": "sk-ant-oat01-...",
       "refreshToken": "sk-ant-ort01-...",
       "expiresAt": 1818838722297
     }
   }
   ```
3. **`$HERMES_HOME/.env`**:
   Ensure `ANTHROPIC_TOKEN=sk-ant-oat01-...` is set.
4. **`$HERMES_HOME/auth.json`**:
   Register under `credential_pool["anthropic"]`:
   ```json
   {
     "id": "claude_desktop",
     "label": "Claude Desktop Pro",
     "token": "sk-ant-oat01-...",
     "refresh_token": "sk-ant-ort01-...",
     "expires_at": 1818838722297,
     "source": "claude_desktop_windows"
   }
   ```

---

## 5. Google Antigravity Provider Integration

### Plugin Architecture
Antigravity operates as an in-process plugin in `$HERMES_HOME/plugins/antigravity-provider`.

### Critical Fixes & Invariants

1. **Strict Request Filtering (`hermes_plugin.py`)**:
   Never let Antigravity intercept non-Antigravity models:
   ```python
   def _is_antigravity_request(model_name: str, provider: Optional[str] = None) -> bool:
       if provider in ("antigravity", "google-antigravity"):
           return True
       if model_name.startswith(("google-antigravity/", "antigravity/")):
           return True
       return False
   ```

2. **Schema Sanitization (`transform.py`)**:
   Cloud Code Assist rejects OpenAI-style schemas containing `anyOf` without `type`, or string-quoted integers in bounds.
   - Strip bare `anyOf` or inject default type.
   - Coerce string integers in `minItems`, `maxItems`, `minimum`, `maximum` to numeric integers.

3. **Wire Model Mapping (`models.py`)**:
   - `google-antigravity/gemini-3.8-flash` -> `gemini-3.8-flash`
   - `google-antigravity/claude-sonnet-4-6` -> `claude-sonnet-4-6`
   - `google-antigravity/gpt-oss-120b` -> `gpt-oss-120b-medium`

---

## 6. Hermes Core Code Patching

If integrating natively into `hermes-agent`:

1. **`agent/anthropic_credentials.py`**:
   Inject `_read_claude_desktop_credentials_windows()` and chain it into `read_claude_code_credentials()`:
   ```python
   kc_creds = _read_claude_code_credentials_from_keychain() or _read_claude_desktop_credentials_windows()
   ```

2. **`hermes_cli/models_catalog_static.py`**:
   Ensure modern Claude models are present under `_PROVIDER_MODELS["anthropic"]`:
   ```python
   "anthropic": [
       "claude-haiku-4-5",
       "claude-haiku-4-5-20251001",
       "claude-sonnet-4-5",
       "claude-sonnet-4-5-20250929",
       "claude-opus-4-5",
       ...
   ]
   ```

3. **`config.yaml`**:
   Add provider entries:
   ```yaml
   providers:
     anthropic: {}
     antigravity: {}
     google-antigravity: {}
   ```

4. **Desktop UI Model Cache**:
   Pre-warm `provider_models_cache.json` using `cached_provider_model_ids('anthropic', force_refresh=True)` so that Claude models appear in the Hermes Desktop Electron model picker.

---

## 7. Verification Procedures

Verify connectivity using one-off prompts with zero tool and tool-enabled runs:

```bash
# 1. Claude Desktop (Fast Haiku)
hermes -m anthropic/claude-haiku-4-5 -z "What is 17 plus 25? Reply with only the number."
# Expected: 42

# 2. Claude Desktop (Tool Call / Agentic)
hermes -m anthropic/claude-haiku-4-5 -z "Calculate 98765 * 43210 using Python and reply with only the answer."
# Expected: 4267635650

# 3. Google Antigravity
hermes -m google-antigravity/gemini-3.8-flash -z "What is 10 plus 15? Reply with only the number."
# Expected: 25

# 4. Diagnostic Suite
python scripts/verify_connections.py
```

---

## 8. Summary Checklist

- [ ] Claude Desktop signed in and running locally.
- [ ] Windows DPAPI / macOS Keychain token extracted.
- [ ] Multi-year inference token selected (`expiresAt: 2027+`).
- [ ] Credentials synchronized across `.anthropic_oauth.json`, `auth.json`, and `.env`.
- [ ] `antigravity-provider` plugin installed in `$HERMES_HOME/plugins/`.
- [ ] Schema transformation rules verified in `transform.py`.
- [ ] Hermes `config.yaml` updated with provider definitions.
- [ ] Live test runs executed for both Anthropic and Google Antigravity.
