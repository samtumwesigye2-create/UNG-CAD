# UNG ArtCraft project-file workflow

The Mac adapter now supports opening an existing local file in a selected ArtCraft app:

```bash
bash integrations/artcraft/ung-artcraft-mac.sh list
bash integrations/artcraft/ung-artcraft-mac.sh open PhotoCraft
bash integrations/artcraft/ung-artcraft-mac.sh open-file PhotoCraft "$HOME/Desktop/ps.psd"
bash integrations/artcraft/ung-artcraft-mac.sh reveal PhotoCraft
```

## Verification
- `list` shows actual `.app` bundles in `/Applications` or `~/Applications`; ArtCraft Launcher status is not sufficient.
- `open-file` checks the app allowlist and that the file exists before asking macOS to open it.
- The target app may reject unsupported file formats. This script does not claim import succeeded.
- Saving back to UNG project folders is performed using the target application's Save/Export dialog until its API is verified.
- No background server, shell execution endpoint, privilege escalation, or remote file access is introduced.

## Production gates still pending
Mac execution tests, app-by-app format capability matrix, project workspace manifest, authenticated local bridge, UNG-CAD dashboard wiring, and manufacturing-gate validation for printable exports.
