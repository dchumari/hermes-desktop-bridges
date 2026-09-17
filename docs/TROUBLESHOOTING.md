# Troubleshooting & Frequently Asked Questions

---

## 1. Claude Desktop: `HTTP 401 Unauthorized` or `token revoked`

### Cause:
Hermes loaded a short-lived session token (`user:sessions:claude_code`) that expired, rather than the multi-year desktop inference token.

### Fix:
1. Ensure `bridges/claude_desktop/extractor_windows.py` is up to date (it selects the maximum `expiresAt` token).
2. Re-run the sync command:
   ```bash
   python scripts/sync_claude.py
   ```
3. Verify that the output prints an expiration date in **2027**:
   ```
   Active Token Found: sk-ant-oat01-... (Expires: 2027-08-21 11:58:42)
   ```

---

## 2. Model Rate Limits (HTTP 429) on Claude Pro

### Cause:
Anthropic Pro subscriptions enforce a rolling 5-hour message limit on frontier models (`claude-sonnet-4-6` and `claude-opus-4-6`). This limit is shared with your active Claude Desktop chat window.

### Solution:
- Use `claude-haiku-4-5` for routine, high-volume tasks. Haiku has virtually zero throttling on Pro subscriptions.
- If you hit a temporary Sonnet limit, switch to Google Antigravity models (`google-antigravity/gemini-3.8-flash` or `google-antigravity/claude-sonnet-4-6`) to continue working without interruption.

---

## 3. Connection Refused to `127.0.0.1:8765/v1`

### Cause:
Hermes did not recognize the provider prefix and fell back to the default local gateway address in `config.yaml`.

### Fix:
1. Always prefix the model with its provider name:
   - `anthropic/claude-haiku-4-5` (not just `claude-haiku-4-5`)
   - `google-antigravity/gemini-3.8-flash`
2. Or supply `--provider anthropic`:
   ```bash
   hermes --provider anthropic -m claude-haiku-4-5 -z "Hello"
   ```
3. Ensure `providers:` section exists in `$HERMES_HOME/config.yaml`:
   ```yaml
   providers:
     anthropic: {}
     antigravity: {}
     google-antigravity: {}
   ```

---

## 4. Cloud Code Assist Schema Errors

### Symptom:
`Invalid JSON payload received. Unknown name "anyOf"...`

### Cause:
Cloud Code Assist enforces stricter schema validation on function/tool definitions than standard OpenAI-compatible endpoints.

### Solution:
The included `bridges/antigravity/plugin/src/antigravity_provider/transform.py` includes automatic schema normalization that resolves `anyOf` blocks and ensures integer types for schema validation constraints.
