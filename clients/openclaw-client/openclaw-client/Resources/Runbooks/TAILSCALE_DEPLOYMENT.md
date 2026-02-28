# Tailscale Deployment Runbook

## 1) Server (Mac mini)
1. Install tailscale.
2. `sudo tailscale up` and sign in.
3. Check IP via `tailscale ip -4`.
4. Start API with host bind:
   - `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`
5. Verify health:
   - `curl http://<tailscale-ip>:8000/health`

## 2) Client (iOS/macOS)
1. Login to same tailnet in Tailscale app.
2. Open OpenClaw Settings.
3. Set server URL: `http://<tailscale-ip>:8000`.
4. Save and reload conversation list.

## 3) Always-On Server (launchd)
1. Prepare startup script.
2. Add launch agent plist.
3. `launchctl load` and `launchctl start`.
4. Monitor logs (`/tmp/openclaw.err`).

## 4) Validation Checklist
- `/health` reachable from iPhone
- `/conversations` loads from app
- `/chat` request-response works
- token/latency values visible in UI
