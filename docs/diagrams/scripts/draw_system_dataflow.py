import json
import subprocess

FLOW = '''flowchart TB
    Cam["IP kamera<br>(RTSP)"]

    subgraph Edge["Edge vrstva (Raspberry Pi 5 + Hailo-8)"]
        P["HailoTrackerPipeline<br>GStreamer + Hailo"]
        D["DetectionData"]
        S["VideoStatistics"]
        R["RTSPServer"]
        M2["MQTTPublisher"]
    end

    subgraph Comm["Komunikační vrstva"]
        MB["MQTT Broker<br>(topic videoanalyza)"]
    end

    subgraph Backend["Backend (serverová vrstva)"]
        L["MQTTPublisher listener<br>DatabaseManagerPostgre.py"]
        DBM["PostgreDatabaseManager"]
        PG["PostgreSQL<br>(table detections)"]
        API["FastAPIApp"]
    end

    subgraph Frontend["Prezentační vrstva"]
        UI["StreamlitDashboard"]
    end

    Cam -- "RTSP stream" --> P
    P --> D
    P --> S
    P --> R
    P --> M2
    M2 -- "publish (JSON)" --> MB
    MB -- "on_message" --> L
    L --> DBM
    DBM -- "psycopg2 pool" --> PG
    API -- "query" --> PG
    UI -- "HTTP REST" --> API
'''

# Black-and-white academic style (matches the ERD)
NODES = ['Cam', 'P', 'D', 'S', 'R', 'M2', 'MB', 'L', 'DBM', 'PG', 'API', 'UI']
bw_styles = ''.join(f'    style {k} fill:#ffffff,stroke:#000000,stroke-width:1.5px,color:#000000\n' for k in NODES)
bw_sub = ''.join(f'    style {k} fill:#f0f0f0,stroke:#000000,stroke-width:1.5px,color:#000000\n'
                 for k in ['Edge', 'Comm', 'Backend', 'Frontend'])
 
def config():
    return {
        "theme": "base",
        "fontFamily": "Liberation Serif, Times New Roman, serif",
        "fontSize": 20,
        "themeVariables": {
            "fontSize": "20px",
            "fontFamily": "Liberation Serif, Times New Roman, serif",
            "primaryTextColor": "#000000",
            "textColor": "#000000",
            "titleColor": "#000000",
            "lineColor": "#000000",
            "edgeLabelBackground": "#ffffff",
            "clusterBkg": "#f0f0f0",
            "clusterBorder": "#000000",
        },
        "flowchart": {"htmlLabels": True, "nodeSpacing": 30, "rankSpacing": 50, "padding": 12, "curve": "basis",
                      "subGraphTitleMargin": {"top": 6, "bottom": 22}},
    }
 
name, styles = 'architecture_bw', bw_styles + bw_sub
if True:
    with open(name + '.mmd', 'w', encoding='utf-8') as f:
        f.write(FLOW + '\n' + styles)
    with open(name + '.json', 'w', encoding='utf-8') as f:
        json.dump(config(), f, indent=2)
    subprocess.run(['mmdc', '-i', name + '.mmd', '-o', name + '.pdf', '-c', name + '.json',
                    '-b', 'white', '-w', '1600', '-H', '2000', '--pdfFit'], check=True)
 
print("Architecture diagrams created!")
 