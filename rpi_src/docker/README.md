# Docker deployment simulation

Runs the whole traffic-detection system as a set of containers: a simulated IP camera,
the Hailo detection pipeline, a PostgreSQL database, a service that stores MQTT
detections in the database, the FastAPI backend and the Streamlit dashboard.

All commands below are run from the **repository root**, because that is where the
`.env` file lives. Paths inside `docker-compose.yml` are relative to the `docker/`
folder, so the source code is referenced through `..`.

## Architecture

```
 camera_sim ──RTSP──▶ rtsp_server ──RTSP──▶ ai_pipeline ──MQTT (TLS)──▶ external broker
 (ffmpeg, loops       (mediamtx)            (GStreamer + Hailo-8)               │
  sample_video.mp4)                                                             │ subscribe
                                                                                ▼
 dashboard ──HTTP──▶ api ──SQL──▶ postgres ◀──SQL── db_subscriber ◀────────────┘
 (Streamlit :8501)   (FastAPI :8000)   (:5432)      (MQTT → database)
```

The MQTT broker is **not** part of this compose file. Both `ai_pipeline` (publisher)
and `db_subscriber` (subscriber) connect to the same external broker defined in `.env`.

## Services

| Service         | Container             | Image / build                 | Port  | Purpose |
|-----------------|-----------------------|-------------------------------|-------|---------|
| `postgres`      | `hailo_db`            | `postgres:15`                 | 5432  | Detection database, schema created from `rpi_src/db/init_hailo.sql` |
| `rtsp_server`   | `rtsp_server`         | `bluenviron/mediamtx`         | 8554  | RTSP server the simulated camera publishes to |
| `camera_sim`    | `camera_simulator`    | `jrottenberg/ffmpeg`          | –     | Streams `camera_simulator/sample_video.mp4` in a loop as `rtsp://rtsp_server:8554/mystream` |
| `ai_pipeline`   | `detection_pipeline`  | `docker/Dockerfile.pipeline`  | –     | GStreamer + Hailo detection and tracking, publishes detections to MQTT |
| `db_subscriber` | `hailo_db_subscriber` | `docker/Dockerfile.api`       | –     | Subscribes to the MQTT topic and stores detections in PostgreSQL |
| `api`           | `hailo_api`           | `docker/Dockerfile.api`       | 8000  | FastAPI backend (REST + WebSocket) |
| `dashboard`     | `hailo_dashboard`     | `docker/Dockerfile.api`       | 8501  | Streamlit dashboard |

## Requirements

- Docker Engine with the Compose plugin (`docker compose`, v2).
- For `ai_pipeline`: a Raspberry Pi 5 (arm64) with a Hailo-8 / AI HAT+ and the HailoRT
  driver installed on the host, so that the device `/dev/hailo0` exists
  (see `rpi_src/auto_setup_repair_hailo_rpi5.sh`).
- A reachable MQTT broker (TLS) and its credentials.

Without Hailo hardware you can still start the rest of the stack, see
[Running without Hailo](#running-without-hailo).

## Setup

### 1. Configure `.env`

```bash
cp .env.example .env
```

Fill in at least the following variables (the file is ignored by git, never commit it):

| Variable                                   | Used by                                    |
|--------------------------------------------|--------------------------------------------|
| `DB_USER`, `DB_PASSWORD`, `DB_NAME`        | `postgres` (creates the user and database), `api`, `db_subscriber` |
| `POSTGRES_PORT` *(optional, default 5432)* | host port of PostgreSQL                    |
| `MQTT_BROKER_HOST`, `MQTT_BROKER_PORT`, `MQTT_TOPIC`, `MQTT_USERNAME`, `MQTT_PASSWORD` | `ai_pipeline`, `db_subscriber`, `api` |

`DB_HOST` is overridden to `postgres` inside Docker, so whatever you have in `.env`
for local runs does not matter here. `CAMERA_RTSP_URL` is not needed while the
simulated camera is used.

> The database user and password are applied only when the `postgres_data` volume is
> created for the first time. If you change them later, recreate the volume with
> `docker compose ... down -v`.

### 2. Add a test video

Put a video file into the `camera_simulator/` folder and name it `sample_video.mp4`:

```
docker/camera_simulator/sample_video.mp4
```

The video must be **H.264**, because the camera simulator copies the stream without
re-encoding (`-c copy`). For other codecs replace `copy` with `libx264` in the
`camera_sim` command. Video files are ignored by git.

### 3. Build and start

```bash
docker compose -f docker/docker-compose.yml --env-file .env up --build
```

Add `-d` to run in the background.

## Access

| What                      | Address                                    |
|---------------------------|--------------------------------------------|
| Streamlit dashboard       | http://localhost:8501                      |
| FastAPI Swagger UI        | http://localhost:8000/docs                 |
| Simulated camera (RTSP)   | `rtsp://localhost:8554/mystream`           |
| PostgreSQL                | `localhost:5432` (or `POSTGRES_PORT`)      |

### Check the simulated camera stream

```bash
ffplay rtsp://localhost:8554/mystream
# or
vlc rtsp://localhost:8554/mystream
# or
gst-launch-1.0 rtspsrc location="rtsp://localhost:8554/mystream" latency=0 \
  ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! autovideosink
```

### Watch MQTT traffic

Watch the logs of the publisher and the subscriber:

```bash
docker compose -f docker/docker-compose.yml logs -f ai_pipeline db_subscriber
```

Or subscribe from the host (requires `mosquitto-clients`):

```bash
mosquitto_sub -h <broker_host> -p <broker_port> -u <username> -P <password> \
  --capath /etc/ssl/certs -t '<MQTT_TOPIC>' -v
```

### Query the database

```bash
docker exec -it hailo_db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
  "SELECT class_name, COUNT(DISTINCT track_id) AS unique_tracks, COUNT(*) AS detections
   FROM detections GROUP BY class_name ORDER BY unique_tracks DESC;"'
```

## Running without Hailo

The `ai_pipeline` service needs the `/dev/hailo0` device and will not start without it.
To run everything else, start the services explicitly:

```bash
docker compose -f docker/docker-compose.yml --env-file .env up --build \
  postgres rtsp_server camera_sim db_subscriber api dashboard
```

Nothing then publishes detections to MQTT by itself. Publish them from another
machine, for example with the GPU reference script (`pc_src/`) pointing at the same
broker and topic.

## Using a real IP camera instead of the simulator

1. Set `CAMERA_RTSP_URL` in `.env`, e.g. `rtsp://user:password@192.168.0.20/Stream`.
2. In `docker-compose.yml`, remove the `--rtsp-link ...` argument from the `ai_pipeline`
   command. Without it the pipeline uses `CAMERA_RTSP_URL`.
3. Remove `camera_sim` and `rtsp_server` and the `depends_on: camera_sim` entry of
   `ai_pipeline` (or just do not start them).

## Useful commands

All with `-f docker/docker-compose.yml --env-file .env` after `docker compose`:

```bash
docker compose ... logs -f                    # logs of all services
docker compose ... logs -f ai_pipeline        # logs of one service
docker compose ... restart ai_pipeline        # restart one service
docker compose ... up --build ai_pipeline     # rebuild and start one service
docker compose ... down                       # stop everything (keeps the database)
docker compose ... down -v                    # stop and delete the database volume
```

## Troubleshooting

| Problem | Cause / fix |
|---------|-------------|
| `DB_USER is missing in .env` | The variable is not set, or `--env-file .env` was left out of the command. |
| `camera_sim` keeps restarting | The RTSP server was not ready yet (it retries automatically), or `sample_video.mp4` is missing or is not H.264. |
| `ai_pipeline`: `no such file or directory: /dev/hailo0` | The host has no Hailo device or driver. See [Running without Hailo](#running-without-hailo). |
| Port 5432 is already in use | Set another `POSTGRES_PORT` in `.env`. |
| Changed `DB_PASSWORD`, but login fails | The password is stored in the existing volume. Run `docker compose ... down -v` and start again. |
| Empty dashboard | Check that `db_subscriber` logs incoming MQTT messages and that `ai_pipeline` (or another publisher) uses the same `MQTT_TOPIC`. |

## Folder layout

```
docker/
├── docker-compose.yml
├── Dockerfile.pipeline      # Hailo pipeline image (arm64, GStreamer, HailoRT)
├── Dockerfile.api           # image shared by api, dashboard and db_subscriber
├── README.md
└── camera_simulator/
    └── sample_video.mp4     # your test video (not in git)
```

The container images pin tool versions where possible (`postgres:15`, `mediamtx`,
`ffmpeg`). Check that the tags in `docker-compose.yml` still exist and update them
deliberately rather than using `:latest`.
