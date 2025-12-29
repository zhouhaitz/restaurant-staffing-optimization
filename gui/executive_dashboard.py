"""Executive Dashboard for Restaurant Simulation.

This module provides high-level KPIs and visualizations for chef/owner decision-making,
including financial metrics, service quality indicators, and bottleneck identification.
"""

from typing import Dict, List, Any
import pandas as pd
import numpy as np
import streamlit as st
import sys
from pathlib import Path
import importlib.util

# Load gui/utils.py and gui/metrics_calculator.py explicitly
gui_path = Path(__file__).parent

# Load utils
gui_utils_path = gui_path / "utils.py"
spec = importlib.util.spec_from_file_location("gui_utils", gui_utils_path)
gui_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gui_utils)

# Load metrics_calculator
metrics_calc_path = gui_path / "metrics_calculator.py"
spec = importlib.util.spec_from_file_location("gui_metrics", metrics_calc_path)
gui_metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gui_metrics)

# Import required functions
convert_minutes_to_hours = gui_utils.convert_minutes_to_hours
get_total_seats_from_snapshots = gui_utils.get_total_seats_from_snapshots
get_total_tables_from_snapshots = gui_utils.get_total_tables_from_snapshots
safe_divide = gui_utils.safe_divide
extract_staff_config_from_metadata = gui_utils.extract_staff_config_from_metadata
calculate_service_times = gui_metrics.calculate_service_times
calculate_percentile_times = gui_metrics.calculate_percentile_times

# Import dashboard visualizations
try:
    from dashboard_visualizations import (
        plot_financial_overview,
        plot_service_quality_breakdown,
        plot_operational_efficiency,
        plot_bottleneck_severity,
        create_metrics_table,
    )
    DASHBOARD_VIZ_AVAILABLE = True
except ImportError:
    DASHBOARD_VIZ_AVAILABLE = False


# Standard hourly wages (fallback if not in metadata)
DEFAULT_WAGES = {
    'server_hourly_wage': 34.73,
    'cook_hourly_wage': 22.60,
    'host_hourly_wage': 20.40,
    'food_runner_hourly_wage': 21.80,
    'busser_hourly_wage': 25.00
}


def calculate_financial_kpis(snapshots: List[Dict], metadata: Dict) -> Dict[str, float]:
    """Calculate financial KPIs including revenue and labor costs.
    
    Args:
        snapshots: List of snapshot dictionaries
        metadata: Simulation metadata including staff configuration
        
    Returns:
        Dictionary of financial KPIs
    """
    if not snapshots:
        return {}
    
    last_snapshot = snapshots[-1]
    first_snapshot = snapshots[0]
    
    # Basic metrics
    total_revenue = last_snapshot.get('total_revenue', 0)
    parties_served = last_snapshot.get('parties_served', 0)
    
    # Time calculation
    start_time = first_snapshot.get('time', 0)
    end_time = last_snapshot.get('time', 0)
    duration_hours = convert_minutes_to_hours(end_time - start_time)
    
    # Seat calculation
    total_seats = get_total_seats_from_snapshots(snapshots)
    seat_hours = total_seats * duration_hours if duration_hours > 0 else 0
    
    # Extract staff configuration and wages
    staff_config = extract_staff_config_from_metadata(metadata)
    wages = metadata.get('wages', DEFAULT_WAGES)
    
    # Calculate labor costs
    total_labor_cost = 0.0
    if duration_hours > 0:
        total_labor_cost += staff_config.get('num_servers', 0) * duration_hours * wages.get('server_hourly_wage', DEFAULT_WAGES['server_hourly_wage'])
        total_labor_cost += staff_config.get('num_cooks', 0) * duration_hours * wages.get('cook_hourly_wage', DEFAULT_WAGES['cook_hourly_wage'])
        total_labor_cost += staff_config.get('num_hosts', 0) * duration_hours * wages.get('host_hourly_wage', DEFAULT_WAGES['host_hourly_wage'])
        total_labor_cost += staff_config.get('num_food_runners', 0) * duration_hours * wages.get('food_runner_hourly_wage', DEFAULT_WAGES['food_runner_hourly_wage'])
        total_labor_cost += staff_config.get('num_bussers', 0) * duration_hours * wages.get('busser_hourly_wage', DEFAULT_WAGES['busser_hourly_wage'])
    
    # Calculate KPIs
    gross_revpash = safe_divide(total_revenue, seat_hours, 0.0)
    net_revpash = safe_divide(total_revenue - total_labor_cost, seat_hours, 0.0)
    labor_cost_percentage = safe_divide(total_labor_cost, total_revenue, 0.0) * 100
    revenue_per_party = safe_divide(total_revenue, parties_served, 0.0)
    cost_per_party = safe_divide(total_labor_cost, parties_served, 0.0)
    labor_cost_per_hour = safe_divide(total_labor_cost, duration_hours, 0.0)
    
    return {
        'total_revenue': total_revenue,
        'total_labor_cost': total_labor_cost,
        'net_revpash': net_revpash,
        'gross_revpash': gross_revpash,
        'labor_cost_percentage': labor_cost_percentage,
        'revenue_per_party': revenue_per_party,
        'cost_per_party': cost_per_party,
        'labor_cost_per_hour': labor_cost_per_hour,
        'duration_hours': duration_hours,
        'parties_served': parties_served,
    }


def calculate_service_quality_kpis(snapshots: List[Dict]) -> Dict[str, float]:
    """Calculate service quality KPIs.
    
    Args:
        snapshots: List of snapshot dictionaries
        
    Returns:
        Dictionary of service quality KPIs
    """
    if not snapshots:
        return {}
    
    # Get service times
    service_times = calculate_service_times(snapshots)
    
    # Calculate averages
    avg_wait_time = np.mean(service_times.get('wait_times', [0])) if service_times.get('wait_times') else 0
    avg_kitchen_time = np.mean(service_times.get('kitchen_times', [0])) if service_times.get('kitchen_times') else 0
    avg_order_to_delivery = np.mean(service_times.get('order_to_delivery_times', [0])) if service_times.get('order_to_delivery_times') else 0
    avg_dining_time = np.mean(service_times.get('dining_times', [0])) if service_times.get('dining_times') else 0
    avg_total_time = np.mean(service_times.get('total_times', [0])) if service_times.get('total_times') else 0
    
    # Calculate percentiles
    percentiles = calculate_percentile_times(service_times, 95)
    p95_wait_time = percentiles.get('wait_times_p95', 0)
    p95_kitchen_time = percentiles.get('kitchen_times_p95', 0)
    
    # Calculate service quality score (0-100)
    # Based on wait time, kitchen time, and order-to-delivery time
    # Lower times = higher score
    wait_score = max(0, 100 - (avg_wait_time / 15.0 * 100))  # 15 min = 0 score
    kitchen_score = max(0, 100 - (avg_kitchen_time / 20.0 * 100))  # 20 min = 0 score
    delivery_score = max(0, 100 - (avg_order_to_delivery / 10.0 * 100))  # 10 min = 0 score
    
    service_quality_score = (wait_score * 0.3 + kitchen_score * 0.4 + delivery_score * 0.3)
    
    return {
        'avg_wait_time': avg_wait_time,
        'avg_kitchen_time': avg_kitchen_time,
        'avg_order_to_delivery': avg_order_to_delivery,
        'avg_dining_time': avg_dining_time,
        'avg_total_time': avg_total_time,
        'p95_wait_time': p95_wait_time,
        'p95_kitchen_time': p95_kitchen_time,
        'service_quality_score': service_quality_score,
    }


def calculate_operational_kpis(snapshots: List[Dict], table_util_df: pd.DataFrame, 
                                station_util_df: pd.DataFrame, staff_util_df: pd.DataFrame) -> Dict[str, float]:
    """Calculate operational efficiency KPIs.
    
    Args:
        snapshots: List of snapshot dictionaries
        table_util_df: DataFrame with table utilization
        station_util_df: DataFrame with station utilization
        staff_util_df: DataFrame with staff utilization
        
    Returns:
        Dictionary of operational KPIs
    """
    if not snapshots:
        return {}
    
    last_snapshot = snapshots[-1]
    first_snapshot = snapshots[0]
    
    # Time calculation
    start_time = first_snapshot.get('time', 0)
    end_time = last_snapshot.get('time', 0)
    duration_hours = convert_minutes_to_hours(end_time - start_time)
    
    # Basic metrics
    parties_served = last_snapshot.get('parties_served', 0)
    total_tables = get_total_tables_from_snapshots(snapshots)
    
    # Calculate averages from DataFrames
    avg_table_utilization = table_util_df['utilization'].mean() if not table_util_df.empty and 'utilization' in table_util_df.columns else 0
    avg_station_utilization = station_util_df['overall_station_utilization'].mean() if not station_util_df.empty and 'overall_station_utilization' in station_util_df.columns else 0
    avg_staff_utilization = staff_util_df['overall_utilization'].mean() if not staff_util_df.empty and 'overall_utilization' in staff_util_df.columns else 0
    
    # Calculate rates
    table_turnover_rate = safe_divide(parties_served, total_tables * duration_hours, 0.0)
    parties_per_hour = safe_divide(parties_served, duration_hours, 0.0)
    
    # Calculate service rate (parties served / parties arrived)
    # Estimate parties arrived from served + current in system
    parties_in_system = last_snapshot.get('parties_in_system', 0)
    parties_arrived = parties_served + parties_in_system
    service_rate = safe_divide(parties_served, parties_arrived, 0.0)
    
    # Dishes metrics
    dishes = last_snapshot.get('dishes', [])
    dishes_delivered = sum(1 for d in dishes if d.get('status') == 'delivered')
    dishes_per_hour = safe_divide(dishes_delivered, duration_hours, 0.0)
    
    return {
        'avg_table_utilization': avg_table_utilization,
        'avg_station_utilization': avg_station_utilization,
        'avg_staff_utilization': avg_staff_utilization,
        'table_turnover_rate': table_turnover_rate,
        'service_rate': service_rate,
        'parties_per_hour': parties_per_hour,
        'dishes_per_hour': dishes_per_hour,
        'total_tables': total_tables,
    }


def render_executive_dashboard(data: Dict, financial_kpis: Dict[str, float], 
                                service_kpis: Dict[str, float], operational_kpis: Dict[str, float],
                                bottlenecks: Dict[str, List[Dict[str, Any]]]):
    """Render the executive dashboard with KPIs and bottleneck alerts.
    
    Args:
        data: Full simulation data
        financial_kpis: Financial metrics
        service_kpis: Service quality metrics
        operational_kpis: Operational efficiency metrics
        bottlenecks: Bottleneck analysis results
    """
    st.header("📊 Executive Dashboard")
    st.markdown("**Real-time operational intelligence for restaurant decision-making**")
    st.markdown("---")
    
    # Top section: 4 primary KPI cards
    st.subheader("Key Performance Indicators")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        net_revpash = financial_kpis.get('net_revpash', 0)
        gross_revpash = financial_kpis.get('gross_revpash', 0)
        delta = net_revpash - gross_revpash
        st.metric(
            "Net RevPASH",
            f"${net_revpash:.2f}",
            delta=f"${delta:.2f} vs Gross",
            delta_color="inverse" if delta < 0 else "normal",
            help="Revenue Per Seat Hour after labor costs - your true profitability metric"
        )
    
    with col2:
        total_revenue = financial_kpis.get('total_revenue', 0)
        labor_pct = financial_kpis.get('labor_cost_percentage', 0)
        st.metric(
            "Total Revenue",
            f"${total_revenue:,.2f}",
            delta=f"{labor_pct:.1f}% labor",
            delta_color="inverse" if labor_pct > 35 else "normal",
            help="Total revenue generated - labor cost shown as percentage (target: <35%)"
        )
    
    with col3:
        service_score = service_kpis.get('service_quality_score', 0)
        # Determine if score is good (>70), ok (50-70), or poor (<50)
        if service_score >= 70:
            delta_color = "normal"
            score_desc = "Excellent"
        elif service_score >= 50:
            delta_color = "off"
            score_desc = "Good"
        else:
            delta_color = "inverse"
            score_desc = "Needs Attention"
        
        st.metric(
            "Service Quality",
            f"{service_score:.0f}/100",
            delta=score_desc,
            delta_color=delta_color,
            help="Composite score based on wait times and kitchen performance (70+ is excellent)"
        )
    
    with col4:
        turnover = operational_kpis.get('table_turnover_rate', 0)
        target_turnover = 2.0  # Target: 2 parties per table per hour
        turnover_delta = turnover - target_turnover
        st.metric(
            "Table Turnover",
            f"{turnover:.2f}/hr",
            delta=f"{turnover_delta:+.2f} vs target",
            delta_color="normal" if turnover_delta >= 0 else "inverse",
            help="Parties served per table per hour (target: 2.0)"
        )
    
    st.markdown("---")
    
    # Middle section: Bottleneck Alerts
    st.subheader("🚨 Bottleneck Analysis")
    
    # Get overall health status
    try:
        from bottleneck_analyzer import get_overall_health_status, generate_recommendations
    except ImportError:
        try:
            from .bottleneck_analyzer import get_overall_health_status, generate_recommendations
        except ImportError:
            # Fallback if import fails
            def get_overall_health_status(bottlenecks):
                return ("Unknown", "❓")
            def generate_recommendations(bottlenecks):
                return ["Unable to generate recommendations - import error"]
    
    health_status, health_icon = get_overall_health_status(bottlenecks)
    
    # Display overall health with colored background
    if health_status == "Critical":
        st.error(f"### {health_icon} System Status: {health_status}")
        st.markdown("**Immediate attention required** - Critical bottlenecks are impacting operations")
    elif health_status in ["Warning", "Caution"]:
        st.warning(f"### {health_icon} System Status: {health_status}")
        st.markdown("**Monitor closely** - Some bottlenecks identified that may impact performance")
    else:
        st.success(f"### {health_icon} System Status: {health_status}")
        st.markdown("**Operating smoothly** - All systems within normal parameters")
    
    st.markdown("")
    
    # Display recommendations in an attractive format
    recommendations = generate_recommendations(bottlenecks)
    if recommendations:
        st.markdown("### 💡 Top Recommendations")
        
        # Create a nice box for recommendations
        rec_text = "\n".join([f"- {rec}" for rec in recommendations[:5]])
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 15px; border-radius: 5px; border-left: 5px solid #ff4b4b;">
        {rec_text.replace('\n', '<br>')}
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Main Content: Tabbed Interface
    main_tab1, main_tab2, main_tab3, main_tab4 = st.tabs([
        "💰 Financial Overview",
        "⏱️ Service Quality",
        "⚙️ Operational Efficiency",
        "🚨 Bottleneck Analysis"
    ])
    
    # Tab 1: Financial Overview
    with main_tab1:
        st.subheader("Financial Performance")
        if DASHBOARD_VIZ_AVAILABLE:
            try:
                from metrics_calculator import calculate_revpash
                from utils import get_total_seats_from_snapshots
                
                snapshots = data.get('snapshots', [])
                if snapshots:
                    total_seats = get_total_seats_from_snapshots(snapshots)
                    revpash_df = calculate_revpash(snapshots, total_seats)
                    st.plotly_chart(plot_financial_overview(financial_kpis, revpash_df), use_container_width=True)
            except Exception as e:
                st.warning(f"Could not generate charts: {e}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Gross RevPASH", f"${financial_kpis.get('gross_revpash', 0):.2f}")
            st.metric("Net RevPASH", f"${financial_kpis.get('net_revpash', 0):.2f}")
        with col2:
            st.metric("Total Labor Cost", f"${financial_kpis.get('total_labor_cost', 0):,.2f}")
            st.metric("Labor Cost %", f"{financial_kpis.get('labor_cost_percentage', 0):.1f}%")
        with col3:
            st.metric("Revenue/Party", f"${financial_kpis.get('revenue_per_party', 0):.2f}")
            st.metric("Labor Cost/Party", f"${financial_kpis.get('cost_per_party', 0):.2f}")
    
    # Tab 2: Service Quality
    with main_tab2:
        st.subheader("Service Quality Performance")
        if DASHBOARD_VIZ_AVAILABLE:
            try:
                from metrics_calculator import calculate_service_times
                snapshots = data.get('snapshots', [])
                if snapshots:
                    service_times = calculate_service_times(snapshots)
                    st.plotly_chart(plot_service_quality_breakdown(service_kpis, service_times), use_container_width=True)
            except Exception as e:
                st.warning(f"Could not generate charts: {e}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Service Quality Score", f"{service_kpis.get('service_quality_score', 0):.0f}/100")
            st.metric("Avg Wait Time", f"{service_kpis.get('avg_wait_time', 0):.1f} min")
        with col2:
            st.metric("Avg Kitchen Time", f"{service_kpis.get('avg_kitchen_time', 0):.1f} min")
            st.metric("95th % Kitchen Time", f"{service_kpis.get('p95_kitchen_time', 0):.1f} min")
        with col3:
            st.metric("Avg Order→Delivery", f"{service_kpis.get('avg_order_to_delivery', 0):.1f} min")
            st.metric("Avg Total Time", f"{service_kpis.get('avg_total_time', 0):.1f} min")
    
    # Tab 3: Operational Efficiency
    with main_tab3:
        st.subheader("Operational Efficiency")
        if DASHBOARD_VIZ_AVAILABLE:
            try:
                from metrics_calculator import calculate_queue_metrics
                snapshots = data.get('snapshots', [])
                if snapshots:
                    queue_df = calculate_queue_metrics(snapshots)
                    st.plotly_chart(plot_operational_efficiency(operational_kpis, queue_df), use_container_width=True)
            except Exception as e:
                st.warning(f"Could not generate charts: {e}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Table Utilization", f"{operational_kpis.get('avg_table_utilization', 0)*100:.1f}%")
            st.metric("Station Utilization", f"{operational_kpis.get('avg_station_utilization', 0)*100:.1f}%")
        with col2:
            st.metric("Table Turnover Rate", f"{operational_kpis.get('table_turnover_rate', 0):.2f}/hr")
            st.metric("Service Rate", f"{operational_kpis.get('service_rate', 0)*100:.1f}%")
        with col3:
            st.metric("Parties/Hour", f"{operational_kpis.get('parties_per_hour', 0):.1f}")
            st.metric("Dishes/Hour", f"{operational_kpis.get('dishes_per_hour', 0):.1f}")
    
    # Tab 4: Bottleneck Analysis
    with main_tab4:
        st.subheader("Bottleneck Analysis")
        if DASHBOARD_VIZ_AVAILABLE:
            try:
                st.plotly_chart(plot_bottleneck_severity(bottlenecks), use_container_width=True)
            except Exception as e:
                st.warning(f"Could not generate chart: {e}")
        
        # Detailed bottleneck tabs
        subtab1, subtab2, subtab3 = st.tabs(["🍳 Kitchen Stations", "📋 System Queues", "👥 Staff"])
        
        with subtab1:
            station_bottlenecks = bottlenecks.get('stations', [])
            if station_bottlenecks:
                for i, bottleneck in enumerate(station_bottlenecks):
                    severity = bottleneck['severity']
                    
                    # Color code based on severity
                    if severity == "critical":
                        color = "#ff4b4b"
                        icon = "🔴"
                        badge = "CRITICAL"
                    elif severity == "warning":
                        color = "#ffa500"
                        icon = "🟡"
                        badge = "WARNING"
                    else:
                        color = "#00cc00"
                        icon = "🟢"
                        badge = "HEALTHY"
                    
                    # Create nice card for each bottleneck
                    st.markdown(f"""
                    <div style="background-color: #f8f9fa; padding: 12px; border-radius: 5px; 
                                border-left: 4px solid {color}; margin-bottom: 10px;">
                        <strong>{icon} {bottleneck['station_name']}</strong> 
                        <span style="background-color: {color}; color: white; padding: 2px 8px; 
                                     border-radius: 3px; font-size: 11px; margin-left: 8px;">{badge}</span>
                        <br><br>
                        <strong>Bottleneck Score:</strong> {bottleneck['score']:.2f}/1.0<br>
                        <strong>Utilization:</strong> {bottleneck['avg_utilization']*100:.0f}%<br>
                        <strong>Avg Queue Length:</strong> {bottleneck['avg_queue_length']:.1f}<br>
                        <br>
                        <em>{bottleneck['recommendation']}</em>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("✓ No station bottlenecks detected - all kitchen stations operating efficiently")
        
        with subtab2:
            queue_bottlenecks = bottlenecks.get('queues', [])
            if queue_bottlenecks:
                for bottleneck in queue_bottlenecks:
                    severity = bottleneck['severity']
                    
                    if severity == "critical":
                        color = "#ff4b4b"
                        icon = "🔴"
                        badge = "CRITICAL"
                    else:
                        color = "#ffa500"
                        icon = "🟡"
                        badge = "WARNING"
                    
                    st.markdown(f"""
                    <div style="background-color: #f8f9fa; padding: 12px; border-radius: 5px; 
                                border-left: 4px solid {color}; margin-bottom: 10px;">
                        <strong>{icon} {bottleneck['queue_name']}</strong>
                        <span style="background-color: {color}; color: white; padding: 2px 8px; 
                                     border-radius: 3px; font-size: 11px; margin-left: 8px;">{badge}</span>
                        <br><br>
                        <strong>Average Length:</strong> {bottleneck['avg_length']:.1f} customers<br>
                        <strong>Peak Length:</strong> {bottleneck['max_length']:.0f} customers<br>
                        <strong>95th Percentile:</strong> {bottleneck['p95_length']:.1f} customers<br>
                        <br>
                        <em>{bottleneck['recommendation']}</em>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("✓ No queue bottlenecks detected - all queues flowing smoothly")
        
        with subtab3:
            staff_bottlenecks = bottlenecks.get('staff', [])
            if staff_bottlenecks:
                for bottleneck in staff_bottlenecks:
                    severity = bottleneck['severity']
                    issue_type = bottleneck['issue_type']
                    
                    if severity == "critical":
                        color = "#ff4b4b"
                        icon = "🔴"
                        badge = "CRITICAL"
                    elif severity == "warning":
                        color = "#ffa500"
                        icon = "🟡"
                        badge = "WARNING"
                    else:
                        color = "#0099ff"
                        icon = "ℹ️"
                        badge = "INFO"
                    
                    st.markdown(f"""
                    <div style="background-color: #f8f9fa; padding: 12px; border-radius: 5px; 
                                border-left: 4px solid {color}; margin-bottom: 10px;">
                        <strong>{icon} {bottleneck['staff_type']}</strong>
                        <span style="background-color: {color}; color: white; padding: 2px 8px; 
                                     border-radius: 3px; font-size: 11px; margin-left: 8px;">{badge}</span>
                        <span style="background-color: #6c757d; color: white; padding: 2px 8px; 
                                     border-radius: 3px; font-size: 11px; margin-left: 4px;">{issue_type.upper()}</span>
                        <br><br>
                        <strong>Average Utilization:</strong> {bottleneck['avg_utilization']*100:.0f}%<br>
                        <strong>Peak Utilization:</strong> {bottleneck['max_utilization']*100:.0f}%<br>
                        <strong>95th Percentile:</strong> {bottleneck['p95_utilization']*100:.0f}%<br>
                        <br>
                        <em>{bottleneck['recommendation']}</em>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("✓ Staff utilization within normal ranges - balanced workload")

