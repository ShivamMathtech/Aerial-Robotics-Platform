# Verification report

Executed in the build environment on 2026-10-06 using Python 3.12.14, Node.js 24.19.0 and Chromium 134 (Playwright).

| Check | Result |
|---|---|
| Backend Pytest | 25 passed |
| Frontend Vitest | 4 passed |
| TypeScript check + Vite production build | Passed |
| Playwright live dashboard workflow | Passed |
| Playwright mission and 390 px mobile layout | Passed |
| Built frontend served directly by FastAPI (Python-only path) | Passed: same-origin API/WebSocket, map marker in viewport, no page errors |

Backend checks cover deterministic seeded samples, all 12 scenarios, landing and return-home integration, emergency/reset behavior, valid telemetry, command rejection, alert severity, REST and WebSocket communication, recording pause/resume, exact JSON round-trip of saved telemetry, CSV fields, mission transitions, API authentication and acknowledgement.

Browser tests verify an actual WebSocket connection, changing altitude, rendered charts, geographic vehicle marker, WebGL canvas, simulator pause/resume, scenario selection, emergency alert, reset, recording start/stop, session load, replay timeline advancement, disabled flight controls during replay, return-to-live, mission creation and status transitions. They also check for JavaScript page errors and mobile horizontal overflow.

The first browser attempt could not reach the backend because the execution environment isolates separately launched processes. Running backend and browser tests in the same execution context resolved that test infrastructure issue.

Not executed here: Windows batch launcher on Windows, Docker Compose/PostgreSQL integration, physical webcams, user-provided codecs and video files, external map tile delivery, real aircraft (not implemented), and sustained multi-hour/large-session load tests. No production certification or distributed concurrency guarantee is implied.

Nonblocking build note: the Recharts vendor chunk is larger than Vite's default 500 kB chunk advisory. Map, Three.js and chart modules are split into separate bundles. A dependency emits a test-only AnyIO deprecation warning; all assertions pass.
