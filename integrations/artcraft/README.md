# UNG ↔ ArtCraft macOS integration (stage 1)

This stage adds a **local application discovery/launch adapter**, not a claim that the desktop apps are embedded in UNG-CAD or that their automation APIs are working.

## Mac setup
From a checkout of this branch:

```bash
bash integrations/artcraft/ung-artcraft-mac.sh list
bash integrations/artcraft/ung-artcraft-mac.sh open PhotoCraft
bash integrations/artcraft/ung-artcraft-mac.sh open CADCraft
```

The adapter searches only `/Applications` and `~/Applications`. It never installs apps, bypasses Gatekeeper, invokes `sudo`, or modifies user projects. A launcher showing an app as installed does not prove it can open.

## Next integration gates
1. Verify actual macOS .app bundle names and launch all available apps.
2. Verify CLI / JSON / MCP commands *per app* from installed binaries or upstream documentation; do not assume a uniform command interface.
3. Add a localhost-only authenticated bridge for explicitly approved actions; reject arbitrary executable names and paths.
4. Connect UNG-CAD project assets with import/export and backups; enforce the existing manufacturing gate for CAD exports.
5. Add functional smoke tests on Mac before promoting the integration into the unified UNG dashboard.

This does not alter the existing Photo Studio prototype or the PhotoCraft CLI wrapper.
