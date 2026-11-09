import json
import subprocess

FLOW = '''flowchart TB
    subgraph Frontend["Prezentační vrstva"]
        S1["Streamlit"] ~~~ S2["Plotly"]
    end

    subgraph Backend["Backendová vrstva"]
        B1["FastAPI"] ~~~ B2["Pandas / NumPy"] ~~~ B3["PostgreSQL + Psycopg"]
    end

    subgraph Comm["Komunikační vrstva"]
        C1["MQTT (Paho-MQTT)"]
    end

    subgraph Edge["Edge vrstva (Raspberry Pi 5 + Hailo-8)"]
        E1["Raspberry Pi OS (Debian Linux)"] ~~~ E2["Python 3.11"] ~~~ E3["GStreamer"]
        E4["HailoRT + TAPPAS (YOLOv8m)"] ~~~ E5["Shapely (filtrace ROI)"]
    end

    Frontend -. "HTTP REST (GET / POST)" .-> Backend
    Backend -. "pub/sub, JSON zprávy" .-> Comm
    Comm -. "MQTT broker" .-> Edge
'''

NODES = ['S1', 'S2', 'B1', 'B2', 'B3', 'C1', 'E1', 'E2', 'E3', 'E4', 'E5']
SUBS = ['Frontend', 'Backend', 'Comm', 'Edge']

# Black-and-white academic style (matches architecture_bw)
bw_styles = ''.join(
    f'    style {k} fill:#ffffff,stroke:#000000,stroke-width:1.5px,color:#000000\n' for k in NODES)
bw_sub = ''.join(
    f'    style {k} fill:#f0f0f0,stroke:#000000,stroke-width:1.5px,color:#000000\n' for k in SUBS)

def config():
    return {
        "theme": "base",
        "fontFamily": "Liberation Serif, Times New Roman, serif",
        "fontSize": 18,
        "themeVariables": {
            "fontSize": "18px",
            "fontFamily": "Liberation Serif, Times New Roman, serif",
            "primaryTextColor": "#000000",
            "textColor": "#000000",
            "titleColor": "#000000",
            "lineColor": "#000000",
            "edgeLabelBackground": "#ffffff",
            "clusterBkg": "#f0f0f0",
            "clusterBorder": "#000000",
        },
        "flowchart": {"htmlLabels": True, "nodeSpacing": 25, "rankSpacing": 60, "padding": 12,
                      "curve": "basis", "subGraphTitleMargin": {"top": 6, "bottom": 22}},
    }

name = 'tech_stack_bw'
with open(name + '.mmd', 'w', encoding='utf-8') as f:
    f.write(FLOW + '\n' + bw_styles + bw_sub)
with open(name + '.json', 'w', encoding='utf-8') as f:
    json.dump(config(), f, indent=2)
subprocess.run(['mmdc', '-i', name + '.mmd', '-o', name + '.pdf', '-c', name + '.json',
                '-b', 'white', '-w', '1600', '-H', '1200', '--pdfFit'], check=True)
print("Tech stack diagram created!")
