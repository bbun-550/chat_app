# Connection Checklist

## Local Dev
- [ ] Base URL is `http://127.0.0.1:8000`
- [ ] Backend running on local machine
- [ ] `GET /health` returns `{"status":"ok"}`

## Tailscale Dev/Prod
- [ ] Tailscale connected on server/client
- [ ] Base URL uses `http://100.x.x.x:8000`
- [ ] `GET /conversations` successful
- [ ] `POST /chat` successful

## Failure Triage
- [ ] Verify URL and port
- [ ] Verify backend process is alive
- [ ] Verify Tailscale status and ACL
- [ ] Check server logs for 4xx/5xx
