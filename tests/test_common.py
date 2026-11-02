# tests/test_common.py
# run in root directory by: python3 -m unittest discover tests
import os
import unittest
from unittest.mock import patch
from shapely.geometry import Point, Polygon
from common.config import get_db_config, get_mqtt_config, get_camera_rtsp_url

class TestTrafficSystem(unittest.TestCase):
    def test_roi_point_in_polygon(self):
        """Test if normalized vehicle centroid detection inside Hailo/GPU ROI polygon works."""
        zone_points = [(0.1, 0.85), (0.46, 0.85), (0.6, 0.9), (0.45, 0.9), (0.4, 1.0)]
        roi_polygon = Polygon(zone_points)

        point_inside = Point(0.30, 0.88)
        point_outside = Point(0.80, 0.50)

        self.assertTrue(roi_polygon.contains(point_inside))
        self.assertFalse(roi_polygon.contains(point_outside))

    @patch.dict(os.environ, {
        "MQTT_BROKER_HOST": "mqtt.example.com",
        "MQTT_BROKER_PORT": "8883",
        "MQTT_TOPIC": "/videoanalyza",
        "MQTT_CLIENT_ID": "test_client",
        "MQTT_USERNAME": "test_user",
        "MQTT_PASSWORD": "test_password",
    })
    def test_get_mqtt_config(self):
        """Verify that MQTT configuration loads and converts types properly."""
        cfg = get_mqtt_config()
        self.assertEqual(cfg["broker_host"], "mqtt.example.com")
        self.assertEqual(cfg["broker_port"], 8883)
        self.assertIsInstance(cfg["broker_port"], int)
        self.assertEqual(cfg["username"], "test_user")

    @patch.dict(os.environ, {
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "traffic_monitoring",
        "DB_USER": "postgres",
        "DB_PASSWORD": "secret",
    })
    def test_get_db_config(self):
        """Verify that PostgreSQL configuration dictionary is constructed properly."""
        cfg = get_db_config()
        self.assertEqual(cfg["host"], "localhost")
        self.assertEqual(cfg["port"], 5432)
        self.assertEqual(cfg["database"], "traffic_monitoring")

    @patch.dict(os.environ, {"CAMERA_RTSP_URL": "rtsp://user:pass@192.0.2.10:554/Stream"})
    def test_get_camera_rtsp_url(self):
        """Verify that camera RTSP URL loader returns expected string."""
        self.assertEqual(get_camera_rtsp_url(), "rtsp://user:pass@192.0.2.10:554/Stream")
    
if __name__ == "__main__":
    unittest.main()