# UNG Mac App Bridge

Run on macOS with Node.js 18+ from the integration branch:

```bash
node integrations/artcraft/ung-mac-bridge.js
```

Open the printed localhost URL **on the same Mac**. It lists installed ArtCraft and Microsoft Office apps and requests launches through macOS. Stop with Ctrl+C. Do not share the printed URL (it contains a per-session secret).

Security: localhost-only, per-session random token, Origin validation, strict app allowlist, no arbitrary shell commands, no file uploads or document modification. Launch acknowledgement does not verify the application opened successfully. This does not yet connect a remotely hosted UNG dashboard; authenticated pairing and browser security review are required. Mac-side testing remains pending.
