"""
Streamlit Analytics Dashboard for Traffic Monitoring System.
Can be run standalone via:
    streamlit run rpi_src/pipeline/streamlit_dashboard.py
or launched automatically via API_with_streamlit.py.
"""
import os
import time
import asyncio
import requests
import numpy as np  
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

def run_streamlit():
    """Streamlit dashboard - runs in separate process"""
    st.set_page_config(
        page_title="Detection Analytics Dashboard",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.markdown("""
        <style>
        .main { padding: 0rem 1rem; }
        .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
        [data-testid="stMetricValue"] { font-size: 24px;  /* Change the value size */ }
        [data-testid="stMetricLabel"] { font-size: 28px;  /* Change the label size */ }
        [data-testid="stMetricDelta"] { font-size: 24px;  /* Change the delta size */ }
        </style>
    """, unsafe_allow_html=True)
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

    @st.cache_data(ttl=60)
    def fetch_detections(minutes=60, limit=10000000):
        try:
            response = requests.get(
                f"{API_BASE_URL}/api/detections",
                params={"minutes": minutes, "limit": limit},
                timeout=300
            )
            if response.status_code == 200:
                data = response.json()
                #print(data[0:5])  # Print first 5 records for debugging
                #print(f"Fetched {len(data)} detections")
                if data:
                    df = pd.DataFrame(data)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df[['x1', 'y1', 'x2', 'y2']] = pd.DataFrame(df['bbox'].tolist(), index=df.index) # into columns
                    return df
                #print(df.head())
                return pd.DataFrame()
            else:
                st.error(f"API Error: {response.status_code} - {response.text}")
                return pd.DataFrame()
        except requests.Timeout:
            st.error(f"Request timed out fetching {minutes} minutes of data")
            return pd.DataFrame()
        except Exception as e:
            st.error(f"Error fetching detections: {str(e)}")
            return pd.DataFrame()

    @st.cache_data(ttl=60)
    def fetch_statistics(hours=24):
        try:
            response = requests.get(
                f"{API_BASE_URL}/api/statistics",
                params={"hours": hours},
                timeout=300
            )
            data = response.json()
            if data:
                print(f"Fetched statistics: {data}")
                return data
            #print(f'{response.json()}')
        except Exception:
            return {}

    @st.cache_data(ttl=5)
    def fetch_pipeline_status():
        try:
            response = requests.get(f"{API_BASE_URL}/pipeline/status", timeout=5)
            return response.json() if response.status_code == 200 else None
        except Exception:
            return None

    def start_pipeline(config):
        try:
            response = requests.post(f"{API_BASE_URL}/pipeline/start", json=config, timeout=10)
            return response.status_code == 200, response.json()
        except Exception as e:
            return False, {"error": str(e)}

    def stop_pipeline():
        try:
            response = requests.post(f"{API_BASE_URL}/pipeline/stop", timeout=10)
            return response.status_code == 200, response.json()
        except Exception as e:
            return False, {"error": str(e)}

    def fetch_db_status():
        try:
            response = requests.get(f"{API_BASE_URL}/database/status", timeout=5)
            return response.json() if response.status_code == 200 else None
        except Exception:
            return None

    def start_database(mqtt_connect):
        try:
            print(f"Starting database with MQTT: {mqtt_connect}")
            response = requests.post(f"{API_BASE_URL}/database/start", json={"mqtt_sending": mqtt_connect}, timeout=10)
            return response.status_code == 200, response.json()
        except Exception as e:
            return False, {"error": str(e)}

    def stop_database():
        try:
            response = requests.post(f"{API_BASE_URL}/database/stop", timeout=10)
            return response.status_code == 200, response.json()
        except Exception as e:
            return False, {"error": str(e)}

    ## SIDEBAR
    with st.sidebar:
        st.header("System Control")
        st.subheader("Database")
        db_status = fetch_db_status()
        print(f"DB Status: {db_status}")
        if db_status and db_status.get('status') == "healthy":
            st.success("CONNECTED")
            if db_status.get('total_detections') is not None:
                st.metric("Total Detections", f"{db_status['total_detections']:,}")
            if db_status.get('database_size') is not None:
                st.metric("Database Size", db_status['database_size'])
        else:
            st.error("Not Connected")
            if st.button("Start Database", use_container_width=True):
                with st.spinner("Starting database..."):
                    success, result = start_database(mqtt_connect=False)
                    if success:
                        st.success("Database started!")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Failed: {result}")

        stats_format_func = lambda x: f"Last {x} hours" if x < 24 else f"Last {x//24} days"
        time_format_func = lambda x: f"Last {x} minutes" if x < 60 else (f"Last {x//1440} days" if x > 1440 else f"Last {x//60} hours")
        st.subheader("Detections Time Range")
        time_range = st.selectbox(
            "Select time range",
            options=[60, 180, 360, 720, 1440, 2880, 5760, 10080, 20160, 40320, 80640, 161280, 322560, 604800],
            format_func=time_format_func,
            index=1
        )
        INTERVAL_MAP = {"1 minute": "1T", "10 minutes": "10T", "30 minutes": "30T", "1 hour": "1H", "1 day": "1D", "1 month": "M1"}
        DTICK_MAP = {"1T": 1 * 60 * 1000, "10T": 10 * 60 * 1000, "30T": 30 * 60 * 1000, "1H": 60 * 60 * 1000, "6H": 6 * 60 * 60 * 1000, "1D": 24 * 60 * 60 * 1000, "1W": 7 * 24 * 60 * 60 * 1000, "1M": "M1", "3M": "M3", "1Y": "M12"}
        FORMAT_MAP = {"1T": "%H:%M", "10T": "%H:%M", "30T": "%H:%M", "1H": "%H:%M", "6H": "%H:%M", "1D": "%d.%m", "1W": "%d.%m", "M1": "%b %Y", "M3": "%b %Y", "M12": "%Y"}
        st.markdown("---")
        auto_refresh = st.checkbox("Enable auto-refresh", value=True)
        refresh_interval = st.slider("Refresh interval (seconds)", 5, 60, 60)
        if st.button("Refresh Now"):
            st.cache_data.clear()
            st.rerun()

    ## DASHBOARD
    if db_status and db_status.get('status') == "healthy":
        df_detections = fetch_detections(minutes=time_range, limit=10000000)
        col1 = st.columns(1)[0]
        with col1:
            st.subheader("Statistics Summary")
            stats_hours = st.selectbox(
                "**Statistics time range:**",
                options=[1, 6, 12, 24, 48, 168, 336, 720, 1440, 2880, 5760, 10080, 20160, 40320],
                format_func=stats_format_func,
                index=3
            )
            stats = fetch_statistics(hours=stats_hours)
            if stats:
                stats_data = []
                for class_name, data in stats.items():
                    stats_data.append({
                        'Class': data['class_name'],
                        'Total Detections': data['total_detections'],
                        'Avg Confidence': f"{data['avg_confidence']:.2%}",
                        'Min Confidence': f"{data['min_confidence']:.2%}",
                        'Max Confidence': f"{data['max_confidence']:.2%}"
                    })
                stats_df = pd.DataFrame(stats_data)
                st.dataframe(stats_df, width='stretch', hide_index=True)
            else:
                st.info("No statistics available for the selected time range.")

        if isinstance(df_detections, list) or df_detections.empty:
            st.warning("No detection data available for the selected time range.")
        else:
            st.subheader(f"Detection Analytics Dashboard {time_format_func(time_range).lower()}.")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Detections", f"{len(df_detections):,}")
            with col2:
                st.metric("Avg Confidence", f"{df_detections['confidence'].mean():.2%}")

            # Histogram
            col1 = st.columns(1)[0]
            with col1:
                st.subheader("Histogram of Detected Classes")
                per = st.pills(
                    "**Time aggregation:**",
                    options=["1 minute", "10 minutes", "30 minutes", "1 hour", "1 day", "1 month"],
                    selection_mode="single",
                    default="10 minutes",
                    key="time_aggregation_pills"
                )
                per = per if per is not None else "10 minutes"
                selected = INTERVAL_MAP[per]
                available_classes = sorted(df_detections['class_name'].unique().tolist())
                selected_classes = None
                st.html("""
                <style>
                    [data-testid="stButtonGroup"] {
                        margin-bottom: 0px !important;
                        padding-bottom: 0px !important;
                    }
                    [data-testid="stBaseButton-pillsActive"] {
                        background-color: #1a4a1a !important;
                        color: #ffffff !important;
                        border: 1px solid #2e7d32 !important;
                        border-radius: 0px !important;
                        font-size: 12px !important;
                        height: 26px !important;
                        padding: 2px 10px !important;
                    }
                    [data-testid="stBaseButton-pills"] {
                        background-color: #3a3a3a !important;
                        color: #aaaaaa !important;
                        border: 1px solid #555 !important;
                        border-radius: 0px !important;
                        font-size: 12px !important;
                        height: 26px !important;
                        padding: 2px 10px !important;
                    }
                    [data-testid="stBaseButton-pillsActive"]:hover { background-color: #2e5a2e !important; }
                    [data-testid="stBaseButton-pills"]:hover { background-color: #4a4a4a !important; }
                </style>
                """)
                active_classes = tuple(sorted(selected_classes if selected_classes else available_classes))

                def compute_timeline(df_det: pd.DataFrame, sel, act_classes):
                    df_timeline = df_det[df_det['class_name'].isin(act_classes)].copy()
                    df_timeline['timestamp'] = pd.to_datetime(df_timeline['timestamp'], utc=True).dt.tz_localize(None)
                    df_timeline = df_timeline.set_index("timestamp")
                    df_grouped = (df_timeline.groupby('class_name').resample(sel)["class_name"].size().reset_index(name="count"))
                    df_pivot = df_grouped.pivot_table(index='timestamp', columns='class_name', values='count', fill_value=0).reset_index()
                    df_long = df_pivot.melt(id_vars='timestamp', var_name='class_name', value_name='count')
                    unique_times = sorted(df_long['timestamp'].unique())
                    if len(df_long) > 0 and len(unique_times) > 2:
                        df_long = df_long[(df_long['timestamp'] > unique_times[0]) & (df_long['timestamp'] < unique_times[-1])]
                    return df_long

                df_class_timeline = compute_timeline(df_detections, selected, active_classes)
                class_order = (df_class_timeline.groupby('class_name')['count'].sum().sort_values(ascending=True).index.tolist())
                df_class_timeline['class_name'] = pd.Categorical(df_class_timeline['class_name'], categories=class_order, ordered=True)
                unique_times = sorted(df_class_timeline['timestamp'].unique())
                columns_count = max(len(unique_times), 1)
                if columns_count >= 5:
                    fig_timeline = go.Figure()
                    if len(active_classes) == 1:
                        fig_timeline.add_trace(go.Bar(
                            x=df_class_timeline['timestamp'],
                            y=df_class_timeline['count'],
                            name=active_classes[0],
                        ))
                    else:
                        for cls in class_order:
                            df_cls = df_class_timeline[df_class_timeline['class_name'] == cls]
                            fig_timeline.add_trace(go.Bar(
                                x=df_cls['timestamp'],
                                y=df_cls['count'],
                                name=cls,
                            ))
                        fig_timeline.update_layout(barmode='stack')
                    fig_timeline.update_traces(marker_line_width=0)
                    fig_timeline.update_xaxes(
                        type="date",
                        title="Time",
                        ticklabelmode="period",
                        nticks=DTICK_MAP[selected] if columns_count < 60 else 15,
                        tickformat=FORMAT_MAP[selected],
                        tickangle=-45 if columns_count > 20 else 0
                    )
                    fig_timeline.update_layout(
                        title=f"Diagram by detections every {per}",
                        height=800,
                        hovermode="x unified",
                        yaxis_title="Number of Objects",
                        legend_title="Class",
                        xaxis_title="Time",
                        transition={'duration': 0},
                        uirevision='constant'
                    )
                    st.plotly_chart(fig_timeline, use_container_width=True, config={'displayModeBar': False, 'staticPlot': False})
                else:
                    st.info("A little data available for the selected time range.")

            # Detection timeline line chart
            col1 = st.columns(1)[0]
            with col1:
                df_timeline = df_detections.copy()
                selected = INTERVAL_MAP[per]
                df_timeline = df_timeline.set_index("timestamp")
                df_hourly = (
                    df_timeline.resample(selected)
                    .size()
                    .reset_index(name="count")
                )
                df_timeline = df_hourly
                if len(df_timeline) > 2:
                    df_timeline = df_timeline.iloc[1:-1]
                fig_timeline = px.line(
                    df_timeline,
                    x=df_timeline.columns[0],
                    y="count",
                    title=f"Detection timeline every {per}",
                    markers=True
                )
                fig_timeline.update_xaxes(
                    type="date",
                    title="Time",
                    nticks=10,
                    tickformat=FORMAT_MAP[selected],
                    ticklabelmode="period",
                    ticks="outside"
                )
                fig_timeline.update_layout(
                    height=400,
                    hovermode="x unified",
                    yaxis_title="Number of Objects"
                )
                st.plotly_chart(fig_timeline, use_container_width=True)

            # Class distribution pie chart
            col1 = st.columns(1)[0]
            with col1:
                class_counts = df_detections['class_name'].value_counts()
                fig_pie = px.pie(
                    values=class_counts.values,
                    names=class_counts.index,
                    hole=0.4,
                    title="Class distribution pie",
                )
                fig_pie.update_layout(height=500)
                st.plotly_chart(fig_pie, width='stretch')

            # Confidence distribution
            col1 = st.columns(1)[0]
            with col1:
                fig_conf = px.box(
                    df_detections,
                    x='class_name',
                    y='confidence',
                    color='class_name',
                    title='Confidence by Class',
                    labels={'class_name': 'Class', 'confidence': 'Confidence'}
                )
                fig_conf.update_layout(height=800, showlegend=False)
                st.plotly_chart(fig_conf, width='stretch')
            st.markdown("---")

            col1 = st.columns(1)[0]
            with col1:
                df_bbox = df_detections.copy()
                df_bbox['center_x'] = (df_bbox['bbox'].apply(lambda x: x[0]) + df_bbox['bbox'].apply(lambda x: x[2])) / 2
                df_bbox['center_y'] = (df_bbox['bbox'].apply(lambda x: x[1]) + df_bbox['bbox'].apply(lambda x: x[3])) / 2
                fig_scatter = px.scatter(
                    df_bbox,
                    x='center_x',
                    y='center_y',
                    color='class_name',
                    size='confidence',
                    title='Detection Positions (Bbox Centers)',
                    labels={'center_x': 'X Position', 'center_y': 'Y Position', 'class_name': 'Class'},
                    opacity=0.6
                )
                fig_scatter.update_yaxes(autorange="reversed")
                fig_scatter.update_layout(title='Spatial analysis map', height=400)
                st.plotly_chart(fig_scatter, use_container_width=True)

            # Bounding box density heatmap
            col1 = st.columns(1)[0]
            with col1:
                df_bbox = df_detections.copy()
                df_bbox['center_x'] = (df_bbox['bbox'].apply(lambda x: x[0]) + df_bbox['bbox'].apply(lambda x: x[2])) / 2
                df_bbox['center_y'] = (df_bbox['bbox'].apply(lambda x: x[1]) + df_bbox['bbox'].apply(lambda x: x[3])) / 2
                bins_x = 40
                bins_y = 40
                heatmap, xedges, yedges = np.histogram2d(
                    df_bbox['center_x'],
                    df_bbox['center_y'],
                    bins=[bins_x, bins_y]
                )
                fig_heatmap = go.Figure(data=go.Heatmap(
                    z=heatmap.T,
                    x=xedges[:-1],
                    y=yedges[:-1],
                    colorscale='Hot',
                    colorbar=dict(title="Density<br>(0-1)")
                ))
                fig_heatmap.update_layout(
                    title='Detection Density Heatmap',
                    xaxis_title='X Position',
                    yaxis_title='Y Position',
                    height=600,
                    yaxis=dict(autorange="reversed")
                )
                st.plotly_chart(fig_heatmap, use_container_width=True)

            # Class distribution bar chart
            col1 = st.columns(1)[0]
            with col1:
                class_dist = df_detections['class_name'].value_counts().reset_index()
                class_dist.columns = ['Class', 'Count']
                fig_bar = px.bar(
                    class_dist,
                    x='Class',
                    y='Count',
                    color='Class',
                    title='Detections distribution by Class',
                    labels={'Count': 'Number of Detections', 'Class': 'Object Class'},
                    text='Count'
                )
                fig_bar.update_traces(texttemplate='%{text}', textposition='outside')
                fig_bar.update_layout(height=600, showlegend=False)
                st.plotly_chart(fig_bar, width='stretch')
    else:
        st.info("No database connected.")

    if auto_refresh:
        time.sleep(refresh_interval)
        st.cache_data.clear()
        st.rerun()


if __name__ == "__main__":
    run_streamlit()