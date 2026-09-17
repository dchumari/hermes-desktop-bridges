#!/usr/bin/env python3
"""
One-Shot Setup Wizard for Hermes Desktop Bridges.
Installs Antigravity plugin, patches Hermes Agent for Claude Desktop,
synchronizes credentials, and updates configuration.
"""

import os
import sys
import yaml
import logging
from pathlib import Path

# Ensure package root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bridges.claude_desktop.sync import sync_claude_desktop_to_hermes, get_hermes_home_dir
from bridges.claude_desktop.patcher import (
    find_hermes_agent_dir,
    patch_anthropic_credentials,
    patch_models_catalog,
)
from bridges.antigravity.installer import install_antigravity_plugin

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def configure_hermes_yaml(hermes_home: Path):
    """Ensure providers mapping exists in config.yaml."""
    config_path = hermes_home / "config.yaml"
    data = {}
    if config_path.exists():
        try:
            data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            logging.warning("Could not parse config.yaml: %s", exc)

    providers = data.setdefault("providers", {})
    updated = False

    if "anthropic" not in providers:
        providers["anthropic"] = {}
        updated = True
    if "antigravity" not in providers:
        providers["antigravity"] = {}
        updated = True
    if "google-antigravity" not in providers:
        providers["google-antigravity"] = {}
        updated = True

    if updated:
        try:
            config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
            print(f"    Configured providers in: {config_path}")
        except Exception as exc:
            logging.warning("Could not update config.yaml: %s", exc)


def main():
    print("================================================================")
    print("      Hermes Desktop Bridges: Automated Setup Wizard            ")
    print("================================================================\n")

    hermes_home = get_hermes_home_dir()
    print(f"[*] Detected Hermes home directory: {hermes_home}")

    agent_dir = find_hermes_agent_dir()
    if agent_dir:
        print(f"[*] Detected Hermes agent directory: {agent_dir}")
    else:
        print("[!] Note: hermes-agent source directory not found; core patches skipped.")

    # 1. Install Google Antigravity Provider
    print("\n--- 1. Installing Google Antigravity Provider Plugin ---")
    install_antigravity_plugin(hermes_home=hermes_home, verbose=True)

    # 2. Patch Hermes Agent for Claude Desktop
    if agent_dir:
        print("\n--- 2. Patching Hermes Agent for Claude Desktop ---")
        patch_anthropic_credentials(agent_dir)
        patch_models_catalog(agent_dir)

    # 3. Synchronize Claude Desktop Credentials
    print("\n--- 3. Synchronizing Claude Desktop Credentials ---")
    sync_claude_desktop_to_hermes(verbose=True)

    # 4. Configure config.yaml
    print("\n--- 4. Updating Hermes Configuration ---")
    configure_hermes_yaml(hermes_home)

    print("\n================================================================")
    print("                   Setup Complete!                              ")
    print("================================================================\n")
    print("You can now run Hermes with either provider:")
    print("  • Claude Desktop:   hermes -m anthropic/claude-haiku-4-5 -z \"Hello\"")
    print("  • Antigravity:      hermes -m google-antigravity/gemini-3.8-flash -z \"Hello\"")
    print("\nTo verify both connections, run:")
    print("  python scripts/verify_connections.py\n")


if __name__ == "__main__":
    main()
