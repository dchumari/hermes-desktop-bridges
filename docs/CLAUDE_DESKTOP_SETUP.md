# Claude Desktop Setup & Synchronization Guide

This guide walks through configuring Hermes to use your active **Claude Desktop** subscription (Claude Pro / Team / Enterprise) on Windows, macOS, and Linux without paying for Anthropic API credits.

---

## Prerequisites

1. **Claude Desktop** installed and signed into your Anthropic account.
2. **Hermes Agent** installed (`hermes` command accessible in your terminal).
3. Python 3.10+ with `cryptography` installed:
   ```bash
   pip install cryptography pyyaml
   ```

---

## 1. Quick Setup (Automated)

Run the one-shot onboarding script from the root of this repository:

```bash
python scripts/setup_all.py
```

This will:
- Detect your Claude Desktop installation.
- Decrypt and extract the active multi-year inference token.
- Populate `$HERMES_HOME/.anthropic_oauth.json`, `~/.claude/.credentials.json`, and `$HERMES_HOME/.env`.
- Patch `hermes-agent` so modern models (`claude-haiku-4-5`, `claude-sonnet-4-5`, etc.) are recognized.

---

## 2. On-Demand Token Refresh

Tokens generally remain valid through their multi-year expiration, but if you ever re-log in to Claude Desktop or switch accounts, re-sync with:

### Windows:
```cmd
scripts\sync_claude.bat
```

### macOS / Linux:
```bash
./scripts/sync_claude.sh
```

---

## 3. Supported Models & Usage

With your Claude Desktop subscription connected, you can run prompts using:

```bash
# Fastest model: Claude 3.5 Haiku
hermes -m anthropic/claude-haiku-4-5 -z "Write a python script to parse CSV files"

# Frontier reasoning: Claude Sonnet 4.5
hermes -m anthropic/claude-sonnet-4-5 -z "Refactor this architecture"

# In Hermes Desktop UI:
# Simply open Hermes Desktop and select "Anthropic" from the provider dropdown.
```

---

## 4. Platform-Specific Storage Details

| Operating System | Credential Storage Location | Decryption Method |
| :--- | :--- | :--- |
| **Windows** | `%LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude` | Windows DPAPI + AES-256-GCM |
| **macOS** | `~/Library/Application Support/Claude` & macOS Keychain | `/usr/bin/security` Keychain Query |
| **Linux** | `~/.config/Claude` & `~/.claude` | Secret Service API / Config Store |
