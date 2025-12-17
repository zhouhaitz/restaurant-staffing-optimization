"""Restaurant Simulation GUI - Main Streamlit Application.

This is the main entry point for the Restaurant Simulation visualization application.
Run with: streamlit run gui/app.py

Features:
- Load JSON log files from the simulation
- Interactive dashboard with RevPASH and utilization metrics
- Animated playback of simulation state
- Performance analysis and summary statistics
"""

import streamlit as st
import time
from typing import Dict, Any, Optional

# Import GUI modules
from data_loader import load_and_prepare_data, LogValidationError, get_log_summary
from metrics_calculator import (
    calculate_revpash,
    calculate_instantaneous_revpash,
    calculate_table_utilization,
    calculate_staff_utilization,
    calculate_station_utilization,
    calculate_queue_metrics,
    calculate_throughput_metrics,
    calculate_service_times,
    calculate_summary_statistics,
)
from visualizations import (
    plot_revpash_over_time,
    plot_revenue_accumulation,
    plot_table_utilization,
    plot_staff_utilization,
    plot_station_utilization,
    plot_queue_lengths,
    plot_station_queues,
    plot_utilization_heatmap,
    plot_throughput,
    plot_service_time_distribution,
    plot_current_state_gauges,
)
from animation_player import (
    AnimationPlayer,
    render_restaurant_layout,
    render_station_status,
    render_party_flow,
    render_current_metrics,
)
from utils import (
    get_total_seats_from_snapshots,
    get_total_tables_from_snapshots,
    format_time_display,
    get_time_range,
)


# Page configuration
st.set_page_config(
    page_title="Restaurant Simulation Dashboard",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    """Main application entry point."""
    
    # Initialize session state
    if "data" not in st.session_state:
        st.session_state.data = None
    if "player" not in st.session_state:
        st.session_state.player = None
    if "current_time" not in st.session_state:
        st.session_state.current_time = 0.0
    if "is_playing" not in st.session_state:
        st.session_state.is_playing = False
    
    # Sidebar
    with st.sidebar:
        st.title("🍽️ Restaurant Simulation")
        st.markdown("---")
        
        # File upload
        uploaded_file = st.file_uploader(
            "Upload Simulation Log (JSON)",
            type=["json"],
            help="Upload a JSON log file exported from the restaurant simulation"
        )
        
        if uploaded_file is not None:
            try:
                # Load and process data
                with st.spinner("Loading simulation data..."):
                    data = load_and_prepare_data(uploaded_file, max_hours=4.0)
                    st.session_state.data = data
                    st.session_state.player = AnimationPlayer(data["snapshots"])
                    st.session_state.current_time = 0.0
                    
                st.success(f"Loaded {len(data['snapshots'])} snapshots")
                
            except LogValidationError as e:
                st.error(f"Invalid log file: {e}")
            except Exception as e:
                st.error(f"Error loading file: {e}")
        
        # Display summary if data loaded
        if st.session_state.data is not None:
            st.markdown("---")
            st.subheader("📊 Log Summary")
            
            summary = st.session_state.data.get("summary", {})
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Duration", f"{summary.get('duration_hours', 0):.1f}h")
                st.metric("Parties", summary.get("num_parties", 0))
            with col2:
                st.metric("Snapshots", summary.get("num_snapshots", 0))
                st.metric("Events", summary.get("num_events", 0))
            
            st.metric("Total Revenue", f"${summary.get('total_revenue', 0):,.2f}")
            
            st.markdown("---")
            
            # Playback controls
            st.subheader("🎬 Playback Controls")
            
            min_time, max_time = get_time_range(st.session_state.data["snapshots"])
            
            st.session_state.current_time = st.slider(
                "Time",
                min_value=float(min_time),
                max_value=float(max_time),
                value=st.session_state.current_time,
                format="%.1f min",
                key="time_slider",
            )
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("⏮️ Start"):
                    st.session_state.current_time = min_time
            with col2:
                play_text = "⏸️ Pause" if st.session_state.is_playing else "▶️ Play"
                if st.button(play_text):
                    st.session_state.is_playing = not st.session_state.is_playing
            with col3:
                if st.button("⏭️ End"):
                    st.session_state.current_time = max_time
            
            playback_speed = st.select_slider(
                "Speed",
                options=[0.5, 1.0, 2.0, 5.0, 10.0],
                value=1.0,
                format_func=lambda x: f"{x}x",
            )
    
    # Main content area
    if st.session_state.data is None:
        # Welcome screen
        st.title("Restaurant Simulation Dashboard")
        st.markdown("""
        Welcome to the Restaurant Simulation visualization dashboard.
        
        ### Getting Started
        
        1. **Upload a log file** using the sidebar file uploader
        2. The log file should be a JSON file exported from the restaurant simulation
           using `simulation.export_all_logs_to_json()`
        
        ### Features
        
        - **RevPASH & Revenue**: Track Revenue Per Available Seat Hour over time
        - **Utilization Dashboard**: Monitor table, staff, and station utilization
        - **System Animation**: Animated playback of restaurant state
        - **Performance Summary**: Service time distributions and throughput metrics
        
        ### Log File Format
        
        The log file should contain:
        - `metadata`: Simulation parameters and summary
        - `snapshots`: State snapshots at each time point
        - `events`: (Optional) Event log with state transitions
        
        Maximum simulation duration: **4 hours**
        """)
        
        st.info("👈 Upload a JSON log file to get started")
        return
    
    # Data is loaded - show dashboard
    data = st.session_state.data
    snapshots = data["snapshots"]
    events = data.get("events", [])
    
    # Calculate metrics
    total_seats = get_total_seats_from_snapshots(snapshots)
    total_tables = get_total_tables_from_snapshots(snapshots)
    
    revpash_df = calculate_revpash(snapshots, total_seats)
    table_util_df = calculate_table_utilization(snapshots, total_tables)
    staff_util_df = calculate_staff_utilization(snapshots)
    station_util_df = calculate_station_utilization(snapshots)
    queue_df = calculate_queue_metrics(snapshots)
    throughput_df = calculate_throughput_metrics(snapshots)
    service_times = calculate_service_times(snapshots)
    summary_stats = calculate_summary_statistics(snapshots)
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 RevPASH & Revenue",
        "⚙️ Utilization",
        "🎬 Animation",
        "📋 Performance Summary"
    ])
    
    # Tab 1: RevPASH & Revenue
    with tab1:
        st.header("Revenue Per Available Seat Hour (RevPASH)")
        
        # KPI cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Current RevPASH",
                f"${summary_stats.get('revpash', 0):.2f}",
                help="Revenue / (Total Seats × Hours)"
            )
        
        with col2:
            st.metric(
                "Total Revenue",
                f"${summary_stats.get('total_revenue', 0):,.2f}"
            )
        
        with col3:
            st.metric(
                "Revenue/Party",
                f"${summary_stats.get('revenue_per_party', 0):.2f}"
            )
        
        with col4:
            st.metric(
                "Parties/Hour",
                f"{summary_stats.get('parties_per_hour', 0):.1f}"
            )
        
        st.markdown("---")
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.plotly_chart(
                plot_revpash_over_time(revpash_df),
                use_container_width=True
            )
        
        with col2:
            st.plotly_chart(
                plot_revenue_accumulation(revpash_df),
                use_container_width=True
            )
    
    # Tab 2: Utilization Dashboard
    with tab2:
        st.header("Utilization Dashboard")
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            avg_table_util = summary_stats.get('avg_table_utilization', 0)
            st.metric(
                "Avg Table Utilization",
                f"{avg_table_util * 100:.1f}%"
            )
        
        with col2:
            avg_station_util = summary_stats.get('avg_station_utilization', 0)
            st.metric(
                "Avg Station Utilization",
                f"{avg_station_util * 100:.1f}%"
            )
        
        with col3:
            st.metric(
                "Total Seats",
                total_seats
            )
        
        st.markdown("---")
        
        # Utilization charts
        st.subheader("Table Utilization")
        st.plotly_chart(
            plot_table_utilization(table_util_df),
            use_container_width=True
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Staff Utilization")
            st.plotly_chart(
                plot_staff_utilization(staff_util_df),
                use_container_width=True
            )
        
        with col2:
            st.subheader("Station Utilization")
            st.plotly_chart(
                plot_station_utilization(station_util_df),
                use_container_width=True
            )
        
        # Heatmaps
        st.subheader("Utilization Heatmaps")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.plotly_chart(
                plot_utilization_heatmap(staff_util_df, "staff"),
                use_container_width=True
            )
        
        with col2:
            st.plotly_chart(
                plot_utilization_heatmap(station_util_df, "station"),
                use_container_width=True
            )
        
        # Queue lengths
        st.subheader("Queue Lengths")
        st.plotly_chart(
            plot_queue_lengths(queue_df),
            use_container_width=True
        )
    
    # Tab 3: Animation
    with tab3:
        st.header("System Animation")
        
        # Get current snapshot
        player = st.session_state.player
        if player:
            player.set_time(st.session_state.current_time)
            current_snapshot = player.get_current_snapshot()
            
            if current_snapshot:
                # Current metrics
                metrics = render_current_metrics(current_snapshot, total_seats)
                
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.metric("Time", metrics.get("time_formatted", "0m"))
                with col2:
                    st.metric("Revenue", f"${metrics.get('revenue', 0):,.2f}")
                with col3:
                    st.metric("RevPASH", f"${metrics.get('revpash', 0):.2f}")
                with col4:
                    st.metric("Table Util", f"{metrics.get('table_utilization', 0) * 100:.0f}%")
                with col5:
                    st.metric("Parties", metrics.get("parties_in_system", 0))
                
                st.markdown("---")
                
                # Restaurant layout
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.subheader("Restaurant Layout")
                    st.plotly_chart(
                        render_restaurant_layout(current_snapshot),
                        use_container_width=True
                    )
                
                with col2:
                    st.subheader("Station Status")
                    st.plotly_chart(
                        render_station_status(current_snapshot, width=400, height=300),
                        use_container_width=True
                    )
                    
                    st.subheader("Queue Status")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("Guest Queue", metrics.get("guest_queue", 0))
                    with col_b:
                        st.metric("Expo Queue", metrics.get("expo_queue", 0))
                
                # Party flow
                st.subheader("Party Flow")
                st.plotly_chart(
                    render_party_flow(current_snapshot),
                    use_container_width=True
                )
            else:
                st.warning("No snapshot data available at this time")
        else:
            st.warning("Animation player not initialized")
        
        # Auto-advance if playing
        if st.session_state.is_playing:
            min_time, max_time = get_time_range(snapshots)
            if st.session_state.current_time < max_time:
                time.sleep(0.1)  # Small delay
                st.session_state.current_time = min(
                    st.session_state.current_time + 1.0,
                    max_time
                )
                st.rerun()
            else:
                st.session_state.is_playing = False
    
    # Tab 4: Performance Summary
    with tab4:
        st.header("Performance Summary")
        
        # Summary statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("Revenue Metrics")
            st.metric("Total Revenue", f"${summary_stats.get('total_revenue', 0):,.2f}")
            st.metric("RevPASH", f"${summary_stats.get('revpash', 0):.2f}")
            st.metric("Revenue/Party", f"${summary_stats.get('revenue_per_party', 0):.2f}")
        
        with col2:
            st.subheader("Throughput Metrics")
            st.metric("Parties Served", summary_stats.get("parties_served", 0))
            st.metric("Parties/Hour", f"{summary_stats.get('parties_per_hour', 0):.1f}")
            st.metric("Duration", f"{summary_stats.get('duration_hours', 0):.1f} hours")
        
        with col3:
            st.subheader("Utilization Metrics")
            st.metric("Avg Table Util", f"{summary_stats.get('avg_table_utilization', 0) * 100:.1f}%")
            st.metric("Avg Station Util", f"{summary_stats.get('avg_station_utilization', 0) * 100:.1f}%")
            st.metric("Total Seats", summary_stats.get("total_seats", 0))
        
        st.markdown("---")
        
        # Throughput chart
        st.subheader("Throughput Over Time")
        st.plotly_chart(
            plot_throughput(throughput_df),
            use_container_width=True
        )
        
        # Service time distributions
        st.subheader("Service Time Distributions")
        
        if service_times:
            st.plotly_chart(
                plot_service_time_distribution(service_times),
                use_container_width=True
            )
            
            # Summary statistics for service times
            col1, col2 = st.columns(2)
            
            with col1:
                if service_times.get("wait_times"):
                    import numpy as np
                    wait_times = service_times["wait_times"]
                    st.markdown("**Wait Times (Arrival to Seating)**")
                    st.write(f"- Mean: {np.mean(wait_times):.1f} min")
                    st.write(f"- Median: {np.median(wait_times):.1f} min")
                    st.write(f"- Max: {np.max(wait_times):.1f} min")
            
            with col2:
                if service_times.get("total_times"):
                    import numpy as np
                    total_times = service_times["total_times"]
                    st.markdown("**Total Times (Arrival to Departure)**")
                    st.write(f"- Mean: {np.mean(total_times):.1f} min")
                    st.write(f"- Median: {np.median(total_times):.1f} min")
                    st.write(f"- Max: {np.max(total_times):.1f} min")
        else:
            st.info("No completed parties in the simulation data")


if __name__ == "__main__":
    main()


