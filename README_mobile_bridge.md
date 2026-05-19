# LoL Mobile Bridge

This project now includes a local server + mobile web panel:

- Python server: reads live League Client (LCU) data and exposes API/WebSocket.
- React panel: can be opened from phone and sends champion select / rune actions.

## 1) Start backend server

From project root:

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python live_server.py
```

Server runs on `0.0.0.0:8765` by default.

Optional env vars:

- `LOL_BRIDGE_HOST` (default `0.0.0.0`)
- `LOL_BRIDGE_PORT` (default `8765`)
- `LOL_LOCKFILE_PATH` (custom lockfile path if auto-discovery fails)
- `BUILD_PROVIDER_URL` (optional external build API, queried with `?championId=...`)

## 2) Start frontend (dev mode)

```powershell
cd mobile-panel
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

If backend is not same origin, set:

```powershell
$env:VITE_API_BASE = "http://YOUR_PC_IP:8765"
npm run dev -- --host 0.0.0.0 --port 5173
```

## 3) Open from phone

- Phone and PC must be on same LAN/Wi-Fi.
- Open either:
  - `http://YOUR_PC_IP:5173` (React dev server)
  - `http://YOUR_PC_IP:8765` (backend serves built panel from `mobile-panel/dist`)

## 4) Build frontend for backend static hosting

```powershell
cd mobile-panel
npm run build
```

After build, backend serves `mobile-panel/dist` automatically at `/`.

## Available API routes

- `GET /api/state` live snapshot
- `GET /api/champions` owned champions list
- `GET /api/runes/pages` current rune pages
- `GET /api/runes/styles` rune styles/perks catalog
- `GET /api/spells` summoner spell catalog
- `GET /api/builds/suggestions/{championId}` auto 3 build suggestions (role-based)
- `POST /api/champ-select/hover` `{ "championId": 266 }`
- `POST /api/champ-select/lock` `{ "championId": 266 }`
- `POST /api/champ-select/ban` `{ "championId": 157 }`
- `POST /api/champ-select/spells` `{ "spell1Id": 4, "spell2Id": 14 }`
- `POST /api/runes/apply` rune page payload
- `GET /api/health`
- `WS /ws` live state updates

## Notes

- The server uses LCU local API (lockfile auth), not public Riot REST endpoints.
- League client must be running.
- Windows firewall may need inbound allow for selected port.
- This build is manual-action oriented and blocks champion-select/rune/spell actions outside allowed phases.
- Mobile UI is phase-driven single screen: `ReadyCheck -> Ban -> Pick -> Rune+Spell`.

## Policy alignment checklist (important)

- Keep this as a companion tool (no scripting/macro loops, no gameplay automation).
- Only trigger actions from explicit user input.
- Avoid hidden-information features and in-game decision automation.
- Register and maintain the product on Riot Developer Portal if you distribute it.
