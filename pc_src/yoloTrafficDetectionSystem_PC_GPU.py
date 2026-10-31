import os
import sys
import queue
import time
import threading
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional, Any
import av
import cv2
import numpy as np
import torch
from dotenv import load_dotenv
from shapely.geometry import Point, Polygon
from ultralytics import YOLO

# Add project root to sys.path so 'common' and 'pc_src' packages are always found
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from common.MQTTClient import MQTTPublisher

try:
    from pc_src.traffic_stats import Detection, TrafficCounter, VideoRecorder
except ImportError:
    from traffic_stats import Detection, TrafficCounter, VideoRecorder

class TrafficDetector:
    """
    YOLO-based object detector optimized for PC GPU (CUDA) with ByteTrack.
    Aligned with Hailo-8 GStreamer pipeline parameters.
    """
    TRAFFIC_CLASSES = {'person', 'car', 'motorcycle', 'bicycle', 'bus', 'truck'}
    def __init__(
        self,
        model_path: str = "yolov8m.pt",
        tracker_config: str = "bytetrack.yaml",
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.5,
        img_size: Tuple[int, int] = (640, 640),
        device: str = "auto"
    ):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.img_size = img_size
        self.tracker_config = tracker_config
        if device == "auto":
            if not torch.cuda.is_available():
                print("[TrafficDetector] CUDA not available — exiting.")
                raise SystemExit(1)
            self.device = "cuda"
        else:
            self.device = device
        print(f"[TrafficDetector] Using device: {self.device}")
        print(f"[TrafficDetector] Tracker    : {tracker_config}")
        print(f"[TrafficDetector] Loading YOLO model: {model_path}")
        self.model = YOLO(model_path)
        self.model.fuse()
        # Warm-up inference to compile model / CUDA kernels
        dummy = np.zeros((img_size[1], img_size[0], 3), dtype=np.uint8)
        _ = self.model.track(
            dummy,
            imgsz=img_size,
            verbose=False,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            device=self.device,
            tracker=self.tracker_config,
            persist=True
        )
        print(f"[TrafficDetector] Ready  resolution={img_size}  device={self.device}")

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Run YOLO + ByteTrack on a single frame."""
        results = self.model.track(
            frame,
            imgsz=self.img_size,
            verbose=False,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            device=self.device,
            tracker=self.tracker_config,
            persist=True
        )
        detections: List[Detection] = []
        for result in results:
            boxes = getattr(result, 'boxes', None)
            if boxes is None or boxes.id is None:
                continue
            for box in boxes:
                label = self.model.names[int(box.cls[0])]
                if label not in self.TRAFFIC_CLASSES:
                    continue
                track_id = int(box.id[0]) if box.id is not None else -1
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detections.append(
                    Detection(
                        bbox=(x1, y1, x2, y2),
                        label=label,
                        confidence=float(box.conf[0]),
                        track_id=track_id
                    )
                )
        return detections

    @staticmethod
    def draw_detections(frame: np.ndarray, detections: List[Detection], show_tracking: bool = True) -> np.ndarray:
        """Draw bounding boxes and labels on frame."""
        annotated = frame.copy()
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            color = (0, 255, 0) if det.label in ['car', 'truck', 'bus', 'motorcycle', 'bicycle'] else (255, 0, 0)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            label_text = f"{det.label} {det.confidence:.2f}"
            if show_tracking and det.track_id != -1:
                label_text += f" ID:{det.track_id}"
            (text_width, text_height), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated, (x1, y1 - text_height - 4), (x1 + text_width, y1), color, -1)
            cv2.putText(annotated, label_text, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        return annotated

class VideoStreamer:
    """
    Threaded video capture for RTSP streams or local cameras.
    - For local files: uses a lossless queue without FPS throttling so every
      single frame is processed at maximum GPU speed.
    - For live RTSP streams: keeps only the latest frame to minimize latency.
    Usage examples:
        RTSP camera : VideoStreamer(source="rtsp://user:pass@192.168.1.100:554/stream1")
        Local webcam: VideoStreamer(source=0)
        Video file  : VideoStreamer(source="/path/to/video.mp4")
    Crop behaviour (crop_rect):
        Pass crop_rect=(x, y, w, h) to extract a 640×640 (or any size) region
        from the raw decoded frame BEFORE it is stored.  The crop is applied
        after decoding but before the resize step, so `resolution` is the final
        output size of the cropped region.  If crop_rect is None the full frame
        is resized to `resolution` as before.
    Example – crop a 640×640 patch starting at pixel (320, 180):
        VideoStreamer(source=..., resolution=(640, 640), crop_rect=(320, 180, 640, 640))
    """
    def __init__(
            self,
            source: Any = 0,
            resolution: Tuple[int, int] = (1280, 720), 
            fps: int = 20,
            crop_rect: Optional[Tuple[int, int, int, int]] = None, 
            throttle_fps: bool = False,
        ):
        """
        Args:
            source:      RTSP URL (str), device index (int), or video file path (str)
            resolution:  Desired *output* resolution (width, height).
                         If crop_rect is given this is the size of the cropped tile.
                         If crop_rect is None the full frame is resized to this.
            fps:         Target frames-per-second (throttles read loop speed)
            crop_rect:   Optional (x, y, w, h) crop window applied to the raw
                         decoded frame before resize.  Set to None to disable.
        """
        self.source = source
        self.resolution = resolution
        self.target_fps = fps
        self.frame_time = 1.0 / fps
        self.crop_rect = crop_rect
        self.is_file = isinstance(source, str) and os.path.isfile(source)
        self.throttle_fps = throttle_fps if not self.is_file else False
        self.frame: Optional[np.ndarray] = None
        self.frame_queue: queue.Queue = queue.Queue(maxsize=64)
        self.running = False
        self.eof = False
        self.camera_started = False
        self.lock = threading.Lock()
        self.thread: Optional[threading.Thread] = None
        mode_str = "FILE QUEUE (lossless, unthrottled)" if self.is_file else "LIVE STREAM"
        print(f"[VideoStreamer] Mode: {mode_str} | Output resolution: {resolution}")
        
    def _open_stream(self):
        if self.is_file:
            return av.open(self.source)
        return av.open(
            self.source,
            options={
                "rtsp_transport": "tcp",
                "fflags": "nobuffer",
                "flags": "low_delay",
                "max_delay": "0",
                "reorder_queue_size": "0",
                "stimeout": "5000000",
            }
        )
    
    def _apply_crop(self, img: np.ndarray) -> np.ndarray:
        """Crop img to self.crop_rect then resize to self.resolution."""
        cx, cy, cw, ch = self.crop_rect
        h, w = img.shape[:2]
        x1, y1 = max(0, cx), max(0, cy)
        x2, y2 = min(w, cx + cw), min(h, cy + ch)
        cropped = img[y1:y2, x1:x2]
        if cropped.size == 0:
            return cv2.resize(img, self.resolution)
        if (x2 - x1, y2 - y1) != self.resolution:
            cropped = cv2.resize(cropped, self.resolution)
        return cropped

    def _capture_loop(self):
        while self.running:
            try:
                container = self._open_stream()
                self.camera_started = True
                print("[VideoStreamer] Stream opened via PyAV")
                for packet in container.demux(video=0):
                    if not self.running:
                        break
                    if packet.size == 0:
                        print("[VideoStreamer] End of file reached.")
                        self.eof = True
                        self.running = False
                        break
                    loop_start = time.time()
                    for av_frame in packet.decode():
                        if not self.running:
                            break
                        img = av_frame.to_ndarray(format="bgr24")
                        if self.crop_rect is not None:
                            img = self._apply_crop(img)
                        else:
                            h, w = img.shape[:2]
                            if (w, h) != self.resolution:
                                img = cv2.resize(img, self.resolution)
                        if self.is_file:
                            while self.running:
                                try:
                                    self.frame_queue.put(img, timeout=0.5)
                                    break
                                except queue.Full:
                                    continue
                        else:
                            with self.lock:
                                self.frame = img
                    if self.throttle_fps:
                        elapsed = time.time() - loop_start
                        sleep_time = self.frame_time - elapsed
                        if sleep_time > 0:
                            time.sleep(sleep_time)
                container.close()
                if self.is_file:
                    self.eof = True
                    self.running = False
                    break
            except Exception as e:
                print(f"[VideoStreamer] Unexpected error: {e}")
                if self.is_file:
                    self.eof = True
                    self.running = False
                    break
                time.sleep(3)

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

    def get_frame(self) -> Optional[np.ndarray]:
        if self.is_file:
            while self.running or not self.frame_queue.empty():
                try:
                    return self.frame_queue.get(timeout=0.1)
                except queue.Empty:
                    if self.eof and self.frame_queue.empty():
                        return None
            return None
        with self.lock:
            return self.frame.copy() if self.frame is not None else None
         
    def is_ready(self) -> bool:
        if self.is_file:
            return self.camera_started and (not self.frame_queue.empty() or self.eof)
        with self.lock:
            return self.camera_started and self.frame is not None
    
    def is_eof(self) -> bool:
        """True once a file source has played to the end."""
        if self.is_file:
            return self.eof and self.frame_queue.empty()
        return self.eof
    
class RTSPBroadcaster:
    """
    Self-contained RTSP server using GStreamer's gst-rtsp-server.
    gir1.2-gst-rtsp-server-1.0) to host an RTSP endpoint directly inside
    this process. Frames are fed via an appsrc element.
    Install on Ubuntu/Debian:
        sudo apt install python3-gi gir1.2-gst-rtsp-server-1.0 \
                         gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
                         gstreamer1.0-plugins-bad gstreamer1.0-libav
    Usage:
        broadcaster = RTSPBroadcaster(port=8554, path="/traffic", width=640, height=640, fps=25)
        broadcaster.start()
        broadcaster.push_frame(bgr_frame)   # call from any thread
        broadcaster.stop()
    Connect with:
        ffplay  rtsp://127.0.0.1:8554/traffic
        vlc     rtsp://127.0.0.1:8554/traffic
        gst-launch-1.0 rtspsrc location=rtsp://127.0.0.1:8554/traffic latency=0 \\
            ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! autovideosink
    """

    def __init__(self, port: int = 8554, path: str = "/traffic", width: int = 640, height: int = 640, fps: int = 25, bitrate: int = 2000):
        self.port = port
        self.path = path
        self.width = width
        self.height = height
        self.fps = fps
        self.bitrate = bitrate
        self._appsrc = None
        self._loop = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._pts = 0
        self._frame_duration_ns = int(1e9 / fps)
        print(f"[RTSPBroadcaster] Configured → rtsp://127.0.0.1:{port}{path}  {width}×{height} @ {fps} fps")
        
    def start(self):
        """Start the GStreamer RTSP server in a background thread."""
        self._running = True
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()
        time.sleep(0.5)

    def _run_server(self):
        try:
            import gi
            gi.require_version("Gst", "1.0")
            gi.require_version("GstRtspServer", "1.0")
            from gi.repository import Gst, GstRtspServer, GLib
        except Exception as e:
            print(f"[RTSPBroadcaster] GStreamer import failed: {e}")
            return
        Gst.init(None)
        pipeline = (
            f"( appsrc name=src is-live=true block=false format=time "
            f"  caps=video/x-raw,format=BGR,width={self.width},height={self.height},"
            f"framerate={self.fps}/1 "
            f"! videoconvert ! video/x-raw,format=I420 "
            f"! x264enc tune=zerolatency bitrate={self.bitrate} speed-preset=ultrafast key-int-max={self.fps} "
            f"! rtph264pay name=pay0 pt=96 config-interval=1 )"
        )
        server = GstRtspServer.RTSPServer.new()
        server.set_service(str(self.port))
        factory = GstRtspServer.RTSPMediaFactory.new()
        factory.set_launch(pipeline)
        factory.set_shared(True)
        # Grab appsrc once the pipeline is constructed
        factory.connect("media-configure", self._on_media_configure)
        mounts = server.get_mount_points()
        mounts.add_factory(self.path, factory)
        server.attach(None)
        print(f"[RTSPBroadcaster] RTSP server listening on "f"rtsp://127.0.0.1:{self.port}{self.path}")
        self._loop = GLib.MainLoop()
        self._loop.run()

    def _on_media_configure(self, factory, media):
        """Called by GStreamer when a client connects and the pipeline starts."""
        pipeline = media.get_element()
        self._appsrc = pipeline.get_by_name("src")
        # Debug: print the actual caps being negotiated
        #print(f"[RTSPBroadcaster] appsrc caps: {self._appsrc.get_property('caps')}")
        #print("[RTSPBroadcaster] appsrc ready — streaming active")
    
    def push_frame(self, frame: np.ndarray):
        """Push one BGR frame into the RTSP stream (thread-safe)."""
        with self._lock:
            appsrc = self._appsrc
        if appsrc is None:
            return
        # Resize if needed
        h, w = frame.shape[:2]
        if (w, h) != (self.width, self.height):
            frame = cv2.resize(frame, (self.width, self.height))
        try:
            from gi.repository import Gst
            data = frame.tobytes()
            buf = Gst.Buffer.new_wrapped(data)
            buf.pts = self._pts
            buf.duration = self._frame_duration_ns
            self._pts += self._frame_duration_ns
            appsrc.emit("push-buffer", buf)
        except Exception as e:
            print(f"[RTSPBroadcaster] push_frame error: {e}")
    
    def stop(self):
        self._running = False
        if self._loop:
            self._loop.quit()
        if self._thread:
            self._thread.join(timeout=5)
        print("[RTSPBroadcaster] Stopped")

class TrafficMonitoringPipeline:
    """
    Main pipeline integrating detection, tracking, WebSocket streaming, and MQTT publishing.
    Architecture:
        VideoStreamer   – captures RTSP / local camera frames in a background thread with optional 640×640 crop (crop_rect)
        TrafficDetector – runs YOLO11 on GPU
        TrafficCounter  – IoU tracker assigns persistent IDs
        WebSocketManager– streams detection JSON to connected browser clients
        MQTTPublisher   – publishes detections to the MQTT broker
        RTSPBroadcaster  – (optional) re-streams annotated frames as an RTSP feed
        ROI zone         – (optional) rectangle that restricts which detections count
    """
    def __init__(
            self,
            model_path: str = "yolov8m.pt",
            tracker_config: str = "bytetrack.yaml",
            video_source: Any = 0,
            resolution: Tuple[int, int] = (640, 640),
            fps: int = 20,
            device: str = "auto",
            confidence_threshold: float = 0.25,
            iou_threshold: float = 0.5,
            crop_rect: Optional[Tuple[int, int, int, int]] = None,
            zone_points: Optional[List[Tuple[float, float]]] = None,
            mqtt_enabled: bool = True,
            rtsp_out_enabled: bool = False,
            recording_enabled: bool = False,
            recording_dir: str = "results",
        ):
        """
        Initialize complete pipeline.
        Args:
            model_path: Path to YOLO11 model weights
            video_source: Camera index or video file path
            db_path: SQLite database path
            resolution: Camera resolution (MUST be RPi hardware-accelerated)
            fps: Target frames per second
            device              : "auto" | "cuda" | "cpu"
            confidence_threshold: YOLO confidence threshold
            crop_rect           : (x, y, w, h) crop in raw-frame pixels; None = no crop
            roi_rect            : (x, y, w, h) detection-active rectangle in output-frame pixels; None = whole frame
            websocket_enabled   : Enable WebSocket JSON streaming
            mqtt_enabled        : Enable MQTT publishing
            rtsp_out_enabled    : Broadcast annotated frames as an RTSP stream
            recording_enabled   : Set True to record annotated frames to MP4 from session start
            recording_dir       : Directory where recording_YYYYMMDD_HHMMSS.mp4 files are saved 
        """
        # Initialize components
        self.model_name = Path(model_path).stem
        self.detector = TrafficDetector(
            model_path,
            img_size=resolution,
            device=device,
            conf_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
            tracker_config=tracker_config
        )
        self.counter = TrafficCounter()
        self.streamer = VideoStreamer(source=video_source, resolution=resolution, fps=fps, crop_rect=crop_rect)
        
        self.mqtt_enabled = mqtt_enabled
        self.mqtt = MQTTPublisher(topic="patrik/traffic_detection", client_id="PC_traffic_detection") if mqtt_enabled else None
        self.mqtt_publish_every_n_frames = 1
        self.rtsp_out_enabled = rtsp_out_enabled
        self.rtsp_broadcaster: Optional[RTSPBroadcaster] = None
        if rtsp_out_enabled:
            w, h = resolution
            self.rtsp_broadcaster = RTSPBroadcaster(port=8554, path="/traffic", width=w, height=h, fps=fps, bitrate=2000)
            print(f"[Pipeline] RTSP output enabled → rtsp://127.0.0.1:8554/traffic")
        self.recording_enabled = recording_enabled
        self.recorder = VideoRecorder(output_dir=recording_dir, fps=fps, resolution=resolution)
        if recording_enabled:
            self.recorder.start()
        else:
            print("[Pipeline] Video recording disabled (set recording_enabled=True to activate)")
        # Polygon ROI Zone (normalized coordinates, identical to Hailo pipeline)
        self.zone_points = zone_points
        self.zone_polygon: Optional[Polygon] = Polygon(zone_points) if zone_points else None
        if self.zone_polygon:
            print(f"[Pipeline] Polygon ROI enabled with {len(zone_points)} vertices: {zone_points}")
        else:
            print("[Pipeline] ROI zone disabled (whole frame)")
        
        self.running = False
        self.fps = fps
        self.resolution = resolution
        self.frame_id = 0
        self.current_frame: Optional[np.ndarray] = None
        self.current_detections: List[Detection] = []
        self.fps_actual = 0.0
        self.last_fps_update = time.time()
        self.frame_times: List[float] = []
    
    def _detection_in_roi(self, det: Detection) -> bool:
        """
        Return True if the normalized bbox centre of `det` lies inside self.zone_polygon.
        Matches Hailo pipeline logic: cx, cy in [0.0, 1.0] checked via Shapely Polygon.contains(Point(cx, cy)).
        """
        if self.zone_polygon is None:
            return True
        w, h = self.resolution
        x1, y1, x2, y2 = det.bbox
        cx = ((x1 + x2) * 0.5) / w
        cy = ((y1 + y2) * 0.5) / h
        return self.zone_polygon.contains(Point(cx, cy))
    
    def _filter_by_roi(self, detections: List[Detection]) -> List[Detection]:
        """Keep only detections whose centre falls inside the polygon ROI."""
        if self.zone_polygon is None:
            return detections
        return [d for d in detections if self._detection_in_roi(d)]

    def _publish_mqtt(self, timestamp: str, tracked_detections: List[Detection]):
        """Build the MQTT payload and publish (non-blocking – called from async context via to_thread)."""
        if not self.mqtt or not self.mqtt.connected:
            return
        counts = self.counter.get_counts()
        payload = {
            "type": "detections",
            "timestamp": timestamp,
            "frame_id": self.frame_id,
            "detections": [det.to_dict() for det in tracked_detections],
            "statistics": {
                "total_count": self.counter.get_total_count(),
                "counts_by_type": self.counter.get_counts(),
                "fps": round(self.fps_actual, 1),
            },
        }
        self.mqtt.publish(payload)

    async def process_frame(self) -> bool:
        """
        Process a single frame. Returns False when stream reaches EOF.
        Pipeline flow:
        1. Get frame from streamer (already cropped if crop_rect set)
        2. Run YOLO11 detection
        3. Filter detections by ROI rectangle
        4. Update ByteTrack counter
        5. Broadcast detection JSON via WebSocket
        6. Publish to MQTT (rate-limited)
        7. Push annotated frame to RTSP broadcaster (if enabled) 
        """
        start_time = time.time()
        #print("[Pipeline] Waiting for frame...")
        frame = await asyncio.to_thread(self.streamer.get_frame)
        if frame is None:
            if self.streamer.is_eof():
                return False
            await asyncio.sleep(0.005)
            return True
        self.current_frame = frame
        detections = await asyncio.to_thread(self.detector.detect, frame)
        detections = self._filter_by_roi(detections)
        tracked = self.counter.update(detections)
        self.current_detections = tracked
        timestamp = datetime.now().isoformat()
        if self.mqtt_enabled and (self.frame_id % self.mqtt_publish_every_n_frames == 0):
            await asyncio.to_thread(self._publish_mqtt, timestamp, tracked)
        if self.frame_id % 30 == 0 and tracked:
            print(f"[Frame {self.frame_id}] Detected objects in ROI: {[d.to_dict() for d in tracked]}")
        if self.rtsp_out_enabled and self.rtsp_broadcaster:
            annotated = self.get_annotated_frame()
            if annotated is not None:
                await asyncio.to_thread(self.rtsp_broadcaster.push_frame, annotated)
        if self.recording_enabled and self.recorder.is_recording:
            annotated = self.get_annotated_frame()
            if annotated is not None:
                await asyncio.to_thread(self.recorder.write, annotated)
            self.recorder.feed_detections(tracked)
        # Update metrics (id, time, FPS)
        self.frame_id += 1
        elapsed = time.time() - start_time
        self.frame_times.append(elapsed)
        # Calculate FPS every second
        if time.time() - self.last_fps_update > 1.0:
            if self.frame_times:
                avg_time = sum(self.frame_times) / len(self.frame_times)
                self.fps_actual = 1.0 / avg_time if avg_time > 0 else 0
                self.frame_times = []
            self.last_fps_update = time.time()
            print(f"[Pipeline] Frame {self.frame_id:5d} | FPS: {self.fps_actual:.1f} | Total objects: {self.counter.get_total_count()}")
        return True
    
    async def start(self):
        """Start the processing pipeline (runs until stopped)."""
        print("[Pipeline] Starting traffic monitoring...")
        self.streamer.start()
        if self.rtsp_out_enabled and self.rtsp_broadcaster:
            self.rtsp_broadcaster.start()
        print("[Pipeline] Waiting for camera/stream to initialise...")
        max_wait, waited = 10.0, 0.0
        while not self.streamer.is_ready() and waited < max_wait:
            await asyncio.sleep(0.2)
            waited += 0.2
        if not self.streamer.is_ready():
            print("[Pipeline] ERROR: Camera/stream failed to initialise!")
            self.stop()
            return
        print("[Pipeline] Stream ready, starting detection...")
        self.running = True
        try:
            while self.running:
                keep_going = await self.process_frame()
                if not keep_going:
                    break
        except Exception as e:
            print(f"[Pipeline] Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop()

    def stop(self):
        """Stop pipeline and cleanup resources."""
        print("[Pipeline] Stopping...")
        self.running = False
        self.streamer.stop()
        if self.rtsp_out_enabled and self.rtsp_broadcaster:
            self.rtsp_broadcaster.stop()
        if self.recording_enabled:
            self.recorder.stop()
        if self.mqtt:
            self.mqtt.disconnect()
        print("[Pipeline] Stopped")
    
    def get_annotated_frame(self) -> Optional[np.ndarray]:
        """Return current frame with bounding boxes, Shapely polygon ROI, and stats overlay."""
        if self.current_frame is None:
            return None
        annotated = self.detector.draw_detections(self.current_frame, self.current_detections, show_tracking=True)
        # Draw translucent green polygon ROI (matching Hailo Cairo overlay)
        if self.zone_points is not None:
            w, h = self.resolution
            pts = np.array(
                [[int(x * w), int(y * h)] for x, y in self.zone_points],
                dtype=np.int32
            ).reshape((-1, 1, 2))
            overlay = annotated.copy()
            cv2.fillPoly(overlay, [pts], (0, 255, 0))
            cv2.addWeighted(overlay, 0.15, annotated, 0.85, 0, annotated)
            cv2.polylines(annotated, [pts], isClosed=True, color=(0, 255, 0), thickness=2)
          
        counts = self.counter.get_counts()
        y_offset = 30
        cv2.putText(annotated, f"ByteTrack - {self.model_name}", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        y_offset += 25
        cv2.putText(annotated, f"Total: {self.counter.get_total_count()}", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        y_offset += 25
        for label, count in counts.items():
            cv2.putText(annotated, f"{label}: {count}", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            y_offset += 25
        cv2.putText(annotated, f"FPS: {self.fps_actual:.1f}", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        return annotated

# bytetrack config
def create_bytetrack_config(
        output_path: str = "bytetrack.yaml",
        track_high_thresh: float = 0.6,
        track_low_thresh: float = 0.1,
        new_track_thresh: float = 0.6,
        track_buffer: int = 50,
        match_thresh: float = 0.8,
        fuse_score: bool = True
    ) -> str:
    """
    Write a custom bytetrack.yaml so you can tune without editing
    Ultralytics internals. Returns the output path for convenience.
    Parameters explained:
        track_high_thresh  — detections above this confidence are matched in the first (primary) association pass. Raise this if you have many false positives.
        track_low_thresh   — detections between low and high thresh are used in the second pass to recover lost tracks. Lower this to recover more detections at cost of noise.
        new_track_thresh   — a brand-new track is only created if detection confidence exceeds this. Raise to kill ghost tracks.
        track_buffer       — frames a lost track is kept alive before deletion. Increase for slow-moving or temporarily occluded vehicles.
        match_thresh       — IoU distance threshold for Kalman-predicted bbox matching. Lower = stricter spatial matching.
    """
    config = (
        "# ByteTrack configuration\n"
        "# Aligned with Hailo-8 hailotracker parameters\n\n"
        "tracker_type: bytetrack\n\n"
        f"track_high_thresh: {track_high_thresh}\n"
        f"track_low_thresh: {track_low_thresh}\n"
        f"new_track_thresh: {new_track_thresh}\n"
        f"track_buffer: {track_buffer}\n"
        f"match_thresh: {match_thresh}\n"
        f"fuse_score: {fuse_score}\n"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(config)
    print(f"[Config] ByteTrack config saved -> {output_path}")
    return output_path

async def main():
    print("=== YOLOv8m GPU Traffic Detection Benchmark ===")
    print("Press 'q' to exit")
    print()
    # Configuration for local testing (adjust resolution for your camera)
    # RTSP_URL = get_camera_rtsp_url()  # IP camera; set CAMERA_RTSP_URL in .env
    # VIDEO_SOURCE = 0                      # webcam
    # VIDEO_SOURCE = get_camera_rtsp_url()  # IP camera stream; set CAMERA_RTSP_URL in .env
    # Load video source from .env (fallback to local default path)
    VIDEO_SOURCE = os.getenv(
        "VIDEO_SOURCE",
        "/videos/sample_video.mp4"
    )
    MODEL_PATH = "yolov8m.pt"
    RECORDING_DIR = "results"
    # Crop 640x640 from 1280x720 (top=80, left=200, right=440, bottom=0 — identical to Hailo videocrop)
    CROP_RECT: Optional[Tuple[int, int, int, int]] = (200, 80, 640, 640) # (x,y,w,h) | None
    RESOLUTION = (640, 640)
    # Identical Polygon ROI zone as in DetectionWithGStreamer_pipeline.py
    ZONE_POINTS: List[Tuple[float, float]] = [
        (0.1, 0.85),
        (0.46, 0.85),
        (0.6, 0.9),
        (0.45, 0.9),
        (0.4, 1.0)
    ]
    # Bytetrack
    TRACKER_CONFIG = create_bytetrack_config(
        output_path="bytetrack.yaml",
        track_high_thresh=0.6,   # lower if losing detections on real camera
        track_low_thresh=0.1,    # lower to recover more occluded vehicles
        new_track_thresh=0.6,    # raise if getting ghost/duplicate tracks
        track_buffer=50,          # raise for slow traffic or long occlusions
        match_thresh=0.7,         # lower slightly if IDs keep switching
        fuse_score=True           # multiply confidence into matching distance
    )
    # Create pipeline instance
    pipeline = TrafficMonitoringPipeline(
        model_path=MODEL_PATH,
        tracker_config=TRACKER_CONFIG,
        video_source=VIDEO_SOURCE,
        resolution=RESOLUTION,
        fps=20,
        device="auto",
        confidence_threshold=0.25,
        iou_threshold=0.5,
        crop_rect=CROP_RECT,
        zone_points=ZONE_POINTS,
        mqtt_enabled=False,
        rtsp_out_enabled=False,
        recording_enabled=True,
        recording_dir=RECORDING_DIR,
    )
    await pipeline.start()
    print("\n=== FINAL STATISTICS ===")
    print(f"Total objects detected: {pipeline.counter.get_total_count()}")
    print(f"Count by type: {pipeline.counter.get_counts()}")
    print(f"Total frames processed: {pipeline.frame_id}")

if __name__ == "__main__": 
    asyncio.run(main())