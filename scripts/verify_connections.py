#!/usr/bin/env python3
"""
Verification script for Hermes Desktop Bridges.
Runs live completion tests against both Claude Desktop and Google Antigravity.
"""

import sys
import shutil
import subprocess


def run_hermes_test(model: str, prompt: str) -> tuple[bool, str]:
    """Execute a one-off prompt with hermes and capture output."""
    cmd = ["hermes", "-m", model, "-z", prompt]
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            shell=(sys.platform == "win32"),
        )
        output = res.stdout.strip()
        if res.returncode == 0:
            return True, output
        else:
            return False, res.stderr.strip() or output
    except Exception as exc:
        return False, str(exc)


def main():
    print("================================================================")
    print("      Hermes Desktop Bridges: Connection Verification           ")
    print("================================================================\n")

    if not shutil.which("hermes"):
        print("❌ Error: 'hermes' executable was not found on your system PATH.")
        print("   Please ensure Hermes is installed and added to PATH.")
        sys.exit(1)

    print("[*] Testing Anthropic Claude Desktop bridge (claude-haiku-4-5)...")
    ok_claude, out_claude = run_hermes_test(
        "anthropic/claude-haiku-4-5",
        "What is 17 plus 25? Reply with only the number.",
    )
    if ok_claude:
        print(f"    ✅ Claude Desktop: OK (Output: {out_claude})")
    else:
        print(f"    ❌ Claude Desktop: FAILED ({out_claude})")

    print("\n[*] Testing Google Antigravity bridge (gemini-3.8-flash)...")
    ok_ag, out_ag = run_hermes_test(
        "google-antigravity/gemini-3.8-flash",
        "What is 10 plus 15? Reply with only the number.",
    )
    if ok_ag:
        print(f"    ✅ Google Antigravity: OK (Output: {out_ag})")
    else:
        print(f"    ❌ Google Antigravity: FAILED ({out_ag})")

    print("\n----------------------------------------------------------------")
    if ok_claude and ok_ag:
        print("🎉 Both bridges are active, healthy, and communicating with Hermes!")
    elif ok_claude or ok_ag:
        print("⚠️ Partial connection: One bridge succeeded, but the other encountered an error.")
    else:
        print("❌ Both connections failed. Please check your local credentials and setup.")
    print("----------------------------------------------------------------\n")


if __name__ == "__main__":
    main()
