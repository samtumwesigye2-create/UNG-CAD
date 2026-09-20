# UNG-CAD Safari AD5M Bridge

Browser-independent local bridge for FlashForge Adventurer 5M / 5M Pro.

- Safari talks to the bridge at http://127.0.0.1:8765.
- The bridge auto-discovers the printer over UDP.
- Printer control/upload uses the AD5M LAN TCP interface on port 8899.
- No Web Serial, Chrome, extension, or Python package installation is required.
- Upload & Print always requires the user to explicitly press the button in the local page.

Run `start-safari-ad5m-bridge.command` on macOS.
