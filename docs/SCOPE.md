# Delivered scope and deliberate limitations

This package implements a working local simulator and the main end-to-end workflows. It does not claim every production requirement in the aspirational input specification is complete.

| Requirement | Delivery status |
|---|---|
| Reference dashboard arrangement | Implemented with responsive panel layout; synthetic scene replaces the reference photograph |
| React/TypeScript/Vite/Tailwind/Zustand | Implemented; detailed visual styling uses CSS alongside Tailwind setup |
| Recharts / Leaflet / Three.js | Implemented with local bundled dependencies |
| FastAPI, WebSockets, Pydantic, SQLAlchemy | Implemented |
| 50 Hz telemetry | Fixed-step generation/recording, 10 Hz UI delivery; not a hard-real-time guarantee |
| Recording/replay, mission CRUD lifecycle | Implemented; mission delete/edit-name operations are not exposed |
| Multiple cameras | Three synthetic view variants plus webcam and file modes; not three physical feeds |
| CV perception | Synthetic telemetry detections, confidence filter, labels/IDs and measured trails; no trained detector |
| RTSP / WebRTC | Future adapter boundary only; no gateway or signaling service shipped |
| Map | Offline grid and optional OpenStreetMap; no offline satellite imagery bundled |
| Geofence / no-fly zones | A 500 m visual geofence with outside warning; illustrative zone, no route enforcement |
| Waypoints | Persistent mission annotations displayed on the map; no autonomous waypoint navigation |
| Flight modes | Manual inputs, hold-mode behavior and scenario-driven AUTO; no PID/physics-engine autopilot |
| Emergency | Immediate simulated freeze and reset latch, not physical vehicle behavior |
| Hardware adapter | Protocol and explicitly unimplemented placeholder; no real transport |
| Security | Optional shared API key, validation and origin checks; no users/login/RBAC service despite reserved User model |
| Settings | Metric units, theme, rate, seed/speed, alert thresholds and local view controls; imperial units not implemented |
| Video recording | Not implemented; recorder captures telemetry, events and commands, not video |
| Replay alert panel | Alert/event history panels remain the current server history; recorded event data is available in JSON export |
| Database | Local SQLite verified; PostgreSQL-compatible schema and Compose config supplied, not integration-tested here |
| Production operations | No migrations, TLS termination, distributed locks, broker, per-user auth, quotas or long-term retention policy |

Pause stops simulation-time progression; it is distinct from recording pause, graph pause and replay pause. Takeoff begins from the ground as an explicit scenario initialization. Reset restores seeded initial airborne demo state. Scenario changes are simple research controls rather than constrained aircraft transitions.

Export and replay currently load an entire selected recording into memory (paged retrieval during replay). Use short laboratory sessions. A long-term recorder needs streaming export, disk quotas, retention and seekable server-side replay. A sudden process kill can lose the unflushed approximately one-second telemetry batch; interrupted recordings are marked on restart. Large synchronous database writes can affect cadence.

Settings values persist in the database. Appearance persists in browser local storage. The server starts in the nominal CRUISE demo, regardless of the last pre-shutdown vehicle state. User credentials and external service keys are never bundled.

For deployment beyond localhost: add TLS, a suitable identity/authorization layer, audit retention, backup/restore procedures and migrations. Keep the simulator as a single authoritative process until a broker architecture is implemented.
