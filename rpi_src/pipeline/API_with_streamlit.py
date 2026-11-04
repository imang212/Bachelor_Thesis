"""
Combined FastAPI Backend + Service Launcher.
Streamlit UI is modularized in streamlit_dashboard.py.
Run both services with:
    python3 rpi_src/pipeline/API_with_streamlit.py
Or run FastAPI standalone with:
    uvicorn rpi_src.pipeline.API_with_streamlit:app --host 0.0.0.0 --port 8000
"""
import sys
import time
import asyncio
import threading
import subprocess
import multiprocessing
from time import sleep
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure both project root and current pipeline directory are in sys.path
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parents[1]
for p in (str(PROJECT_ROOT), str(CURRENT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from common.config import get_db_config, get_mqtt_config
from common.DatabaseManagerPostgre import PostgreDatabaseManager
from common.MQTTClient import MQTTPublisher
try:
    from rpi_src.pipeline.DetectionWithGStreamer_pipeline import HailoTrackerPipeline
    PIPELINE_AVAILABLE = True
except ImportError:
    try:
        from DetectionWithGStreamer_pipeline import HailoTrackerPipeline
        PIPELINE_AVAILABLE = True
    except ImportError:
        HailoTrackerPipeline = Any
        PIPELINE_AVAILABLE = False
        print("[WARNING] Pipeline module not found")
try:
    from rpi_src.pipeline.streamlit_dashboard import run_streamlit
except ImportError:
    from streamlit_dashboard import run_streamlit

DB_CONFIG = get_db_config()
MQTT_CONFIG = get_mqtt_config()

## MODELS
class CameraSettings(BaseModel): # Camera settings for capture
    width: int = Field(1536, ge=1536, le=4608)
    height: int = Field(864, ge=864, le=2592)
class PipelineConfig(BaseModel): # Pipeline configuration model
    """Configuration for starting AI pipeline"""
    rpicamera: bool = Field(False, description="Use Raspberry Pi camera")
    video_file: Optional[str] = Field(None, description="Path to video file")
    enable_rtsp: bool = Field(False, description="Enable RTSP streaming")
    enable_mqtt: bool = Field(True, description="Enable MQTT")
    enable_recording: bool = Field(False, description="Enable video recording")
    output_path: Optional[str] = Field(None, description="Output video path")
    enable_debug: bool = Field(False, description="Enable debug mode")
class PipelineStatus(BaseModel): # Pipeline status response model
    """Pipeline status response"""
    running: bool
    mode: Optional[str]
    fps: Optional[float]
    total_tracked: Optional[int]
class DetectionResponse(BaseModel): # Detection response model
    """Response model for detection data via REST API."""
    id: int
    timestamp: datetime
    frame_id: int
    class_name: str
    confidence: float
    bbox: List[float]  # [x1, y1, x2, y2]
    track_id: Optional[int]
class StatisticsResponse(BaseModel): # Statistics response model
    """Response model for traffic statistics."""
    class_name: str
    total_detections: int
    unique_tracks: int
    avg_confidence: float
    min_confidence: float
    max_confidence: float
class HealthResponseDB(BaseModel): # Health check response model for database
    """Health check response."""
    status: str
    total_detections: int
    latest_detection: Optional[str]
    database_size: str
    mqtt_sending: bool
class DatabaseConfig(BaseModel): # Database configuration
    mqtt_sending: bool = Field(False, description="Enable MQTT sending")

# Global instances
db: Optional[PostgreDatabaseManager] = None
pipeline: Optional[Any] = None
pipeline_thread: Optional[threading.Thread] = None
pipeline_config: Optional[Dict[str, Any]] = None
pipeline_running: bool = False
mqtt_client: Optional[MQTTPublisher] = None
mqtt_client_sending: bool = False

# Initialize FastAPI
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],)

@app.on_event("startup")
async def startup():
    global db
    print("[FastAPI] Starting up...")
    try:
        # Create database manager instance
        db = PostgreDatabaseManager(DB_CONFIG)
        print("[FastAPI] Database connected successfully")
    except Exception as e:
        print(f"[FastAPI] Database connection failed: {e}")
        db = None
    
@app.on_event("shutdown")
async def shutdown():
    global db, mqtt_client, mqtt_client_sending
    print("[FastAPI] Shutting down...")
    if db:
        db.close()
        if mqtt_client_sending and mqtt_client:
            mqtt_client.disconnect()
            mqtt_client = None
            mqtt_client_sending = False

## CONFIGURATION FOR CAPTURE STORAGE
CAPTURE_DIR = Path("captures")
CAPTURE_DIR.mkdir(exist_ok=True)

## HELPER FUNCTIONS
def check_pipeline_instance():
    """Check if pipeline instance exists and is properly initialized"""
    global pipeline_running
    if pipeline_running is False:
        return False, "Pipeline not initialized"
    return True, "Pipeline instance available"

def check_db_instance():
    """Check if database instance exists and is connected"""
    global db
    if db is None:
        return False, "Database not initialized"
    try:
        if db.verify_pool():
            return True, "Database connected"
        else:
            return False, "Database connection pool verification failed"
    except Exception as e:
        return False, f"Database error: {str(e)}"

## DATABASE MANAGEMENT ENDPOINTS
@app.get("/database/status")
async def database_status():
    """Check database connection status"""
    global db, mqtt_client, mqtt_client_sending
    is_connected, _ = check_db_instance()
    if is_connected:
        try:
            health = db.get_health_status()
            if mqtt_client_sending is True:
                health['mqtt_sending'] = mqtt_client_sending
            return health
        except Exception as e:
            return {"connected": False, "status": "error", "message": f"Health check failed: {str(e)}", "mqtt_sending": mqtt_client_sending}
    return {"connected": False, "status": "disconnected", "message": "Database not connected", "mqtt_sending": mqtt_client_sending}

@app.post("/database/start")
async def database_start(data: DatabaseConfig):
    """Start/initialize database connection"""
    global db, mqtt_client, mqtt_client_sending
    if db is not None:
        is_connected, _ = check_db_instance()
        if is_connected:
            return {"status": "already_running", "message": "Database and MQTT client are already connected", "mqtt": mqtt_client_sending}
    try:
        db = PostgreDatabaseManager(DB_CONFIG) # create new db instance
        if data.mqtt_sending is True:
            mqtt_client = MQTTPublisher(MQTT_CONFIG) # create new mqtt client instance
            mqtt_client.client.user_data_set({"db": db})
            mqtt_client.client.on_message = mqtt_client.on_message
            mqtt_client.connect({"db": db})
            await asyncio.sleep(2)  # Wait for connection
            mqtt_client_sending = True
            print("[FastAPI] MQTT client connected for sending")
        return {"status": "started", "message": "Database connection established successfully", "mqtt": mqtt_client_sending}
    except Exception as e:
        db = None
        if mqtt_client_sending and mqtt_client:
            mqtt_client.disconnect()
            mqtt_client = None
            mqtt_client_sending = False
        raise HTTPException(status_code=500, detail=f"Failed to start database connection: {str(e)}")

@app.post("/database/stop")
async def database_stop():
    """Stop/close database connection"""
    global db, mqtt_client, mqtt_client_sending
    if db is None:
        return {"status": "already_stopped", "message": "Database is not running"}
    try:
        db.close()
        if mqtt_client_sending and mqtt_client:
            mqtt_client.disconnect()
        db = None
        mqtt_client = None
        mqtt_client_sending = False
        return {"status": "stopped", "message": "Database connection closed successfully", "mqtt": mqtt_client_sending}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop database: {str(e)}")

## DATABASE QUERIES ENDPOINTS
# STATISTICS FROM DB ENDPOINT
@app.get("/api/detections", response_model=List[DetectionResponse])
async def get_detections(minutes: int = 5, limit: int = 100):
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    try:
        detections = db.get_recent_detections(minutes=minutes, limit=limit)
        #print(f"[FastAPI] Retrieved {len(detections)} detections from DB")
        #print(detections[0:5])  # Print first 5 detections for debugging
        #print(detections[0:1].keys(), detections[0:1].items())  # Print keys of the first detection
        result = []
        for d in detections:
            try:
                d_dict = dict(d)  # make sure it's a dict
                result.append(
                    DetectionResponse(
                        id=d_dict['id'],
                        timestamp=d_dict['timestamp_'],  # or d_dict['timestamp_'].isoformat()
                        frame_id=d_dict['frame_id'],
                        class_name=d_dict['class_name'],
                        confidence=d_dict['confidence'],
                        bbox=[d_dict['x1'], d_dict['y1'], d_dict['x2'], d_dict['y2']],
                        track_id=d_dict['track_id']
                    )
                )
            except Exception as inner_e:
                print(f"[FastAPI] Error converting detection: {inner_e}, data: {d}")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching detections: {str(e)}")

@app.get("/api/detection_counts", response_model=List[Any])
async def get_detection_counts(minutes: int = 5, per: str = "10 minutes"):
    """Get recent aggregated detection counts from database."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    try:
        detections = db.get_counts_detections(minutes=minutes, per=per)
        #print(f"[FastAPI] Retrieved {len(detections)} detections from DB")
        #print(detections[0:5])  # Print first 5 detections for debugging
        #print(detections[0:1].keys(), detections[0:1].items())  # Print keys of the first detection
        result = []
        for d in detections:
            try:
                d_dict = dict(d)  # make sure it's a dict
                result.append((d_dict['time_bucket'], d_dict['detection_count']))
            except Exception as inner_e:
                print(f"[FastAPI] Error converting detection: {inner_e}, data: {d}")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching detections: {str(e)}")

@app.get("/api/statistics", response_model=Dict[str, StatisticsResponse])
async def get_statistics(hours: int = 1):
    """Get aggregated traffic statistics. Returns count and average confidence for each object type within the specified time window."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    try:
        stats = db.get_statistics(hours=hours)
        return {
            class_name: StatisticsResponse(
                class_name=class_name,
                total_detections=data['total_detections'],
                unique_tracks=data['unique_tracks'],
                avg_confidence=data['avg_confidence'],
                min_confidence=data['min_confidence'],
                max_confidence=data['max_confidence']
            )
            for class_name, data in stats.items()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching statistics: {str(e)}")

## AI PIPELINE DETECTION ENDPOINTS
@app.get("/pipeline/status", response_model=PipelineStatus)
async def pipeline_status():
    """Get current pipeline status"""
    global pipeline, pipeline_config, pipeline_running
    if not PIPELINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Pipeline module not available")
    if pipeline is None:
        return PipelineStatus(running=False, mode=None, fps=None, total_tracked=None, config=None)
    try:
        mode = "unknown"
        if pipeline_config:
            if pipeline_config.get('video_file'):
                mode = "video_file"
            elif pipeline_config.get('rpicamera'):
                mode = "rpicamera"
            else:
                mode = "rtsp_stream"
        print(f"[FastAPI] Pipeline status requested. Running: {pipeline_running}, Mode: {mode}, FPS: {getattr(pipeline, 'frame_count', 0.0)}, Total Tracked: {getattr(pipeline.detection_data, 'get_count_overlay_text', lambda: 0)() if hasattr(pipeline, 'detection_data') else 0}")
        return PipelineStatus(
            running=pipeline_running,
            mode=mode,
            fps=pipeline.frame_count if hasattr(pipeline, 'frame_count') else 0.0,
            total_tracked=getattr(pipeline.detection_data, 'get_count_overlay_text', lambda: 0)() if hasattr(pipeline, 'detection_data') else 0,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting pipeline status: {str(e)}")

@app.post("/pipeline/start")
async def pipeline_start(config: PipelineConfig):
    """Start AI detection pipeline with specified configuration"""
    global pipeline, pipeline_thread, pipeline_config, pipeline_running
    if not PIPELINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Pipeline module not available")
    if pipeline_running:
        raise HTTPException(status_code=409, detail="Pipeline is already running. Stop it first.")
    if db is None: # Check database connection
        raise HTTPException(status_code=503, detail="Database not connected. Start database first.")
    try:
        output_path = config.output_path # Generate output path if recording enabled
        if config.enable_recording and not output_path and not config.video_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"hailo_output_{timestamp}.mp4"
        # Store configuration
        pipeline_config = config.dict()
        pipeline_config['output_path'] = output_path
        # Create pipeline instance
        pipeline = HailoTrackerPipeline(
            rpicamera=config.rpicamera,
            enable_rtsp=config.enable_rtsp,
            enable_mqtt=config.enable_mqtt,
            enable_recording=config.enable_recording,
            enable_debug=config.enable_debug,
        )
        # Create and start pipeline
        pipeline.create_pipeline()
        # Start in separate thread
        def run_pipeline():
            try:
                pipeline.start()
            except Exception as e:
                print(f"[Pipeline Thread] Error: {e}")
        pipeline_thread = threading.Thread(target=run_pipeline, daemon=True)
        pipeline_thread.start()
        pipeline_running = True
        await asyncio.sleep(1) # Wait a moment to ensure it starts
        return {"status": "started", "message": "Pipeline started successfully", "config": pipeline_config, "running": pipeline_running}
    except Exception as e:
        pipeline = None
        pipeline_config = None
        raise HTTPException(status_code=500, detail=f"Failed to start pipeline: {str(e)}")

@app.post("/pipeline/stop")
async def pipeline_stop():
    """Stop AI detection pipeline"""
    global pipeline, pipeline_config, pipeline_running
    if pipeline is None:
        return {"status": "already_stopped", "message": "Pipeline is not running"}
    try:
        # Stop the pipeline
        if hasattr(pipeline, 'stop') and pipeline_running is True:
            pipeline.stop()
        # Clear references
        pipeline = None
        pipeline_config = None
        pipeline_running = False
        return {"status": "stopped", "message": "Pipeline stopped successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop pipeline: {str(e)}")

@app.get("/pipeline/modes")
async def pipeline_modes():
    """Get available pipeline modes and their descriptions"""
    return {
        "modes": {
            "rpicamera": {
                "description": "Use Raspberry Pi Camera (IMX708)",
                "config": {"rpicamera": True}
            },
            "rtsp_stream": {
                "description": "Use RTSP IP Camera Stream",
                "config": {"rpicamera": False, "video_file": None}
            },
            "video_file": {
                "description": "Analyze video file",
                "config": {"video_file": "/path/to/video.mp4"}
            }
        },
        "features": {
            "enable_rtsp": "Enable RTSP streaming output",
            "enable_mqtt": "Enable MQTT message publishing",
            "enable_recording": "Record processed video output",
            "enable_debug": "Enable debug logging"
        }
    }

@app.get("/api/current/ai")
async def get_current_state():
    """Get current real-time state from running pipeline"""
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not running")
    try:
        pipeline_detections = []
        if hasattr(pipeline, 'detection_data'):
            pipeline_detections = pipeline.detection_data.get_dict()
        return pipeline_detections if pipeline_detections else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting current state: {str(e)}")

## CAMERA ENDPOINTS
# CAMERA CAPTURE (PHOTO)
@app.post("/camera/stream/capture")
async def camera_capture(settings: Optional[CameraSettings] = None):
    """Capture a single photo from the camera"""
    if settings is None:
        settings = CameraSettings()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = CAPTURE_DIR / f"capture_{timestamp}.jpg"
    try:
        result = subprocess.run([
            "rpicam-still",
            "-n",
            "--width", str(settings.width),
            "--height", str(settings.height),
            "-o", str(output)
        ], capture_output=True, timeout=10)
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Camera capture failed: {result.stderr.decode()}")
        if not output.exists():
            raise HTTPException(status_code=500, detail="Output file not created")
        return FileResponse(output, media_type="image/jpeg", filename=output.name)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Camera capture timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# CAMERA STREAM (SNAPSHOT STREAM)
@app.get("/camera/stream/snapshots")
def stream_snapshots(width: int = 1536, height: int = 864, framerate: int = 30):
    """Stream individual JPEG frames via MJPEG."""
    def generate_snapshots():
        frame_delay = 1.0 / framerate
        try:
            while True:
                # Zachytíme jeden frame
                temp_img = "/tmp/stream_frame.jpg"
                result = subprocess.run([
                    "rpicam-still",
                    "-n",
                    "--width", str(width),
                    "--height", str(height),
                    "-o", temp_img,
                    "-t", "1"  # Rychlé zachycení
                ], capture_output=True, timeout=2)
                if result.returncode != 0:
                    sleep(frame_delay)
                    continue
                with open(temp_img, 'rb') as f: # načteme obrázek
                    frame_bytes = f.read()
                # Pošleme jako MJPEG frame
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' +
                       frame_bytes + b'\r\n')
                sleep(frame_delay)
        except Exception as e:
            print(f"Stream error: {e}")
    return StreamingResponse(generate_snapshots(), media_type="multipart/x-mixed-replace; boundary=frame")

#CAMERA VIEWER (IN HTML)
@app.get("/camera/stream/hls")
async def camera_viewer():
    """Simple HTML page for viewing the camera stream."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Raspberry Pi Camera Stream</title>
        <style> body { font-family: Arial, sans-serif; max-width: 1200px; margin: 50px auto; padding: 20px; background: #1a1a1a; color: white;} .stream-container { margin: 20px 0; border: 2px solid #333; border-radius: 8px; overflow: hidden;} img { width: 100%; height: auto; display: block; } h2 { color: #4CAF50; } .info { background: #333; padding: 15px; border-radius: 5px; margin: 10px 0; } button { background: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin: 5px;} button:hover { background: #45a049; }</style>
    </head>
    <body>
        <h1>Raspberry Pi Camera Stream</h1>
        <div class="stream-container">
            <img id="stream" src="/camera/stream/snapshots" alt="Camera Stream">
        </div>
    </body>
    </html>
    """
    return Response(content=html_content, media_type="text/html")

# UTILITY ENDPOINTS FOR CAPTURES STORAGE MANAGEMENT
@app.get("/captures")
async def list_captures():
    """List all captured images"""
    captures = sorted(CAPTURE_DIR.glob("*.jpg"), reverse=True)
    return {
        "total": len(captures),
        "captures": [f.name for f in captures[:20]]  # Last 20
    }

@app.delete("/captures/{filename}")
async def delete_capture(filename: str):
    """Delete a specific capture"""
    filepath = CAPTURE_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    filepath.unlink()
    return {"status": "deleted", "filename": filename}

# HEALTH CHECK ENDPOINT
@app.get("/health/camera")
async def health_check():
    """Check if camera is accessible"""
    try:
        result = subprocess.run(["rpicam-hello", "--list-cameras"], capture_output=True, timeout=5)
        return { "status": "healthy", "camera_available": result.returncode == 0}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e) }
    
# ROOT ENDPOINT
@app.get("/")
def root():
    """API root with endpoint documentation"""
    return {
        "message": "Raspberry Pi Traffic Monitoring API",
        "version": "2.0.0",
        "endpoints": {
            "database": {
                "status": "GET /database/status",
                "start": "POST /database/start",
                "stop": "POST /database/stop",
            },
            "pipeline": {
                "status": "GET /pipeline/status",
                "start": "POST /pipeline/start",
                "stop": "POST /pipeline/stop",
                "modes": "GET /pipeline/modes",
                "current_state": "GET /api/current/ai",
            },
            "ai_detection": {
                "detections": "GET /api/detections?minutes=5&limit=100",
                "statistics": "GET /api/statistics?hours=1",
            },
            "camera": {
                "capture": "POST /camera/stream/capture",
                "stream": "GET /camera/stream/snapshots",
                "viewer": "GET /camera/stream/hls",
                "list_captures": "GET /captures",
                "delete_capture": "DELETE /captures/{filename}",
                "health": "GET /health/camera",
            },
        }
    }

# MAIN LAUNCHER
def run_fastapi():
    """Run FastAPI with uvicorn."""
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "rpi_src.pipeline.API_with_streamlit:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--lifespan", "on",
        "--log-level", "info",
    ], cwd=str(PROJECT_ROOT))

    
def run_streamlit_process():
    """Run Streamlit dashboard module in a subprocess."""
    dashboard_script = CURRENT_DIR / "streamlit_dashboard.py"
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(dashboard_script),
        "--server.port=8501",
        "--server.address=0.0.0.0",
    ], cwd=str(PROJECT_ROOT))

def main():
    """Main launcher - starts both FastAPI and Streamlit."""
    print("Services:")
    print("  - FastAPI:   http://localhost:8000")
    print("  - API Docs:  http://localhost:8000/docs")
    print("  - Streamlit: http://localhost:8501")
    print()
    multiprocessing.set_start_method("spawn", force=True) # Start FastAPI in separate process
    fastapi_process = multiprocessing.Process(target=run_fastapi, daemon=False)
    fastapi_process.start()
    time.sleep(5) # Give FastAPI time to start
    try:
        run_streamlit_process() # Start Streamlit in main process (so we can see output)
    except KeyboardInterrupt:
        print("\nShutting down...")
        fastapi_process.terminate()
        fastapi_process.join()

if __name__ == "__main__":
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx() is not None:
            run_streamlit()
        else:
            main()
    except ImportError:
        main()