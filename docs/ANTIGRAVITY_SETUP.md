# Google Antigravity Setup Guide

This guide details connecting **Google Antigravity** (Google Cloud Code Assist / Google AI Pro) to **Hermes Agent** and **Hermes Desktop**.

---

## Overview

The Google Antigravity integration uses the `antigravity-provider` in-process Hermes plugin. It connects directly to Google's Cloud Code Assist upstream API using your active Google Cloud credentials.

---

## 1. Automated Installation

Run the setup wizard:
```bash
python scripts/setup_all.py
```

Or install the Antigravity plugin specifically:
```bash
python -c "from bridges.antigravity import install_antigravity_plugin; install_antigravity_plugin()"
```

The plugin will be copied to `$HERMES_HOME/plugins/antigravity-provider`.

---

## 2. Configuration (`config.yaml`)

Ensure `$HERMES_HOME/config.yaml` contains the provider entry:

```yaml
providers:
  antigravity: {}
  google-antigravity: {}
```

---

## 3. Available Models

| Model Slug | Underlying Engine | Description |
| :--- | :--- | :--- |
| `google-antigravity/gemini-3.8-flash` | Gemini 3.8 Flash | Ultra-fast multimodal model |
| `google-antigravity/gemini-3.7-flash` | Gemini 3.7 Flash | High-speed frontier reasoning |
| `google-antigravity/gemini-3.6-flash` | Gemini 3.6 Flash | Stable low-latency generation |
| `google-antigravity/gemini-3.1-pro` | Gemini 3.1 Pro | Deep reasoning and analysis |
| `google-antigravity/claude-sonnet-4-6` | Claude Sonnet 4.6 | Claude served via Google Cloud Code |
| `google-antigravity/claude-opus-4-6` | Claude Opus 4.6 | Frontier Claude via Google Cloud Code |
| `google-antigravity/gpt-oss-120b` | GPT OSS 120B | Open-weight foundation model |

---

## 4. Running Prompts

```bash
# Run Gemini 3.8 Flash
hermes -m google-antigravity/gemini-3.8-flash -z "Explain the theory of relativity in simple terms"

# Run Claude Sonnet 4.6 via Antigravity
hermes -m google-antigravity/claude-sonnet-4-6 -z "Analyze this code structure"
```
