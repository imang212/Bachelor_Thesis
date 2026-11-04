import json
import subprocess

# Čistě černobílá / šedivá akademická konfigurace s jemnými boxy pro vrstvy (namespaces)
mermaid_config = {
  "theme": "base",
  "fontFamily": "DejaVu Sans, Arial, sans-serif",
  "themeVariables": {
    "fontSize": "22px",
    "fontFamily": "DejaVu Sans, Arial, sans-serif",
    "primaryColor": "#ffffff",        # Bílé pozadí tříd
    "primaryBorderColor": "#333333",  # Tmavě šedý obrys tříd
    "primaryTextColor": "#111111",    # Černý text
    "lineColor": "#333333",           # Tmavé propojovací čáry
    "clusterBkg": "#fcfcfc",
    "clusterBorder": "#666666"
  },
  "class": {
    "padding": 12,
    "hideEmptyMembersBox": True
  },
  "flowchart": {
    "wrappingWidth": 800,
    "nodeSpacing": 20,
    "rankSpacing": 90,
    "padding": 15,
    "htmlLabels": False
  },
  "htmlLabels": False,
  "fontSize": 22
}

mermaid_class = '''classDiagram
direction TB

    namespace Edge {
        class HailoTrackerPipeline {
            -pipeline : Gst.Pipeline
            -loop : GLib.MainLoop
            -video_file : str
            -rtsp_link : str
            -model_name : str
            -zone_polygon : Polygon
            -sent_track_ids : set
            +create_pipeline()
            +start()
            +stop()
            +buffer_probe_callback(pad, info)
            +on_new_sample_rtsp(appsink)
        }

        class DetectionData {
            -detections : list
            -frame_count : int
            -object_counts : dict
            -counted_track_ids : set
            -lock : Lock
            +update(detections, frame_count)
            +get_dict() dict
            +get_count_overlay_text() str
        }

        class VideoStatistics {
            -detections_per_class : dict
            -unique_track_ids : set
            -total_frames : int
            +add_detection(class_name, conf, track_id)
            +add_frame(has_detections)
            +get_summary() dict
        }

        class RTSPServer {
            -port : int
            -mount_point : str
            -appsrc : Gst.Element
            +create_server()
            +start()
            +push_buffer(buffer)
        }

        class MQTTPublisher {
            -broker_host : str
            -broker_port : int
            -topic : str
            -client : mqtt.Client
            -connected : bool
            +connect(userdata)
            +disconnect()
            +publish(data_dict)
            +on_message(client, userdata, msg)
        }
    }

    namespace Backend {
        class PostgreDatabaseManager {
            -db_config : dict
            -pool : ThreadedConnectionPool
            -inserted_track_ids : set
            +insert_batch_detections(detections)
            +get_recent_detections(minutes, limit)
            +get_counts_detections(minutes, per)
            +get_statistics(hours)
            +get_health_status()
            +close()
            -_process_mqtt_message(msg)
            -_default_message_parser(topic, payload)
        }

        class FastAPIApp {
            <<module>>
            -db : PostgreDatabaseManager
            -pipeline : HailoTrackerPipeline
            -pipeline_thread : Thread
            -mqtt_client : MQTTPublisher
            +startup()
            +shutdown()
            +pipeline_start(config)
            +pipeline_stop()
            +pipeline_status()
            +database_start(config)
            +database_stop()
            +get_detections()
            +get_detection_counts()
            +get_statistics()
        }
    }

    namespace Frontend {
        class StreamlitDashboard {
            <<module>>
            +fetch_detections()
            +fetch_statistics()
            +fetch_pipeline_status()
            +start_pipeline(config)
            +stop_pipeline()
            +start_database(mqtt)
            +stop_database()
        }
    }

class GStreamerHailo {
    <<external>>
    hailonet
    hailofilter
    hailotracker
}
class MQTTBroker {
    <<external>>
    topic videoanalyza
}
class PostgreSQL {
    <<external>>
    table detections
}

HailoTrackerPipeline *-- DetectionData
HailoTrackerPipeline *-- "0..1" VideoStatistics : video mode
HailoTrackerPipeline *-- "0..1" RTSPServer : enable_rtsp
HailoTrackerPipeline *-- "0..1" MQTTPublisher : enable_mqtt
HailoTrackerPipeline ..> GStreamerHailo : parse_launch

MQTTPublisher ..> MQTTBroker : publish and subscribe
MQTTPublisher ..> PostgreDatabaseManager : forwards messages
PostgreDatabaseManager ..> PostgreSQL : psycopg2 pool

StreamlitDashboard ..> FastAPIApp : HTTP REST
FastAPIApp --> HailoTrackerPipeline : creates and runs in thread
FastAPIApp --> PostgreDatabaseManager : owns
FastAPIApp --> MQTTPublisher : owns as DB listener

%% Černobílý/šedivý styl externích prvků
style GStreamerHailo fill:#f2f2f2,stroke:#666666,stroke-width:1.5px,stroke-dasharray:4 4
style MQTTBroker fill:#f2f2f2,stroke:#666666,stroke-width:1.5px,stroke-dasharray:4 4
style PostgreSQL fill:#f2f2f2,stroke:#666666,stroke-width:1.5px,stroke-dasharray:4 4
'''

with open('mmd_config.json', 'w', encoding='utf-8') as f:
    json.dump(mermaid_config, f, indent=2)

with open('class_diagram.mmd', 'w', encoding='utf-8') as f:
    f.write(mermaid_class)

subprocess.run([
    'mmdc',
    '-i', 'class_diagram.mmd',
    '-o', 'class_diagram.pdf',
    '-c', 'mmd_config.json',
    '-b', 'white',
    '-w', '1600',
    '-H', '2400',
    '--pdfFit',
], check=True)

print("Layered monochrome class diagram created successfully!")