# Snapshot

A beautiful website-capture studio. Paste a public URL and export a full-page PNG/JPEG or PDF. The web UI can also package the captured image as a PowerPoint deck.

Architecture:
- Frontend: static HTML/CSS/JS on Netlify.
- Capture API: Netlify Function at /api/capture.
- Browser engine: Browserless REST screenshot and PDF endpoints.
- Python: python/snapshot_client.py provides the same capture capability for automation.

Setup:
Add BROWSERLESS_TOKEN as a Netlify environment variable. Never commit the token to GitHub.

Browserless documentation:
https://docs.browserless.io/rest-apis/screenshot-api
https://docs.browserless.io/rest-apis/pdf-api
