# Telemetry conventions

All values are metric. Local position is ENU: x east, y north, z up. `position.alt` is height above the flat simulated home ground in meters; it is not mean-sea-level altitude. Latitude/longitude are derived from local position near Dehradun using a small-area Earth approximation.

| Field | Meaning / units |
|---|---|
| `timestamp` | ISO UTC simulation timestamp, epoch 2026-01-01 |
| `sim_time` | Seconds since last reset |
| `sequence` | Generated frame count since reset |
| `position.lat`, `position.lon` | Decimal degrees |
| `position.alt`, `position.x`, `position.y` | Meters, local flat-ground frame |
| `velocity.x/y/z` | m/s, z positive upward |
| `acceleration.x/y/z` | m/s²; stationary z contains +9.81 gravity-like sensor term |
| `gyro.x/y/z` | Degrees/second, derived from attitude differences |
| `orientation.roll/pitch/yaw` | Degrees; yaw normalized into [0,360) |
| `battery.percentage` | 0–100% modeled state of charge |
| `battery.voltage/current` | Modeled volts/amps |
| `gps.satellites/fix/hdop` | Synthetic satellite count, NO FIX/2D/3D, modeled HDOP |
| `rssi` | Modeled dBm |
| `rate` | Configured simulator Hz, not measured network throughput |
| `packet_loss`, `packets_lost`, `latency` | Simulated link metrics: %, count, milliseconds |
| `temperature` | Modeled °C |
| `state`, `mode`, `armed` | Simulated flight state |
| `scenario`, `paused`, `health` | Scenario and simulator state |
| `detections[]` | Synthetic class/confidence/bbox/timestamp/track ID |

Bounding boxes use normalized `[left, top, width, height]` coordinates relative to the generated camera viewport. These detections are not ML inference. Webcam and imported videos deliberately do not receive synthetic detection boxes.

Communication degradation changes the modeled link indicators and alerts; it does not intentionally disconnect the real browser WebSocket. The real connection status is driven by actual socket messages.

The 3D display maps ENU telemetry to the Three.js y-up scene for visualization. This is an illustrative attitude model, not a flight-control reference implementation.

Exported JSON includes exact stored telemetry values plus session metadata, commands, events and periodic detections. CSV flattens nested fields with dotted column names. Telemetry always carries detections at sample frequency; the separate detections table stores a periodic snapshot approximately once per wall second.
