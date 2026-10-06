# REST and WebSocket API

Base URL: `http://127.0.0.1:8000`. Interactive OpenAPI UI: `/docs`; machine-readable schema: `/openapi.json`.

Set `X-API-Key` when the server's `API_KEY` environment variable is nonempty. All `/api/` endpoints are protected in that mode. With an empty key, this is a local development API, not a multiuser authorization service.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/vehicles` | List vehicles |
| GET | `/api/vehicles/{id}` | Vehicle metadata |
| GET | `/api/telemetry/latest` | Latest full sample |
| GET | `/api/telemetry/history?limit=1000` | Recent buffer, up to 30,000 samples |
| GET | `/api/system/status` | Simulator, recorder, settings and pipeline error |
| GET / PUT | `/api/settings` | Read/update validated settings |
| POST | `/api/commands` | Validate, persist and apply simulated command |
| GET | `/api/commands` | Most recent 100 command results |
| POST | `/api/simulation/start` | Reconnect and resume simulator |
| POST | `/api/simulation/stop` | Disconnect and pause simulator |
| POST | `/api/simulation/reset` | Reset seeded state |
| GET / POST | `/api/missions` | List/create missions |
| PATCH | `/api/missions/{id}` | Validated status transition |
| GET | `/api/missions/{id}/timeline` | Mission event timeline |
| GET / POST | `/api/missions/{id}/waypoints` | Planning annotation markers |
| DELETE | `/api/waypoints/{id}` | Delete one waypoint |
| GET | `/api/sessions` | Sessions and persisted sample counts |
| POST | `/api/sessions/start?mission_id=...` | Start recording, optional mission |
| POST | `/api/sessions/stop` | Flush and stop recording |
| POST | `/api/sessions/pause` | Pause capture without pausing simulation |
| POST | `/api/sessions/resume` | Resume capture |
| GET | `/api/sessions/{id}/points?offset=0&limit=5000` | Ordered samples, page limit 10,000 |
| GET | `/api/sessions/{id}/export?format=json` | Session bundle; `csv` exports telemetry |
| GET | `/api/alerts` | Latest 200 alerts including resolved ones |
| POST | `/api/alerts/{id}/ack` | Acknowledge alert |
| GET | `/api/events` | Most recent 200 events |

Command examples:

```json
{"type":"SET_CONTROL","value":{"throttle":55,"yaw":10,"pitch":2,"roll":-3},"source":"dashboard"}
```

```json
{"type":"SET_SCENARIO","value":"ORBIT"}
```

Types: ARM, DISARM, EMERGENCY_STOP, RESET, PAUSE, RESUME, LAND, RTH, SET_MODE, SET_CONTROL, SET_SCENARIO. Ranges: throttle 0–100; attitude controls −100–100. Unsupported fields, nonfinite values and invalid bodies fail schema validation. Semantically invalid commands are stored and return `status: REJECTED` plus `error` with HTTP 200; clients must inspect the status. Schema errors use 422, missing records 404 and invalid session/mission transitions 409.

WebSockets:

- `/ws/telemetry`: envelope `{type:"telemetry", data:<Telemetry>, server_time, recording, record_paused, sim_connected}`.
- `/ws/events`: event/alert objects with a `type` discriminator.
- `/ws/commands`: send a command body; receive persistent command-result objects.

When API authentication is configured, send `{"api_key":"YOUR_KEY"}` as the first WebSocket frame within five seconds. It is not a query parameter. Browser origins must match CORS_ORIGINS or the server origin. Clients may send `{"type":"ping"}`; idle server channels send heartbeat objects every five seconds. Dashboard reconnect uses exponential backoff capped at ten seconds and a twelve-second telemetry watchdog.

Mission transitions: PLANNED → RUNNING/ABORTED; RUNNING → PAUSED/COMPLETED/ABORTED; PAUSED → RUNNING/COMPLETED/ABORTED. Completed and aborted missions are terminal. Mission status is organizational metadata and does not itself arm or fly the vehicle.
