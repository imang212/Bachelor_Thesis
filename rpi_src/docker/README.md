# Docker deployment simulation
Runs the whole traffic-detection system as a set of containers: a simulated IP camera streaming `videos/sample_video.mp4`, the Hailo detection pipeline, a PostgreSQL database, a service that stores MQTT detections in the database, the FastAPI backend, and the Streamlit dashboard.

All commands below are run from the **repository root**, because that is where the `.env` file and the `videos/` folder live. Paths inside `rpi_src/docker/docker-compose.yml` are relative to the `rpi_src/docker/` folder, so the repository root is referenced through `../..`.

## Architecture

```
    camera_sim ──RTSP──▶ rtsp_server ──RTSP──▶ ai_pipeline ──MQTT (TLS)──▶ external broker
    (ffmpeg, loops       (mediamtx)            (GStreamer + Hailo-8)               │
     sample_video.mp4)                                                             │ subscribe
                                                                                   ▼
    dashboard ──HTTP──▶ api ──SQL──▶ postgres ◀──SQL── db_subscriber ◀─────────────┘
    (Streamlit :8501)   (FastAPI :8000)   (:5432)      (MQTT → database)
```

The MQTT broker is **not** part of this compose file. Both `ai_pipeline` (publisher) and `db_subscriber` (subscriber) connect to the same external broker defined in `.env`.

## Services

| Service | Container | Image / Build | Port | Purpose |
|---|---|---|---|---|
| `postgres` | `hailo_db` | `postgres:15` | 5432 | Detection database, schema created from `rpi_src/db/init_hailo.sql` |
| `rtsp_server` | `rtsp_server` | `bluenviron/mediamtx:1.9.3` | 8554 | RTSP server the simulated camera publishes to |
| `camera_sim` | `camera_simulator` | `jrottenberg/ffmpeg:6.1-alpine` | – | Streams `videos/sample_video.mp4` in a loop as `rtsp://rtsp_server:8554/mystream` |
| `ai_pipeline` | `detection_pipeline` | `rpi_src/docker/Dockerfile.pipeline` | – | GStreamer + Hailo detection and tracking, publishes detections to MQTT |
| `db_subscriber` | `hailo_db_subscriber` | `rpi_src/docker/Dockerfile.api` | – | Subscribes to the MQTT topic and stores detections in PostgreSQL |
| `api` | `hailo_api` | `rpi_src/docker/Dockerfile.api` | 8000 | FastAPI backend (REST API) |
| `dashboard` | `hailo_dashboard` | `rpi_src/docker/Dockerfile.api` | 8501 | Streamlit analytics dashboard |

## Requirements
- Docker Engine with the Compose plugin (`docker compose`, v2).
- For `ai_pipeline`: a Raspberry Pi 5 (arm64) with a Hailo-8 / AI HAT+ and the HailoRT driver installed on the host, so that the device `/dev/hailo0` exists (see `rpi_src/autosetup_hailo_rpi5.sh`).
- A reachable MQTT broker (TLS) and its credentials.

Without Hailo hardware you can still start the rest of the stack on any PC — see [Running without Hailo](#running-without-hailo).

## Setup

### 1. Configure `.env`

```bash
cp .env.example .env
```

Fill in at least the following variables in `.env` (the file is ignored by git, never commit it):

| Variable | Used by |
|---|---|
| `DB_USER`, `DB_PASSWORD`, `DB_NAME` | `postgres` (creates the user and database), `api`, `db_subscriber` |
| `POSTGRES_PORT` *(optional, default 5432)* | Host port of PostgreSQL |
| `MQTT_BROKER_HOST`, `MQTT_BROKER_PORT`, `MQTT_TOPIC`, `MQTT_USERNAME`, `MQTT_PASSWORD` | `ai_pipeline`, `db_subscriber`, `api` |

`DB_HOST` is overridden to `postgres` inside Docker, so whatever you have in `.env` for local runs does not matter here. `CAMERA_RTSP_URL` is not needed while the simulated camera is used.

> The database user and password are applied only when the `postgres_data` volume is created for the first time. If you change them later, recreate the volume with `docker compose -f rpi_src/docker/docker-compose.yml --env-file .env down -v`.

### 2. Add a test video
The default test video is already included in the repository at `videos/sample_video.mp4` (tracked via Git LFS) and is automatically mounted into the `camera_sim` container.

The video must be **H.264**, because the camera simulator copies the stream without re-encoding (`-c copy`). For other codecs replace `copy` with `libx264` in the `camera_sim` command.

### 3. Build and start (on Raspberry Pi 5 with Hailo-8)

```bash
docker compose -f rpi_src/docker/docker-compose.yml --env-file .env up --build
```

Add `-d` to run in the background.

## Running without Hailo

The `ai_pipeline` service requires the `/dev/hailo0` device and will not start on a regular PC without Hailo hardware. To run the simulation stack on any PC, start the remaining services explicitly:

```bash
docker compose -f rpi_src/docker/docker-compose.yml --env-file .env up --build \
  postgres rtsp_server camera_sim db_subscriber api dashboard
```

Nothing then publishes detections to MQTT by itself. You can publish detections from the reference GPU script (`pc_src/yoloTrafficDetectionSystem_PC_GPU.py`) pointing at the same MQTT broker and topic.

## Access Endpoints

| Service | Address |
|---|---|
| Streamlit dashboard | `http://localhost:8501` |
| FastAPI Swagger UI | `http://localhost:8000/docs` |
| Simulated camera (RTSP) | `rtsp://localhost:8554/mystream` |
| PostgreSQL | `localhost:5432` (or `POSTGRES_PORT`) |

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
docker compose -f rpi_src/docker/docker-compose.yml --env-file .env logs -f ai_pipeline db_subscriber
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

## Using a real IP camera instead of the simulator

1. Set `CAMERA_RTSP_URL` in `.env`, e.g. `rtsp://user:password@192.0.2.20/Stream`.
2. In `rpi_src/docker/docker-compose.yml`, remove the `--rtsp-link ...` argument from the `ai_pipeline` command. Without it the pipeline uses `CAMERA_RTSP_URL`.
3. Remove `camera_sim` and `rtsp_server` and the `depends_on: camera_sim` entry of `ai_pipeline` (or just do not start them).

## Useful commands

All with `-f docker/docker-compose.yml --env-file .env` after `docker compose`:

```bash
docker compose -f rpi_src/docker/docker-compose.yml --env-file .env logs -f  # logs of all services
docker compose -f rpi_src/docker/docker-compose.yml --env-file .env logs -f api
docker compose -f rpi_src/docker/docker-compose.yml --env-file .env restart api
docker compose -f rpi_src/docker/docker-compose.yml --env-file logs -f ai_pipeline        # logs of one service
docker compose -f rpi_src/docker/docker-compose.yml --env-file restart ai_pipeline        # restart one service
docker compose -f rpi_src/docker/docker-compose.yml --env-file up --build ai_pipeline     # rebuild and start one service
docker compose -f rpi_src/docker/docker-compose.yml --env-file .env down # stop everything (keeps the database)
docker compose -f rpi_src/docker/docker-compose.yml --env-file .env down -v # stop and delete the database volume
```

## Troubleshooting

| Problem | Cause / fix |
|---------|-------------|
| `DB_USER is missing in .env` | The variable is not set, or `--env-file .env` was left out of the command. |
| `camera_sim` keeps restarting | The RTSP server was not ready yet (it retries automatically), or `videos/sample_video.mp4` is missing or is not a real video file (check `git lfs pull`). |
| `ai_pipeline`: `no such file or directory: /dev/hailo0` | The host has no Hailo device or driver. See [Running without Hailo](#running-without-hailo). |
| Port 5432 is already in use | Set another `POSTGRES_PORT` in `.env` (e.g. `POSTGRES_PORT=5434`). |
| Changed `DB_PASSWORD`, but login fails | The password is stored in the existing volume. Run `docker compose ... down -v` and start again. |
| Empty dashboard | Check that `db_subscriber` logs incoming MQTT messages and that `ai_pipeline` (or another publisher) uses the same `MQTT_TOPIC`. |

## Folder layout
```
Bachelor_Thesis/
├── .env                         # local environment variables (not in git)
├── videos/
│   └── sample_video.mp4         # default test video (tracked via Git LFS)
└── rpi_src/
    └── docker/
        ├── docker-compose.yml   # full stack definition
        ├── Dockerfile.pipeline  # Hailo + GStreamer pipeline image (Python 3.11)
        ├── Dockerfile.api       # image shared by api, dashboard and db_subscriber
        ├── api_requirements.txt # Python dependencies for API, dashboard & DB subscriber
        └── README.md            # this guide
```
