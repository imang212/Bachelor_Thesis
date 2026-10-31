import os
import json
import threading
from datetime import datetime
from collections import defaultdict
from typing import List, Tuple, Optional, Dict, Any
import cv2
import numpy as np

class Detection:
    """
    Data class representing a single detected object.
    Attributes:
        bbox: Bounding box coordinates (x1, y1, x2, y2)
        label: Object class name (e.g., "car", "truck", "person")
        confidence: Detection confidence score (0.0 - 1.0)
        track_id: Unique tracking ID assigned by tracker
    """
    def __init__(self, bbox: Tuple[int, int, int, int], label: str, confidence: float, track_id: int = -1):
        self.bbox = bbox
        self.label = label
        self.confidence = confidence
        self.track_id = track_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert detection to dictionary for JSON serialization."""
        return {
            'bbox': list(self.bbox),
            'label': self.label,
            'confidence': round(self.confidence, 3),
            'track_id': self.track_id
        }

class TrafficCounter:
    """
    Traffic counter using simple IoU-based tracking. 
    Counts unique objects that pass through the scene.
    """
    def __init__(self):
        """
        Initialize traffic counter.
        Args:
            max_age: Max frames to keep track alive without detection
            min_hits: Min detections before track is confirmed
        """       
        self.object_counts: Dict[str, int] = defaultdict(int)
        self.tracked_ids: set = set()
        self.total_count: int = 0

    def update(self, detections: List[Detection]) -> List[Detection]:
        """Register new track_ids and increment per-class counters."""
        for det in detections:
            if det.track_id != -1 and det.track_id not in self.tracked_ids:
                self.tracked_ids.add(det.track_id)
                self.object_counts[det.label] += 1
                self.total_count += 1
        return detections

    def get_counts(self) -> Dict[str, int]:
        """Get count of each object type."""
        return dict(self.object_counts)

    def get_total_count(self) -> int:
        """Get total count of all tracked objects."""
        return self.total_count

class VideoStatistics:
    """
    Tracks and calculates statistics for a single recording session.
    Owned by VideoRecorder — one instance per recording.
    reset() is called automatically on VideoRecorder.start() so the same
    VideoRecorder object can be reused across multiple sessions.
    """
    def __init__(self):
        self.detections_per_class: Dict[str, int] = defaultdict(int)
        self.confidence_sum_per_class: Dict[str, float] = defaultdict(float)
        self.total_frames: int = 0
        self.frames_with_detections: int = 0
        self.object_counts: Dict[str, int] = {
            "person": 0, "car": 0, "truck": 0,
            "bus": 0, "motorcycle": 0, "bicycle": 0,
        }
        self.unique_track_ids: set = set()
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def reset(self):
        """Clear all counters — called at the start of every new recording."""
        self.__init__()

    def add_detection(self, class_name: str, confidence: float, track_id: Optional[int] = None):
        """Register one detected object in the current frame."""
        self.detections_per_class[class_name] += 1
        self.confidence_sum_per_class[class_name] += confidence
        if track_id is not None and track_id not in self.unique_track_ids:
            self.unique_track_ids.add(track_id)
            if class_name in self.object_counts:
                self.object_counts[class_name] += 1

    def add_frame(self, has_detections: bool = False):
        """Record that one frame was processed."""
        self.total_frames += 1
        if has_detections:
            self.frames_with_detections += 1

    def get_summary(self) -> Dict[str, Any]:
        """Return a JSON-serialisable statistics dictionary."""
        summary: Dict[str, Any] = {
            "total_frames": self.total_frames,
            "frames_with_detections": self.frames_with_detections,
            "unique_objects_tracked": len(self.unique_track_ids),
            "processing_time": None,
            "fps": "n/a",
            "detections_by_class": {},
        }
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
            summary["recording_start"] = self.start_time.isoformat()
            summary["recording_end"] = self.end_time.isoformat()
            summary["processing_time"] = f"{duration:.2f} seconds"
            summary["fps"] = (
                f"{self.total_frames / duration:.2f}" if duration > 0 else "N/A"
            )
        for class_name, count in self.detections_per_class.items():
            avg_conf = (
                self.confidence_sum_per_class[class_name] / count if count > 0 else 0.0
            )
            summary["detections_by_class"][class_name] = {
                "count": count,
                "real_object_count": self.object_counts.get(class_name, 0),
                "average_confidence": f"{avg_conf:.4f}",
            }
        return summary

class VideoRecorder:
    """
    Records annotated pipeline frames to a single MP4 file per session
    and exports companion JSON statistics.
    """
    def __init__(self, output_dir: str = "recordings", fps: int = 20, resolution: Tuple[int, int] = (640, 640)):
        self.output_dir = output_dir
        self.fps = fps
        self.resolution = resolution
        self._writer: Optional[cv2.VideoWriter] = None
        self._lock = threading.Lock()
        self._output_path: Optional[str] = None
        self._frame_count: int = 0
        self.stats: VideoStatistics = VideoStatistics()

    def start(self) -> str:
        """Open a new MP4 file and start recording."""
        with self._lock:
            if self._writer is not None:
                raise RuntimeError("[VideoRecorder] Already recording – call stop() first.")
            os.makedirs(self.output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.mp4"
            self._output_path = os.path.join(self.output_dir, filename)
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self._writer = cv2.VideoWriter(
                self._output_path, fourcc, self.fps, self.resolution
            )
            if not self._writer.isOpened():
                self._writer = None
                raise RuntimeError(
                    f"[VideoRecorder] cv2.VideoWriter failed to open '{self._output_path}'."
                )
            self._frame_count = 0
            self.stats.reset()
            self.stats.start_time = datetime.now()
            print(f"[VideoRecorder] Recording started → {self._output_path}")
            return self._output_path

    def write(self, frame: np.ndarray) -> bool:
        """Write one BGR frame to the open recording."""
        with self._lock:
            if self._writer is None:
                return False
            w, h = self.resolution
            fh, fw = frame.shape[:2]
            if (fw, fh) != (w, h):
                frame = cv2.resize(frame, (w, h))
            self._writer.write(frame)
            self._frame_count += 1
            return True

    def stop(self) -> Optional[str]:
        """Flush and close the current recording, then write a companion JSON statistics file."""
        with self._lock:
            if self._writer is None:
                return None
            self._writer.release()
            self._writer = None
            path = self._output_path
            self._output_path = None
            print(f"[VideoRecorder] Recording stopped → {path} ({self._frame_count} frames)")
            self._frame_count = 0
        self.stats.end_time = datetime.now()
        self._write_stats_json(path)
        return path

    def _write_stats_json(self, video_path: Optional[str]):
        """Serialise VideoStatistics.get_summary() to a .json file beside the MP4."""
        if video_path is None:
            return
        json_path = os.path.splitext(video_path)[0] + "_stats.json"
        summary = self.stats.get_summary()
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            print(f"[VideoRecorder] Statistics saved  → {json_path}")
        except Exception as e:
            print(f"[VideoRecorder] Failed to write statistics JSON: {e}")

    def feed_detections(self, detections: List[Detection]):
        """Update statistics for the current frame."""
        if not self.is_recording:
            return
        self.stats.add_frame(has_detections=bool(detections))
        for det in detections:
            self.stats.add_detection(
                class_name=det.label,
                confidence=det.confidence,
                track_id=det.track_id if det.track_id != -1 else None,
            )

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._writer is not None

    @property
    def output_path(self) -> Optional[str]:
        with self._lock:
            return self._output_path

    @property
    def frame_count(self) -> int:
        return self._frame_count
