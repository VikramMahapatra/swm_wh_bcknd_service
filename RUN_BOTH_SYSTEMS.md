# Run Both Systems

## Start SWM Backend Stack

Open Terminal A and run:

```powershell
cd C:/Users/vikik/Projects/swm_wh_bcknd_service/swm-platform
docker compose -f infra/docker-compose.yml up -d --build
```

Health checks:

- http://127.0.0.1:8003/healthz (admin-api)
- http://127.0.0.1:8002/healthz (websocket-api)
- http://127.0.0.1:8001/healthz (ingestion-api)

## Start Frontend App

Open Terminal B and run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
cd C:/Users/vikik/Projects/swm_wh_bcknd_service/garbage_vechile_tracking
npm.cmd i
npm.cmd run dev
```

## Frontend Environment for Live Map Wiring

Ensure these env values exist in the frontend environment (for example in `.env`):

```env
VITE_API_URL=http://127.0.0.1:8003
VITE_WS_URL=ws://127.0.0.1:8002/ws/realtime
VITE_SWM_ADMIN_API_URL=http://127.0.0.1:8003
VITE_SWM_WS_URL=ws://127.0.0.1:8002/ws/realtime
```

Important:

- Do not use deprecated `localhost:8000` URLs. They cause `ERR_CONNECTION_REFUSED` in browser console for `/trucks`, `/routes`, `/drivers`, and `/zones` requests.

## SWM-Only Migration Mode (Legacy Backend Removed)

The live map pages now run in SWM-only mode:

- Live snapshot source: `GET /v1/realtime/trucks` (admin-api, port `8003`)
- Live stream source: `ws://127.0.0.1:8002/ws/realtime`
- Legacy metadata endpoints are no longer required for live map rendering:
	- `/trucks`
	- `/zones`
	- `/drivers`
	- `/routes`

Verification checklist after startup:

- Open browser devtools Network tab.
- Refresh Dashboard and Fleet pages.
- Confirm there are no requests to `/trucks`, `/zones`, `/drivers`, `/routes` on `127.0.0.1:8003`.
- Confirm `GET /v1/realtime/trucks` returns `200`.
- Confirm websocket `ws://127.0.0.1:8002/ws/realtime` connects successfully.

Migration-mode behavior (expected during transition):

- Frontend currently stubs some non-live modules (`alerts`, `vendors`) to empty responses in SWM-only mode.
- You should not see repeated network errors for `/alerts` or `/vendors` after latest frontend code.
- If you still see old errors, hard refresh (`Ctrl+Shift+R`) once to clear stale bundled code.

Google Maps warning note:

- A stack trace from `@react-google-maps/api` during mount can appear if browser state has stale map script context.
- In most cases this is transient; restart frontend dev server and refresh once.
- If it persists, clear site data for `localhost:8080` and reload.

Open frontend:

- http://localhost:8080

## Stop Both Systems

Frontend:

- Press Ctrl+C in Terminal B

Backend:

```powershell
cd C:/Users/vikik/Projects/swm_wh_bcknd_service/swm-platform
docker compose -f infra/docker-compose.yml down
```

## Push Live Data for 10 Trucks (Kharadi, 10 Minutes)

Open Terminal C and run:

```powershell
cd C:/Users/vikik/Projects/swm_wh_bcknd_service/swm-platform
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/loadtest/push_kharadi_live.ps1 -DurationMinutes 10 -Trucks 10
```

What this does:

- Sends live GPS webhook events for 10 trucks.
- Coordinates stay around Kharadi center (`18.5516, 73.9483`) with small movement.
- Keeps pushing once per second for 10 minutes.
- Prints progress every 10 seconds with metrics: `accepted` (backend accepted), `published` (stream published).
- Example: `second=10 sent=30 ok2xx=30 failed=0 accepted=30 published=30`

Optional flags:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/loadtest/push_kharadi_live.ps1 -DurationMinutes 10 -Trucks 10 -CenterLat 18.5516 -CenterLng 73.9483 -VerboseProgress
```

Troubleshooting:

- If you see HTTP 422 with `Request body must be a JSON array`, pull latest code and rerun this script. The current script sends the payload in API-compatible array format for Windows PowerShell.
- Quick ingestion check: open `http://127.0.0.1:8001/healthz` and verify `{"status":"ok","service":"ingestion-api"}`.
