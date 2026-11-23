"""
Streamlit Analytics Dashboard for Traffic Monitoring System.
Can be run standalone via:
    streamlit run rpi_src/pipeline/streamlit_dashboard.py
or launched automatically via API_with_streamlit.py.
"""
from datetime import datetime, time as dt_time
import os
import time
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
    def fetch_filter_metadata():
        try:
            response = requests.get(f"{API_BASE_URL}/api/filter_metadata", timeout=10)
            return response.json() if response.status_code == 200 else {}
        except Exception:
            return {}

    @st.cache_data(ttl=60)
    def fetch_detections(start_time=None, end_time=None, device_type=None, model_name=None, limit=None):
        try:
            params = {"limit": 0 if limit is None else limit}
            if start_time and end_time:
                params["start_time"] = start_time.isoformat()
                params["end_time"] = end_time.isoformat()
            if device_type:
                params["device_type"] = device_type
            if model_name:
                params["model_name"] = model_name
            response = requests.get(f"{API_BASE_URL}/api/detections", params=params, timeout=300)
            if response.status_code == 200:
                data = response.json()
                if data:
                    df = pd.DataFrame(data)
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                    df[["x1", "y1", "x2", "y2"]] = pd.DataFrame(df["bbox"].tolist(), index=df.index)
                    return df
            return pd.DataFrame()
        except Exception as e:
            st.error(f"Error fetching detections: {str(e)}")
            return pd.DataFrame()

    @st.cache_data(ttl=60)
    def fetch_timeline(interval="10min", start_time=None, end_time=None, device_type=None, model_name=None):
        try:
            params = {"interval": interval}
            if start_time and end_time:
                params["start_time"] = start_time.isoformat()
                params["end_time"] = end_time.isoformat()
            if device_type:
                params["device_type"] = device_type
            if model_name:
                params["model_name"] = model_name
            response = requests.get(f"{API_BASE_URL}/api/timeline", params=params, timeout=60)
            if response.status_code == 200 and response.json():
                df = pd.DataFrame(response.json())
                df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_localize(None)
                return df
            return pd.DataFrame()
        except Exception as e:
            st.error(f"Error fetching timeline: {str(e)}")
            return pd.DataFrame()
    
    @st.cache_data(ttl=60)
    def fetch_statistics(start_time=None, end_time=None, device_type=None, model_name=None):
        try:
            params = {}
            if start_time and end_time:
                params["start_time"] = start_time.isoformat()
                params["end_time"] = end_time.isoformat()
            if device_type:
                params["device_type"] = device_type
            if model_name:
                params["model_name"] = model_name
            response = requests.get(f"{API_BASE_URL}/api/statistics", params=params, timeout=300)
            return response.json() if response.status_code == 200 else {}
        except Exception:
            return {}

    @st.cache_data(ttl=30)
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

        st.subheader("Data Filters")
        meta = fetch_filter_metadata()
        min_ts = pd.to_datetime(meta["min_timestamp"]).tz_localize(None) if meta.get("min_timestamp") else None
        max_ts = pd.to_datetime(meta["max_timestamp"]).tz_localize(None) if meta.get("max_timestamp") else None
        available_devices, available_models = meta.get("device_types", []), meta.get("model_names", [])
        selected_start, selected_end = None, None
        period_label = "selected period"

        if min_ts and max_ts:
            st.markdown(
                f"""
                <div style="
                    background-color: rgba(28, 131, 225, 0.1);
                    border-left: 3px solid #1c83e1;
                    padding: 6px 10px;
                    border-radius: 4px;
                    font-size: 12px;
                    line-height: 1.4;
                    margin-bottom: 10px;
                ">
                    <strong>Dataset range:</strong><br>
                    {min_ts.strftime('%d.%m.%Y %H:%M')} – {max_ts.strftime('%d.%m.%Y %H:%M')}
                </div>
                """,
                unsafe_allow_html=True,
            )
            use_full_range = st.checkbox("Select entire dataset range", value=False)
            if use_full_range:
                start_d, end_d = min_ts.date(), max_ts.date()
                start_t, end_t = min_ts.time().replace(microsecond=0), max_ts.time().replace(microsecond=0)
            else:
                default_start = max(min_ts.date(), (max_ts - pd.Timedelta(days=7)).date())
                date_range = st.date_input(
                    "Date range",
                    value=(default_start, max_ts.date()),
                    min_value=min_ts.date(),
                    max_value=max_ts.date(),
                )
                if isinstance(date_range, tuple) and len(date_range) == 2:
                    start_d, end_d = date_range
                else:
                    start_d = end_d = date_range[0] if isinstance(date_range, tuple) else date_range
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    start_t = st.time_input("From time", value=dt_time(0, 0))
                with col_t2:
                    end_t = st.time_input("To time", value=dt_time(23, 59, 59))

            selected_start = datetime.combine(start_d, start_t)
            selected_end = datetime.combine(end_d, end_t)
            period_label = f"{selected_start.strftime('%d.%m.%Y %H:%M')} – {selected_end.strftime('%d.%m.%Y %H:%M')}"
        else:
            st.warning("No timestamp range found in database.")

        # Device type selector (auto-select if only 1 exists in DB)
        selected_device = None
        if len(available_devices) == 1:
            selected_device = available_devices[0]
            st.selectbox("Device type", options=available_devices, index=0, disabled=True)
        elif len(available_devices) > 1:
            choice = st.selectbox("Device type", options=["All"] + available_devices, index=0)
            selected_device = None if choice == "All" else choice

        # Model name selector (auto-select if only 1 exists in DB)
        selected_model = None
        if len(available_models) == 1:
            selected_model = available_models[0]
            st.selectbox("Model name", options=available_models, index=0, disabled=True)
        elif len(available_models) > 1:
            choice = st.selectbox("Model name", options=["All"] + available_models, index=0)
            selected_model = None if choice == "All" else choice

        max_points = st.select_slider(
            "Max chart records",
            options=[5000, 10000, 25000, 50000, 100000, 250000],
            value=50000,
        )
        INTERVAL_MAP = {
            "1 minute": "1min",
            "10 minutes": "10min",
            "30 minutes": "30min",
            "1 hour": "1h",
            "6 hours": "6h",
            "1 day": "1D",
            "1 week": "1W",
            "1 month": "1ME",
            "3 months": "3ME",
            "1 year": "1YE",
        }
        DTICK_MAP = {
            "1min": 1 * 60 * 1000,
            "10min": 10 * 60 * 1000,
            "30min": 30 * 60 * 1000,
            "1h": 60 * 60 * 1000,
            "6h": 6 * 60 * 60 * 1000,
            "1D": 24 * 60 * 60 * 1000,
            "1W": 7 * 24 * 60 * 60 * 1000,
            "1ME": "M1",
            "3ME": "M3",
            "1YE": "M12",
        }
        FORMAT_MAP = {
            "1min": "%H:%M",
            "10min": "%H:%M",
            "30min": "%H:%M",
            "1h": "%H:%M",
            "6h": "%d.%m %H:%M",
            "1D": "%d.%m",
            "1W": "%d.%m",
            "1ME": "%b %Y",
            "3ME": "%b %Y",
            "1YE": "%Y",
        }
        st.markdown("---")
        auto_refresh = st.checkbox("Enable auto-refresh", value=True)
        refresh_interval = st.slider("Refresh interval (seconds)", 5, 60, 60)
        if st.button("Refresh Now"):
            st.cache_data.clear()
            st.rerun()

    ## DASHBOARD
    if db_status and db_status.get('status') == "healthy":
        df_detections = fetch_detections(
            start_time=selected_start,
            end_time=selected_end,
            device_type=selected_device,
            model_name=selected_model,
            limit=max_points,
        )
        col1 = st.columns(1)[0]
        with col1:
            st.subheader(f"Statistics Summary")
            stats = fetch_statistics(start_time=selected_start, end_time=selected_end, device_type=selected_device, model_name=selected_model,)
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
            st.subheader(f"Detection Analytics Dashboard")
            col1, col2 = st.columns(2)
            with col1:
                total_in_period = sum(d['total_detections'] for d in stats.values()) if stats else len(df_detections)
                st.metric("Total Detections (period)", f"{total_in_period:,}")
            with col2:
                st.metric("Avg Confidence", f"{df_detections['confidence'].mean():.2%}")

            # Histogram
            col1 = st.columns(1)[0]
            with col1:
                st.subheader("Histogram of Detected Classes")
                per = st.pills(
                    "**Time aggregation:**",
                    options=list(INTERVAL_MAP.keys()),
                    selection_mode="single",
                    default="10 minutes",
                    key="time_aggregation_pills",
                )
                per = per if per is not None else "10 minutes"
                selected = INTERVAL_MAP[per]
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
                df_class_timeline = df_class_timeline = fetch_timeline(
                    interval=selected,
                    start_time=selected_start,
                    end_time=selected_end,
                    device_type=selected_device,
                    model_name=selected_model,
                )
                if not df_class_timeline.empty:
                    class_order = (
                        df_class_timeline.groupby('class_name')['count']
                        .sum()
                        .sort_values(ascending=True)
                        .index.tolist()
                    )
                    df_class_timeline['class_name'] = pd.Categorical(
                        df_class_timeline['class_name'],
                        categories=class_order,
                        ordered=True,
                    )
                    unique_times = sorted(df_class_timeline['timestamp'].unique())
                    columns_count = len(unique_times)
                    if columns_count >= 1:
                        fig_timeline = go.Figure()
                        for cls in class_order:
                            df_cls = df_class_timeline[df_class_timeline['class_name'] == cls]
                            fig_timeline.add_trace(go.Bar(
                                x=df_cls['timestamp'],
                                y=df_cls['count'],
                                name=cls,
                            ))
                        if len(class_order) > 1:
                            fig_timeline.update_layout(barmode='stack')
                        fig_timeline.update_traces(marker_line_width=0)
                        fig_timeline.update_xaxes(
                            type="date",
                            title="Time",
                            ticklabelmode="period",
                            dtick=DTICK_MAP[selected] if columns_count < 60 else None,
                            nticks=15 if columns_count >= 60 else None,
                            tickformat=FORMAT_MAP[selected],
                            tickangle=-45 if columns_count > 20 else 0,
                        )
                        fig_timeline.update_layout(
                            title=f"Diagram by detections every {per}",
                            height=800,
                            hovermode="x unified",
                            yaxis_title="Number of Objects",
                            legend_title="Class",
                            xaxis_title="Time",
                            transition={'duration': 0},
                            uirevision='constant',
                        )
                        st.plotly_chart(
                            fig_timeline,
                            use_container_width=True,
                            config={'displayModeBar': False, 'staticPlot': False},
                        )
                else:
                    st.info("No timeline data available for the selected filters.")    

            # Detection timeline line chart
            col1 = st.columns(1)[0]
            with col1:
                if not df_class_timeline.empty:
                    df_hourly = (
                        df_class_timeline.groupby("timestamp", as_index=False)["count"]
                        .sum()
                        .sort_values("timestamp")
                    )
                    fig_line = px.line(
                        df_hourly,
                        x="timestamp",
                        y="count",
                        title=f"Detection timeline every {per}",
                        markers=True,
                    )
                    fig_line.update_xaxes(
                        type="date",
                        title="Time",
                        nticks=10,
                        tickformat=FORMAT_MAP[selected],
                        ticklabelmode="period",
                        ticks="outside",
                    )
                    fig_line.update_layout(
                        height=400,
                        hovermode="x unified",
                        yaxis_title="Number of Objects",
                    )
                    st.plotly_chart(fig_line, use_container_width=True)
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