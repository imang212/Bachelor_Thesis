\connect hailo_db;

ALTER TABLE public.detections
    ADD COLUMN IF NOT EXISTS model_name TEXT NOT NULL DEFAULT 'yolov8m',
    ADD COLUMN IF NOT EXISTS device_type TEXT NOT NULL DEFAULT 'hailo8';

CREATE INDEX IF NOT EXISTS idx_det_model ON public.detections(model_name);
CREATE INDEX IF NOT EXISTS idx_det_device ON public.detections(device_type);
CREATE INDEX IF NOT EXISTS idx_det_model_time ON public.detections(model_name, timestamp_ DESC);
CREATE INDEX IF NOT EXISTS idx_det_device_time ON public.detections(device_type, timestamp_ DESC);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO hailo_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO hailo_user;