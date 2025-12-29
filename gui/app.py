"""Restaurant Simulation GUI - Main Streamlit Application.

This is the main entry point for the Restaurant Simulation visualization application.
Run with: streamlit run gui/app.py

Features:
- Load JSON log files from the simulation
- Interactive dashboard with RevPASH and utilization metrics
- Animated playback of simulation state
- Performance analysis and summary statistics
"""

import sys
from pathlib import Path
import importlib.util

# CRITICAL: Add experiments directory to path FIRST, before any other imports
# This ensures simulation.py finds experiments/utils.py (which has generate_party_size)
experiments_path = Path(__file__).parent.parent / "experiments"
if str(experiments_path) in sys.path:
    sys.path.remove(str(experiments_path))
sys.path.insert(0, str(experiments_path))

# Also add gui directory for other imports
gui_path = Path(__file__).parent
if str(gui_path) not in sys.path:
    sys.path.append(str(gui_path))

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
try:
    from executive_dashboard import (
        calculate_financial_kpis,
        calculate_service_quality_kpis,
        calculate_operational_kpis,
        render_executive_dashboard,
    )
    from bottleneck_analyzer import (
        analyze_station_bottlenecks,
        analyze_queue_bottlenecks,
        analyze_staff_bottlenecks,
    )
    EXECUTIVE_DASHBOARD_AVAILABLE = True
except ImportError as e:
    EXECUTIVE_DASHBOARD_AVAILABLE = False
    IMPORT_ERROR = str(e)

# Import simulation runner modules
from simulation_runner import (
    run_simulation_with_progress,
    estimate_simulation_runtime,
    list_saved_configs,
)
from session_manager import (
    save_simulation_to_session,
    get_current_simulation,
    list_available_simulations,
    clear_simulation_data,
    get_simulation_summary,
)
from config_ui import render_simulation_config_ui

# Import RAG chatbot components
try:
    from rag import LogProcessor, SimulationVectorStore, RAGChatbot, FactChecker
    from chatbot_ui import render_chatbot_tab
    RAG_AVAILABLE = True
    RAG_IMPORT_ERROR = None
except ImportError as e:
    RAG_AVAILABLE = False
    RAG_IMPORT_ERROR = str(e)
    import traceback
    print(f"⚠️ RAG chatbot unavailable: {RAG_IMPORT_ERROR}")
    print(f"   To enable the chatbot, install dependencies: pip install -r requirements.txt")
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
    plot_dish_flow,
    plot_kitchen_performance,
)
from animation_player import (
    AnimationPlayer,
    render_restaurant_layout,
    render_station_status,
    render_party_flow,
    render_current_metrics,
)

# Load gui/utils.py explicitly to avoid conflict with experiments/utils.py
gui_utils_path = gui_path / "utils.py"
spec = importlib.util.spec_from_file_location("gui_utils", gui_utils_path)
gui_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gui_utils)

# Import required utility functions
get_total_seats_from_snapshots = gui_utils.get_total_seats_from_snapshots
get_total_tables_from_snapshots = gui_utils.get_total_tables_from_snapshots
format_time_display = gui_utils.format_time_display
get_time_range = gui_utils.get_time_range


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
    
    # Initialize RAG components
    if RAG_AVAILABLE:
        if "vector_store" not in st.session_state:
            st.session_state.vector_store = SimulationVectorStore()
        if "rag_chatbot" not in st.session_state:
            st.session_state.rag_chatbot = None
        if "fact_checker" not in st.session_state:
            st.session_state.fact_checker = None
    
    # Sidebar
    with st.sidebar:
        st.title("🍽️ Restaurant Simulation")
        st.markdown("---")
        
        # Display current simulation summary if loaded
        if st.session_state.data is not None:
            st.subheader("📊 Current Simulation")
            
            # Use standardized metrics for consistency
            if "standardized_metrics" in st.session_state:
                std_metrics = st.session_state.standardized_metrics
                duration_hours = std_metrics.get('duration_hours', 0)
                parties_served = std_metrics.get('parties_served', 0)
                total_revenue = std_metrics.get('total_revenue', 0)
            else:
                # Fallback to summary if standardized metrics not yet calculated
                summary = st.session_state.data.get("summary", st.session_state.data.get("metadata", {}))
                duration_hours = summary.get('simulation_duration', 0) / 60
                parties_served = summary.get("num_parties", 0)
                total_revenue = summary.get('total_revenue', 0)
            
            # Get metadata for counts
            metadata = st.session_state.data.get("metadata", {})
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Duration", f"{duration_hours:.1f}h")
                st.metric("Parties", parties_served)
            with col2:
                st.metric("Snapshots", metadata.get("num_snapshots", 0))
                st.metric("Events", metadata.get("num_events", 0))
            
            st.metric("Total Revenue", f"${total_revenue:,.2f}")
            
            # Clear button
            if st.button("🗑️ Clear Simulation", use_container_width=True):
                clear_simulation_data()
                st.rerun()
        else:
            st.info("No simulation loaded. Go to the 'Run Simulation' tab to get started.")
        
        # Show RAG availability status
        st.markdown("---")
        if not RAG_AVAILABLE and RAG_IMPORT_ERROR:
            st.warning(
                f"💬 Chat Assistant unavailable\n\n"
                f"To enable:\n"
                f"`pip install -r requirements.txt`\n\n"
                f"_Error: {RAG_IMPORT_ERROR}_"
            )
    
    # Main content area
    # Always show tabs - Run Simulation tab doesn't require data to be loaded
    
    # Create tabs with Run Simulation as first tab
    if EXECUTIVE_DASHBOARD_AVAILABLE and RAG_AVAILABLE:
        tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "⚙️ Run Simulation",
            "📊 Executive Dashboard",
            "📈 RevPASH & Revenue",
            "🍳 Kitchen",
            "⚙️ Utilization",
            "🎬 Animation",
            "📋 Performance Summary",
            "💬 Chat Assistant"
        ])
    elif EXECUTIVE_DASHBOARD_AVAILABLE:
        tab0, tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "⚙️ Run Simulation",
            "📊 Executive Dashboard",
            "📈 RevPASH & Revenue",
            "🍳 Kitchen",
            "⚙️ Utilization",
            "🎬 Animation",
            "📋 Performance Summary"
        ])
    elif RAG_AVAILABLE:
        tab0, tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "⚙️ Run Simulation",
            "📈 RevPASH & Revenue",
            "🍳 Kitchen",
            "⚙️ Utilization",
            "🎬 Animation",
            "📋 Performance Summary",
            "💬 Chat Assistant"
        ])
    else:
        tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "⚙️ Run Simulation",
            "📈 RevPASH & Revenue",
            "🍳 Kitchen",
            "⚙️ Utilization",
            "🎬 Animation",
            "📋 Performance Summary"
        ])
    
    # Tab 0: Run Simulation
    with tab0:
        st.header("🚀 Run Simulation")
        st.markdown("Configure and run restaurant simulations directly in the GUI")
        
        # Check if recommended config exists
        if 'recommended_config' in st.session_state and st.session_state.recommended_config is not None:
            st.info("📋 Recommended configuration loaded from bottleneck analysis")
            if st.button("Clear Recommended Config"):
                st.session_state.recommended_config = None
                st.rerun()
        
        # Render configuration UI
        params = render_simulation_config_ui()
        
        if params is not None:
            st.markdown("---")
            
            # Estimate runtime
            estimated_time = estimate_simulation_runtime(params)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Estimated Runtime", f"{estimated_time:.1f}s")
            with col2:
                st.metric("Simulation Duration", f"{params.simulation_duration} min")
            with col3:
                st.metric("Total Staff", params.num_servers + params.num_cooks + params.num_hosts + params.num_food_runners + params.num_bussers)
            
            st.markdown("---")
            
            # Run button
            if st.button("▶️ Run Simulation", type="primary", use_container_width=True):
                try:
                    # Progress tracking
                    progress_bar = st.progress(0.0)
                    status_text = st.empty()
                    
                    def update_progress(progress: float, status: str):
                        progress_bar.progress(progress)
                        status_text.text(status)
                    
                    # Run simulation
                    with st.spinner("Running simulation..."):
                        result = run_simulation_with_progress(params, update_progress)
                    
                    if result['success']:
                        # Store results in session state
                        st.session_state.data = result['log_data']
                        st.session_state.player = AnimationPlayer(result['log_data']['snapshots'])
                        st.session_state.current_time = 0.0
                        st.session_state.metrics_stale = True  # Mark metrics as needing recalculation
                        
                        # Process for RAG if available
                        if RAG_AVAILABLE:
                            try:
                                with st.spinner("Processing simulation for chatbot..."):
                                    processor = LogProcessor()
                                    chunks = processor.process_log(result['log_data'])
                                    
                                    # Clear and add to vector store
                                    st.session_state.vector_store.clear()
                                    st.session_state.vector_store.add_log_chunks(chunks)
                                    
                                    # Calculate metrics for fact-checking (will be stored in session_state)
                                    # This happens later when metrics are calculated
                                    st.session_state.fact_checker = None  # Will be initialized when metrics are ready
                                    
                                    # Initialize chatbot (fact_checker added later)
                                    st.session_state.rag_chatbot = RAGChatbot(st.session_state.vector_store)
                            except Exception as e:
                                st.warning(f"Chatbot initialization failed: {e}")
                        
                        # Save to session
                        save_simulation_to_session(
                            result['log_data'],
                            params,
                            label=f"Simulation {len(list_available_simulations()) + 1}"
                        )
                        
                        # Success message
                        st.success(f"✅ Simulation complete! ({result['elapsed_time']:.1f}s)")
                        st.balloons()
                        
                        # Show summary
                        st.subheader("📊 Results Summary")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Parties Served", result['log_data']['metadata']['num_parties'])
                        with col2:
                            st.metric("Total Revenue", f"${result['log_data']['metadata']['total_revenue']:,.2f}")
                        with col3:
                            st.metric("Snapshots", result['log_data']['metadata']['num_snapshots'])
                        with col4:
                            st.metric("Duration", f"{params.simulation_duration} min")
                        
                        st.info("👈 View results in the other tabs!")
                        
                except Exception as e:
                    st.error(f"❌ Simulation failed: {str(e)}")
                    st.exception(e)
        else:
            st.warning("⚠️ Please complete the configuration above to run a simulation")
    
    # Only show data tabs if simulation has been run
    if st.session_state.data is None:
        # Show placeholder in other tabs
        for tab in ([tab1, tab2, tab3, tab4, tab5, tab6] if EXECUTIVE_DASHBOARD_AVAILABLE else [tab1, tab2, tab3, tab4, tab5]):
            with tab:
                st.info("👈 No simulation data loaded. Go to 'Run Simulation' tab to get started!")
        return
    
    # Data is loaded - show dashboard
    data = st.session_state.data
    snapshots = data["snapshots"]
    events = data.get("events", [])
    
    # Calculate metrics
    total_seats = get_total_seats_from_snapshots(snapshots)
    total_tables = get_total_tables_from_snapshots(snapshots)
    
    # Calculate standardized summary statistics for consistency
    if "standardized_metrics" not in st.session_state or st.session_state.get("metrics_stale", True):
        summary_stats = calculate_summary_statistics(snapshots)
        st.session_state.standardized_metrics = summary_stats
        st.session_state.metrics_stale = False
        
        # Initialize/update fact checker with standardized metrics for RAG
        if RAG_AVAILABLE and st.session_state.rag_chatbot is not None:
            try:
                st.session_state.fact_checker = FactChecker(summary_stats)
                # Update chatbot's fact_checker
                st.session_state.rag_chatbot.fact_checker = st.session_state.fact_checker
            except Exception as e:
                print(f"Failed to initialize fact checker: {e}")
    else:
        summary_stats = st.session_state.standardized_metrics
    
    revpash_df = calculate_revpash(snapshots, total_seats)
    table_util_df = calculate_table_utilization(snapshots, total_tables)
    staff_util_df = calculate_staff_utilization(snapshots)
    station_util_df = calculate_station_utilization(snapshots)
    queue_df = calculate_queue_metrics(snapshots)
    throughput_df = calculate_throughput_metrics(snapshots)
    service_times = calculate_service_times(snapshots)
    summary_stats = calculate_summary_statistics(snapshots)
    
    # Render tabs based on availability
    if EXECUTIVE_DASHBOARD_AVAILABLE:
        # Tab 1: Executive Dashboard
        with tab1:
            try:
                # Calculate all KPIs
                financial_kpis = calculate_financial_kpis(snapshots, data.get("metadata", {}))
                service_kpis = calculate_service_quality_kpis(snapshots)
                operational_kpis = calculate_operational_kpis(snapshots, table_util_df, station_util_df, staff_util_df)
                
                # Identify bottlenecks
                station_bottlenecks = analyze_station_bottlenecks(station_util_df, queue_df)
                queue_bottlenecks = analyze_queue_bottlenecks(queue_df)
                staff_bottlenecks = analyze_staff_bottlenecks(staff_util_df)
                
                # Render dashboard
                render_executive_dashboard(
                    data=data,
                    financial_kpis=financial_kpis,
                    service_kpis=service_kpis,
                    operational_kpis=operational_kpis,
                    bottlenecks={
                        'stations': station_bottlenecks,
                        'queues': queue_bottlenecks,
                        'staff': staff_bottlenecks
                    }
                )
            except Exception as e:
                st.error(f"Error loading Executive Dashboard: {str(e)}")
                st.exception(e)
                st.info("Other tabs should still work. Please check the error above.")
        
        # Tab 2: RevPASH & Revenue
        with tab2:
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
    else:
        # Tab 1: RevPASH & Revenue (when Executive Dashboard not available)
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
    
    # Tab 3 (or 2): Kitchen Performance
    tab_kitchen = tab3 if EXECUTIVE_DASHBOARD_AVAILABLE else tab2
    with tab_kitchen:
        st.header("Kitchen Performance")
        
        # Kitchen KPIs
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Avg Kitchen Time",
                f"{summary_stats.get('avg_kitchen_time', 0):.1f} min",
                help="Average time from order to all dishes ready at expo"
            )
        
        with col2:
            st.metric(
                "Avg Order to Delivery",
                f"{summary_stats.get('avg_order_to_delivery', 0):.1f} min",
                help="Average time from order complete to first dish delivered"
            )
        
        with col3:
            st.metric(
                "Total Dishes",
                f"{summary_stats.get('total_dishes', 0)}"
            )
        
        with col4:
            st.metric(
                "Dishes/Hour",
                f"{summary_stats.get('dishes_per_hour', 0):.1f}"
            )
        
        st.markdown("---")
        
        # Station utilization and queues
        st.subheader("Station Performance")
        st.plotly_chart(
            plot_kitchen_performance(station_util_df),
            use_container_width=True
        )
        
        # Dish flow
        st.subheader("Dish Flow Through System")
        st.plotly_chart(
            plot_dish_flow(throughput_df),
            use_container_width=True
        )
        
        # Station queues
        st.subheader("Station Queue Depths")
        st.plotly_chart(
            plot_station_queues(queue_df),
            use_container_width=True
        )
    
    # Tab 4 (or 3): Utilization Dashboard
    tab_util = tab4 if EXECUTIVE_DASHBOARD_AVAILABLE else tab3
    with tab_util:
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
    
    # Tab 5 (or 4): Animation
    tab_anim = tab5 if EXECUTIVE_DASHBOARD_AVAILABLE else tab4
    with tab_anim:
        st.header("System Animation")
        
        # Playback controls at the top of the animation tab
        st.subheader("🎬 Playback Controls")
        
        min_time, max_time = get_time_range(snapshots)
        
        # Time slider
        st.session_state.current_time = st.slider(
            "Time",
            min_value=float(min_time),
            max_value=float(max_time),
            value=st.session_state.current_time,
            format="%.1f min",
            key="time_slider",
        )
        
        # Control buttons
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("⏮️ Start", use_container_width=True):
                st.session_state.current_time = min_time
                st.rerun()
        with col2:
            play_text = "⏸️ Pause" if st.session_state.is_playing else "▶️ Play"
            if st.button(play_text, use_container_width=True):
                st.session_state.is_playing = not st.session_state.is_playing
                st.rerun()
        with col3:
            if st.button("⏭️ End", use_container_width=True):
                st.session_state.current_time = max_time
                st.rerun()
        with col4:
            # Initialize playback speed in session state
            if 'playback_speed' not in st.session_state:
                st.session_state.playback_speed = 1.0
            
            playback_speed = st.selectbox(
                "Speed",
                options=[0.5, 1.0, 2.0, 5.0, 10.0],
                index=[0.5, 1.0, 2.0, 5.0, 10.0].index(st.session_state.playback_speed),
                format_func=lambda x: f"{x}x",
            )
            st.session_state.playback_speed = playback_speed
        
        st.markdown("---")
        
        # Get current snapshot
        player = st.session_state.player
        if player:
            player.set_time(st.session_state.current_time)
            current_snapshot = player.get_current_snapshot()
            
            if current_snapshot:
                # Current metrics - expanded row
                metrics = render_current_metrics(current_snapshot, total_seats)
                
                col1, col2, col3, col4, col5, col6 = st.columns(6)
                
                with col1:
                    st.metric("Time", metrics.get("time_formatted", "0m"))
                with col2:
                    st.metric("Revenue", f"${metrics.get('revenue', 0):,.2f}")
                with col3:
                    st.metric("RevPASH", f"${metrics.get('revpash', 0):.2f}")
                with col4:
                    st.metric("Table Util", f"{metrics.get('table_utilization', 0) * 100:.0f}%")
                with col5:
                    st.metric("Station Util", f"{metrics.get('station_utilization', 0) * 100:.0f}%")
                with col6:
                    st.metric("Parties", metrics.get("parties_in_system", 0))
                
                # Dish status row
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("🍳 Cooking", metrics.get("dishes_cooking", 0))
                with col2:
                    st.metric("✅ Ready", metrics.get("dishes_ready", 0))
                with col3:
                    st.metric("🚀 Deliveries", metrics.get("active_deliveries", 0))
                with col4:
                    st.metric("🍽️ Delivered", metrics.get("dishes_delivered", 0))
                
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
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Guest", metrics.get("guest_queue", 0))
                    with col_b:
                        st.metric("Expo", metrics.get("expo_queue", 0))
                    with col_c:
                        st.metric("Runners", metrics.get("food_runner_queue", 0))
                
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
                # Calculate time increment based on playback speed
                # Base increment: 0.5 minutes per rerun
                base_increment = 0.5
                time_increment = base_increment * st.session_state.playback_speed
                
                st.session_state.current_time = min(
                    st.session_state.current_time + time_increment,
                    max_time
                )
                st.rerun()
            else:
                st.session_state.is_playing = False
    
    # Tab 6 (or 5): Performance Summary
    tab_summary = tab6 if EXECUTIVE_DASHBOARD_AVAILABLE else tab5
    with tab_summary:
        st.header("Performance Summary")
        
        # Summary statistics - expanded to 4 columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.subheader("Revenue Metrics")
            st.metric("Total Revenue", f"${summary_stats.get('total_revenue', 0):,.2f}")
            st.metric("RevPASH", f"${summary_stats.get('revpash', 0):.2f}")
            st.metric("Revenue/Party", f"${summary_stats.get('revenue_per_party', 0):.2f}")
        
        with col2:
            st.subheader("Throughput Metrics")
            st.metric("Parties Served", summary_stats.get("parties_served", 0))
            st.metric("Parties/Hour", f"{summary_stats.get('parties_per_hour', 0):.1f}")
            st.metric("Dishes/Hour", f"{summary_stats.get('dishes_per_hour', 0):.1f}")
        
        with col3:
            st.subheader("Kitchen Timing")
            st.metric("Avg Kitchen Time", f"{summary_stats.get('avg_kitchen_time', 0):.1f} min")
            st.metric("Avg Order→Delivery", f"{summary_stats.get('avg_order_to_delivery', 0):.1f} min")
            st.metric("Avg Dining Time", f"{summary_stats.get('avg_dining_time', 0):.1f} min")
        
        with col4:
            st.subheader("Utilization")
            st.metric("Avg Table Util", f"{summary_stats.get('avg_table_utilization', 0) * 100:.1f}%")
            st.metric("Avg Station Util", f"{summary_stats.get('avg_station_utilization', 0) * 100:.1f}%")
            st.metric("Duration", f"{summary_stats.get('duration_hours', 0):.1f} hours")
        
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
            
            # Summary statistics for service times - expanded to 4 columns
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if service_times.get("wait_times"):
                    import numpy as np
                    wait_times = service_times["wait_times"]
                    st.markdown("**Wait Times**")
                    st.write(f"Mean: {np.mean(wait_times):.1f} min")
                    st.write(f"Median: {np.median(wait_times):.1f} min")
                    st.write(f"Max: {np.max(wait_times):.1f} min")
            
            with col2:
                if service_times.get("kitchen_times"):
                    import numpy as np
                    kitchen_times = service_times["kitchen_times"]
                    st.markdown("**Kitchen Times**")
                    st.write(f"Mean: {np.mean(kitchen_times):.1f} min")
                    st.write(f"Median: {np.median(kitchen_times):.1f} min")
                    st.write(f"Max: {np.max(kitchen_times):.1f} min")
            
            with col3:
                if service_times.get("dining_times"):
                    import numpy as np
                    dining_times = service_times["dining_times"]
                    st.markdown("**Dining Times**")
                    st.write(f"Mean: {np.mean(dining_times):.1f} min")
                    st.write(f"Median: {np.median(dining_times):.1f} min")
                    st.write(f"Max: {np.max(dining_times):.1f} min")
            
            with col4:
                if service_times.get("total_times"):
                    import numpy as np
                    total_times = service_times["total_times"]
                    st.markdown("**Total Times**")
                    st.write(f"Mean: {np.mean(total_times):.1f} min")
                    st.write(f"Median: {np.median(total_times):.1f} min")
                    st.write(f"Max: {np.max(total_times):.1f} min")
        else:
            st.info("No completed parties in the simulation data")
    
    # Chat Assistant Tab (if available)
    if RAG_AVAILABLE:
        if EXECUTIVE_DASHBOARD_AVAILABLE:
            tab_chat = tab7
        else:
            tab_chat = tab6
        
        with tab_chat:
            render_chatbot_tab()


if __name__ == "__main__":
    main()


