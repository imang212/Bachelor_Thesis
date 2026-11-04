import json
import subprocess

mermaid_config = {
    "theme": "base",
    "fontFamily": "DejaVu Sans, Arial, sans-serif",
    "themeVariables": {
        "fontSize": "18px",
        "fontFamily": "DejaVu Sans, Arial, sans-serif",
        "primaryColor": "#ffffff",
        "primaryBorderColor": "#222222",
        "primaryTextColor": "#111111",
        "lineColor": "#222222",
        "clusterBkg": "#f7f7f7",
        "clusterBorder": "#666666",
        "edgeLabelBackground": "#ffffff"
    },
    "flowchart": {
        "nodeSpacing": 45,
        "rankSpacing": 65,
        "padding": 18,
        "htmlLabels": True
    }
}

mermaid_code = '''graph LR
    subgraph "Network interface"
        Camera["IP camera"]
    end

    subgraph "Raspberry Pi (Edge)"
        AI["Detection Module<br/>(Python + GStreamer)"]
    end
    
    subgraph "MQTT Server"
        MQTT["MQTT Broker"]
    end

    subgraph "Backend"
        DB[("Database<br/>(PostgreSQL)")]
        DBListener["Data module<br/>(MQTT subscriber)"]
        FastAPI["FastAPI Server"]
    end

    subgraph "Frontend"
        Streamlit["Streamlit Dashboard"]
    end
    
    Camera -->|RTSP stream| AI
    AI -->|sending JSON| MQTT
    DBListener <-->|listen / publish| MQTT
    DBListener -->|writing batch| DB
    FastAPI <-->|query / reading| DB
    Streamlit <-->|POST / GET| FastAPI
    
    style AI fill:#ffffff,stroke:#222222,stroke-width:1.5px
    style Camera fill:#ffffff,stroke:#222222,stroke-width:1.5px
    style MQTT fill:#ffffff,stroke:#222222,stroke-width:1.5px
    style DB fill:#eaeaea,stroke:#222222,stroke-width:1.5px
    style DBListener fill:#ffffff,stroke:#222222,stroke-width:1.5px
    style FastAPI fill:#ffffff,stroke:#222222,stroke-width:1.5px
    style Streamlit fill:#ffffff,stroke:#222222,stroke-width:1.5px
'''

with open('arch_config.json', 'w', encoding='utf-8') as f:
    json.dump(mermaid_config, f, indent=2)

with open('architecture.mmd', 'w', encoding='utf-8') as f:
    f.write(mermaid_code)

subprocess.run([
    'mmdc',
    '-i', 'architecture.mmd',
    '-o', 'architecture_bw.pdf',
    '-c', 'arch_config.json',
    '-b', 'white',
    '-w', '2200',
    '-H', '800',
    '--pdfFit'
], check=True)

print("Černobílý vektorový diagram architecture_bw.pdf byl vytvořen!")