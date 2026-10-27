# tests/test_common.py
# run in root directory by: python3 -m unittest discover tests
import unittest
from shapely.geometry import Point, Polygon
from common.config import get_mqtt_config

class TestTrafficSystem(unittest.TestCase):
    def test_roi_point_in_polygon(self):
        """Test if vehicle centroid detection inside ROI polygon works correctly."""
        roi_polygon = Polygon([(100, 500), (300, 500), (300, 600), (100, 600)])
        
        point_inside = Point(200, 550)
        point_outside = Point(50, 100)
        
        self.assertTrue(roi_polygon.contains(point_inside))
        self.assertFalse(roi_polygon.contains(point_outside))

    def test_config_defaults(self):
        """Verify that configuration loads valid port numbers."""
        mqtt_config = get_mqtt_config()
        self.assertIsInstance(mqtt_config['broker_port'], int)
        self.assertGreater(mqtt_config['broker_port'], 0)

if __name__ == "__main__":
    unittest.main()