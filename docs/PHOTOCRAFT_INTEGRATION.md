# PhotoCraft native CLI integration

This adapter invokes the **actual upstream PhotoCraft CLI** locally. It does not replace the browser Photo Studio and does not expose file operations over HTTP.

## Install and build
```sh
git clone https://github.com/storytold/photocraft.git
cd photocraft
cargo build --release -p photocraft-cli
```
Set `PHOTOCRAFT_CLI` to the full path of the compiled `photocraft-cli` executable (on Windows, `photocraft-cli.exe`).

## Run from UNG-CAD
```sh
node bridge/photocraft-cli.js info ./design.psd
node bridge/photocraft-cli.js convert ./design.psd ./design.png
```
No network service is enabled. The adapter checks extensions and uses a non-shell subprocess, but **it is not a sandbox**: only run on trusted files and trusted hosts. Upstream PhotoCraft is early alpha. Preserve originals and validate PSD round trips.

## Gatekeeper
Photo assets may be previewed, but image export never authorizes manufacturing or bypasses UNG-CAD production readiness checks. Production remains HOLD until the existing gate passes. The web Photo Studio is a separate limited image editor; it is not the native PhotoCraft engine.

## Validation still required
Compile upstream CLI on the target OS, run PSD fixture round trips, check memory and timeout behavior, and test browser access before release.
