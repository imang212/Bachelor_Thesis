"""
Central configuration loader.
Reads settings from the `.env` file in the repository root (see `.env.example`)
or from real environment variables. No secrets are stored in the source code.
The getters raise a clear error when a required value is missing, so a script
only fails if it actually needs that part of the configuration
(e.g. the Raspberry Pi does not need the PostgreSQL settings).
"""
import os
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv

# .env lives in the repository root, regardless of where the script is started from
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH)

def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable {name}. "
            f"Copy .env.example to .env (expected at {ENV_PATH}) and fill it in."
        )
    return value

def get_mqtt_config() -> Dict[str, Any]:
    """Keyword arguments for MQTTPublisher(**get_mqtt_config())."""
    return {
        "broker_host": _required("MQTT_BROKER_HOST"),
        "broker_port": int(os.getenv("MQTT_BROKER_PORT", 8883)),
        "topic": os.getenv("MQTT_TOPIC", "/videoanalyza"),
        "client_id": os.getenv("MQTT_CLIENT_ID", "hailo_tracker"),
        "username": _required("MQTT_USERNAME"),
        "password": _required("MQTT_PASSWORD"),
    }

def get_mqtt_connect_timeout() -> float:
    """Seconds to wait for the MQTT connection to be established."""
    return float(os.getenv("MQTT_CONNECT_TIMEOUT", 10))

def get_db_config() -> Dict[str, Any]:
    """Dictionary for PostgreDatabaseManager(get_db_config())."""
    return {
        "host": _required("DB_HOST"),
        "port": int(os.getenv("DB_PORT", 5432)),
        "database": os.getenv("DB_NAME", "hailo_db"),
        "user": _required("DB_USER"),
        "password": _required("DB_PASSWORD"),
        "min_connections": int(os.getenv("DB_MIN_CONNECTIONS", 2)),
        "max_connections": int(os.getenv("DB_MAX_CONNECTIONS", 10)),
    }

def get_camera_rtsp_url() -> str:
    """Full RTSP URL of the IP camera, e.g. rtsp://user:password@192.168.0.20/Stream."""
    return _required("CAMERA_RTSP_URL")
