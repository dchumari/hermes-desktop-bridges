"""
Installer for the Google Antigravity Hermes provider plugin.
Copies the plugin into $HERMES_HOME/plugins/antigravity-provider and configures Hermes.
"""

import os
import sys
import shutil
import logging
import platform
from pathlib import Path
from typing import Optional

logger = logging.getLogger("hermes.bridges.antigravity.installer")


def get_hermes_home_dir() -> Path:
    """Resolve the Hermes home directory."""
    if os.environ.get("HERMES_HOME"):
        return Path(os.environ["HERMES_HOME"])
    if platform.system() == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "hermes"
    return Path.home() / ".hermes"


def install_antigravity_plugin(hermes_home: Optional[Path] = None, verbose: bool = True) -> bool:
    """
    Install the antigravity-provider plugin into Hermes.
    """
    home = hermes_home or get_hermes_home_dir()
    plugins_dir = home / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)

    plugin_src = Path(__file__).resolve().parent / "plugin"
    if not plugin_src.exists():
        if verbose:
            print("❌ Error: Antigravity plugin source directory not found.")
        return False

    plugin_dst = plugins_dir / "antigravity-provider"

    if verbose:
        print(f"==> Installing Antigravity provider to {plugin_dst}...")

    def ignore_patterns(path, names):
        ignored = []
        for name in names:
            if name in ["__pycache__", ".git", ".pytest_cache"] or name.endswith(".pyc"):
                ignored.append(name)
        return ignored

    if plugin_dst.exists():
        try:
            shutil.rmtree(plugin_dst)
        except Exception as exc:
            logger.debug("Failed removing old plugin directory: %s", exc)

    shutil.copytree(plugin_src, plugin_dst, ignore=ignore_patterns)

    if verbose:
        print("✅ Antigravity provider plugin installed successfully!")
    return True
