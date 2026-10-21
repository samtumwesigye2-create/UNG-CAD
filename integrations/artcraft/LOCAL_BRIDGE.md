# UNG ArtCraft authenticated local bridge — Stage 3

Run on your **Mac**, from the repository root:

```bash
python3 integrations/artcraft/local_bridge.py
```

The bridge listens only on `127.0.0.1:18765`, prints a fresh bearer token, and accepts only fixed ArtCraft application names. Keep the token private. It does not expose a public network listener or run arbitrary shell commands.

In a **second Terminal window**, replace `PASTE_TOKEN` with the displayed token:

```bash
curl -fsS -H 'Authorization: Bearer PASTE_TOKEN' http://127.0.0.1:18765/v1/apps
curl -fsS -X POST -H 'Authorization: Bearer PASTE_TOKEN' -H 'Content-Type: application/json' -d '{"app":"PhotoCraft"}' http://127.0.0.1:18765/v1/open
```

To open a file, POST `{"app":"PhotoCraft","file":"/Users/YOUR_USER/Desktop/ps.psd"}`. Only existing regular files within the current user's home directory are accepted.

## Security and deployment limits

- This is a **local test bridge**, not a cloud-hosted service or a complete dashboard integration.
- The browser UNG dashboard is **not yet wired** to this API. Cross-origin browser access is intentionally not enabled.
- Requests require a bearer token; cross-origin POST requests are rejected.
- The macOS `open` command only requests launch; it cannot prove the target app opened the document successfully.
- Avoid posting tokens or private file paths in screenshots. Stop the bridge with Ctrl+C.
- No printing or manufacturing release action is exposed. The existing production gatekeeper remains mandatory.

Next: add a same-origin authenticated dashboard proxy, application format capability tests, and smoke tests on the actual Mac.
