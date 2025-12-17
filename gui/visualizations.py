"""Visualization functions for Restaurant Simulation GUI.

This module provides Plotly-based visualization functions for displaying
simulation metrics including RevPASH, utilization, queues, and performance.
"""

from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

try:
    from .utils import format_time_display, get_station_names
except ImportError:
    from utils import format_time_display, get_station_names


# Color palette for consistent styling
COLORS = {
    "primary": "#2E86AB",
    "secondary": "#A23B72",
    "success": "#28A745",
    "warning": "#F18F01",
    "danger": "#C73E1D",
    "info": "#17A2B8",
    "light": "#F8F9FA",
    "dark": "#343A40",
    "revenue": "#2E86AB",
    "utilization": "#28A745",
    "queue": "#F18F01",
    "station_colors": [
        "#2E86AB", "#A23B72", "#F18F01", "#28A745", 
        "#C73E1D", "#17A2B8", "#6C757D", "#9B59B6"
    ],
}


def plot_revpash_over_time(df: pd.DataFrame) -> go.Figure:
    """Create a line chart showing RevPASH over time.
    
    Args:
        df: DataFrame with columns: time_hours, revpash
        
    Returns:
        Plotly Figure object
    """
    if df.empty:
        return _empty_figure("No RevPASH data available")
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df["time_hours"],
        y=df["revpash"],
        mode="lines",
        name="RevPASH",
        line=dict(color=COLORS["primary"], width=2),
        fill="tozeroy",
        fillcolor=f"rgba(46, 134, 171, 0.2)",
    ))
    
    fig.update_layout(
        title="Revenue Per Available Seat Hour (RevPASH)",
        xaxis_title="Time (hours)",
        yaxis_title="RevPASH ($)",
        template="plotly_white",
        hovermode="x unified",
        showlegend=False,
    )
    
    return fig


def plot_revenue_accumulation(df: pd.DataFrame) -> go.Figure:
    """Create an area chart showing cumulative revenue over time.
    
    Args:
        df: DataFrame with columns: time_hours, revenue
        
    Returns:
        Plotly Figure object
    """
    if df.empty:
        return _empty_figure("No revenue data available")
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df["time_hours"],
        y=df["revenue"],
        mode="lines",
        name="Revenue",
        line=dict(color=COLORS["success"], width=2),
        fill="tozeroy",
        fillcolor="rgba(40, 167, 69, 0.3)",
    ))
    
    fig.update_layout(
        title="Cumulative Revenue",
        xaxis_title="Time (hours)",
        yaxis_title="Revenue ($)",
        template="plotly_white",
        hovermode="x unified",
        showlegend=False,
    )
    
    return fig


def plot_table_utilization(df: pd.DataFrame) -> go.Figure:
    """Create a line chart showing table utilization over time.
    
    Args:
        df: DataFrame with columns: time_hours, utilization, occupied, total
        
    Returns:
        Plotly Figure object
    """
    if df.empty:
        return _empty_figure("No table utilization data available")
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Table Utilization Rate", "Occupied vs Total Tables"),
        vertical_spacing=0.15,
    )
    
    # Utilization percentage
    fig.add_trace(
        go.Scatter(
            x=df["time_hours"],
            y=df["utilization"] * 100,
            mode="lines",
            name="Utilization %",
            line=dict(color=COLORS["utilization"], width=2),
            fill="tozeroy",
            fillcolor="rgba(40, 167, 69, 0.2)",
        ),
        row=1, col=1
    )
    
    # Occupied vs total
    fig.add_trace(
        go.Scatter(
            x=df["time_hours"],
            y=df["occupied"],
            mode="lines",
            name="Occupied",
            line=dict(color=COLORS["primary"], width=2),
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df["time_hours"],
            y=df["total"],
            mode="lines",
            name="Total",
            line=dict(color=COLORS["dark"], width=1, dash="dash"),
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        height=500,
        template="plotly_white",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    
    fig.update_yaxes(title_text="Utilization %", row=1, col=1)
    fig.update_yaxes(title_text="Tables", row=2, col=1)
    fig.update_xaxes(title_text="Time (hours)", row=2, col=1)
    
    return fig


def plot_staff_utilization(df: pd.DataFrame) -> go.Figure:
    """Create a multi-line chart showing staff utilization over time.
    
    Args:
        df: DataFrame with utilization columns for each staff type
        
    Returns:
        Plotly Figure object
    """
    if df.empty:
        return _empty_figure("No staff utilization data available")
    
    fig = go.Figure()
    
    staff_types = [
        ("host_utilization", "Hosts", COLORS["primary"]),
        ("server_utilization", "Servers", COLORS["secondary"]),
        ("food_runner_utilization", "Food Runners", COLORS["warning"]),
        ("busser_utilization", "Bussers", COLORS["info"]),
    ]
    
    for col, name, color in staff_types:
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df["time_hours"],
                y=df[col] * 100,
                mode="lines",
                name=name,
                line=dict(color=color, width=2),
            ))
    
    # Add overall utilization as dashed line
    if "overall_utilization" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["time_hours"],
            y=df["overall_utilization"] * 100,
            mode="lines",
            name="Overall",
            line=dict(color=COLORS["dark"], width=2, dash="dash"),
        ))
    
    fig.update_layout(
        title="Staff Utilization Over Time",
        xaxis_title="Time (hours)",
        yaxis_title="Utilization %",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    
    fig.update_yaxes(range=[0, 105])
    
    return fig


def plot_station_utilization(df: pd.DataFrame) -> go.Figure:
    """Create a multi-line chart showing station utilization over time.
    
    Args:
        df: DataFrame with utilization columns for each station
        
    Returns:
        Plotly Figure object
    """
    if df.empty:
        return _empty_figure("No station utilization data available")
    
    fig = go.Figure()
    
    # Find station utilization columns
    util_cols = [c for c in df.columns if c.endswith("_utilization") and c != "overall_station_utilization"]
    
    for i, col in enumerate(util_cols):
        station_name = col.replace("_utilization", "")
        color = COLORS["station_colors"][i % len(COLORS["station_colors"])]
        
        fig.add_trace(go.Scatter(
            x=df["time_hours"],
            y=df[col] * 100,
            mode="lines",
            name=station_name.title(),
            line=dict(color=color, width=2),
        ))
    
    # Add overall utilization
    if "overall_station_utilization" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["time_hours"],
            y=df["overall_station_utilization"] * 100,
            mode="lines",
            name="Overall",
            line=dict(color=COLORS["dark"], width=2, dash="dash"),
        ))
    
    fig.update_layout(
        title="Kitchen Station Utilization Over Time",
        xaxis_title="Time (hours)",
        yaxis_title="Utilization %",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    
    fig.update_yaxes(range=[0, 105])
    
    return fig


def plot_queue_lengths(df: pd.DataFrame) -> go.Figure:
    """Create a stacked area chart showing queue lengths over time.
    
    Args:
        df: DataFrame with queue length columns
        
    Returns:
        Plotly Figure object
    """
    if df.empty:
        return _empty_figure("No queue data available")
    
    fig = go.Figure()
    
    queue_cols = [
        ("guest_queue", "Guest Queue", COLORS["primary"]),
        ("host_queue", "Host Queue", COLORS["secondary"]),
        ("expo_queue", "Expo Queue", COLORS["warning"]),
        ("food_runner_queue", "Food Runner Queue", COLORS["info"]),
        ("busser_queue", "Busser Queue", COLORS["success"]),
    ]
    
    for col, name, color in queue_cols:
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df["time_hours"],
                y=df[col],
                mode="lines",
                name=name,
                line=dict(color=color, width=2),
                stackgroup="one",
            ))
    
    fig.update_layout(
        title="Queue Lengths Over Time",
        xaxis_title="Time (hours)",
        yaxis_title="Queue Length",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    
    return fig


def plot_station_queues(df: pd.DataFrame) -> go.Figure:
    """Create a line chart showing station queue lengths over time.
    
    Args:
        df: DataFrame with station queue columns
        
    Returns:
        Plotly Figure object
    """
    if df.empty:
        return _empty_figure("No station queue data available")
    
    fig = go.Figure()
    
    # Find station queue columns
    queue_cols = [c for c in df.columns if c.endswith("_queue") and not c.startswith(("guest", "host", "expo", "food_runner", "busser", "server"))]
    
    for i, col in enumerate(queue_cols):
        station_name = col.replace("_queue", "")
        color = COLORS["station_colors"][i % len(COLORS["station_colors"])]
        
        fig.add_trace(go.Scatter(
            x=df["time_hours"],
            y=df[col],
            mode="lines",
            name=station_name.title(),
            line=dict(color=color, width=2),
        ))
    
    fig.update_layout(
        title="Station Queue Lengths Over Time",
        xaxis_title="Time (hours)",
        yaxis_title="Queue Length",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    
    return fig


def plot_utilization_heatmap(df: pd.DataFrame, metric_type: str = "staff") -> go.Figure:
    """Create a heatmap showing utilization over time.
    
    Args:
        df: DataFrame with utilization columns
        metric_type: Either "staff" or "station"
        
    Returns:
        Plotly Figure object
    """
    if df.empty:
        return _empty_figure("No utilization data available")
    
    if metric_type == "staff":
        util_cols = ["host_utilization", "server_utilization", 
                    "food_runner_utilization", "busser_utilization"]
        labels = ["Hosts", "Servers", "Food Runners", "Bussers"]
        title = "Staff Utilization Heatmap"
    else:
        util_cols = [c for c in df.columns if c.endswith("_utilization") 
                    and c != "overall_station_utilization"]
        labels = [c.replace("_utilization", "").title() for c in util_cols]
        title = "Station Utilization Heatmap"
    
    # Filter to existing columns
    util_cols = [c for c in util_cols if c in df.columns]
    labels = labels[:len(util_cols)]
    
    if not util_cols:
        return _empty_figure("No utilization columns found")
    
    # Create heatmap data - sample to reduce density
    sample_rate = max(1, len(df) // 50)
    df_sampled = df.iloc[::sample_rate]
    
    z_data = df_sampled[util_cols].values.T * 100
    x_data = df_sampled["time_hours"].values
    
    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=x_data,
        y=labels,
        colorscale="RdYlGn",
        zmin=0,
        zmax=100,
        colorbar=dict(title="Utilization %"),
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Time (hours)",
        yaxis_title="",
        template="plotly_white",
    )
    
    return fig


def plot_throughput(df: pd.DataFrame) -> go.Figure:
    """Create a multi-line chart showing throughput metrics.
    
    Args:
        df: DataFrame with throughput columns
        
    Returns:
        Plotly Figure object
    """
    if df.empty:
        return _empty_figure("No throughput data available")
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Parties", "Dishes"),
        vertical_spacing=0.15,
    )
    
    # Parties
    fig.add_trace(
        go.Scatter(
            x=df["time_hours"],
            y=df["parties_served"],
            mode="lines",
            name="Served",
            line=dict(color=COLORS["success"], width=2),
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df["time_hours"],
            y=df["parties_in_system"],
            mode="lines",
            name="In System",
            line=dict(color=COLORS["primary"], width=2),
        ),
        row=1, col=1
    )
    
    # Dishes
    fig.add_trace(
        go.Scatter(
            x=df["time_hours"],
            y=df["dishes_delivered"],
            mode="lines",
            name="Delivered",
            line=dict(color=COLORS["success"], width=2),
            showlegend=False,
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df["time_hours"],
            y=df["dishes_cooking"],
            mode="lines",
            name="Cooking",
            line=dict(color=COLORS["warning"], width=2),
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df["time_hours"],
            y=df["dishes_queued"],
            mode="lines",
            name="Queued",
            line=dict(color=COLORS["info"], width=2),
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        height=500,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    
    fig.update_yaxes(title_text="Count", row=1, col=1)
    fig.update_yaxes(title_text="Count", row=2, col=1)
    fig.update_xaxes(title_text="Time (hours)", row=2, col=1)
    
    return fig


def plot_service_time_distribution(service_times: Dict[str, List[float]]) -> go.Figure:
    """Create histograms showing service time distributions.
    
    Args:
        service_times: Dictionary with lists of service times
        
    Returns:
        Plotly Figure object
    """
    time_types = [
        ("wait_times", "Wait Time (Arrival to Seating)", COLORS["primary"]),
        ("seating_to_order_times", "Seating to Order Complete", COLORS["info"]),
        ("kitchen_times", "Kitchen Time (Order to Dishes Ready)", COLORS["warning"]),
        ("order_to_delivery_times", "Order to First Delivery", COLORS["secondary"]),
        ("first_to_all_delivery_times", "First to All Dishes Delivered", COLORS["danger"]),
        ("dining_times", "Dining Time", COLORS["success"]),
        ("total_times", "Total Time (Arrival to Departure)", COLORS["dark"]),
    ]
    
    # Count how many have data
    available = [(k, n, c) for k, n, c in time_types if service_times.get(k)]
    
    if not available:
        return _empty_figure("No service time data available")
    
    rows = len(available)
    fig = make_subplots(
        rows=rows, cols=1,
        subplot_titles=[n for k, n, c in available],
        vertical_spacing=0.08,
    )
    
    for i, (key, name, color) in enumerate(available, 1):
        times = service_times[key]
        fig.add_trace(
            go.Histogram(
                x=times,
                name=name,
                marker_color=color,
                opacity=0.75,
                showlegend=False,
            ),
            row=i, col=1
        )
        fig.update_xaxes(title_text="Time (minutes)", row=i, col=1)
        fig.update_yaxes(title_text="Count", row=i, col=1)
    
    fig.update_layout(
        height=160 * rows,
        template="plotly_white",
    )
    
    return fig


def plot_current_state_gauges(
    table_util: float,
    staff_util: float,
    station_util: float,
    revpash: float
) -> go.Figure:
    """Create gauge charts showing current state metrics.
    
    Args:
        table_util: Current table utilization (0-1)
        staff_util: Current staff utilization (0-1)
        station_util: Current station utilization (0-1)
        revpash: Current RevPASH value
        
    Returns:
        Plotly Figure object
    """
    fig = make_subplots(
        rows=1, cols=4,
        specs=[[{"type": "indicator"}, {"type": "indicator"}, 
                {"type": "indicator"}, {"type": "indicator"}]],
        subplot_titles=["Table Util", "Staff Util", "Station Util", "RevPASH"],
    )
    
    # Table utilization gauge
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=table_util * 100,
            number={"suffix": "%"},
            gauge=dict(
                axis=dict(range=[0, 100]),
                bar=dict(color=COLORS["primary"]),
                steps=[
                    dict(range=[0, 50], color="rgba(46, 134, 171, 0.2)"),
                    dict(range=[50, 80], color="rgba(46, 134, 171, 0.4)"),
                    dict(range=[80, 100], color="rgba(46, 134, 171, 0.6)"),
                ],
            ),
        ),
        row=1, col=1
    )
    
    # Staff utilization gauge
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=staff_util * 100,
            number={"suffix": "%"},
            gauge=dict(
                axis=dict(range=[0, 100]),
                bar=dict(color=COLORS["secondary"]),
                steps=[
                    dict(range=[0, 50], color="rgba(162, 59, 114, 0.2)"),
                    dict(range=[50, 80], color="rgba(162, 59, 114, 0.4)"),
                    dict(range=[80, 100], color="rgba(162, 59, 114, 0.6)"),
                ],
            ),
        ),
        row=1, col=2
    )
    
    # Station utilization gauge
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=station_util * 100,
            number={"suffix": "%"},
            gauge=dict(
                axis=dict(range=[0, 100]),
                bar=dict(color=COLORS["warning"]),
                steps=[
                    dict(range=[0, 50], color="rgba(241, 143, 1, 0.2)"),
                    dict(range=[50, 80], color="rgba(241, 143, 1, 0.4)"),
                    dict(range=[80, 100], color="rgba(241, 143, 1, 0.6)"),
                ],
            ),
        ),
        row=1, col=3
    )
    
    # RevPASH indicator
    fig.add_trace(
        go.Indicator(
            mode="number+delta",
            value=revpash,
            number={"prefix": "$", "valueformat": ".2f"},
            delta=dict(reference=0, valueformat=".2f"),
        ),
        row=1, col=4
    )
    
    fig.update_layout(
        height=200,
        template="plotly_white",
        margin=dict(t=50, b=20),
    )
    
    return fig


def plot_dish_flow(df: pd.DataFrame) -> go.Figure:
    """Create a stacked area chart showing dish flow through the system.
    
    Args:
        df: DataFrame with dish status columns over time
        
    Returns:
        Plotly Figure object
    """
    if df.empty:
        return _empty_figure("No dish data available")
    
    fig = go.Figure()
    
    dish_states = [
        ("dishes_queued", "In Queue", COLORS["danger"]),
        ("dishes_cooking", "Cooking", COLORS["warning"]),
        ("dishes_delivered", "Delivered", COLORS["success"]),
    ]
    
    for col, name, color in dish_states:
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df["time_hours"],
                y=df[col],
                mode="lines",
                name=name,
                line=dict(color=color, width=2),
                fill="tonexty" if col != "dishes_queued" else "tozeroy",
                stackgroup="one",
            ))
    
    fig.update_layout(
        title="Dish Flow Through Kitchen",
        xaxis_title="Time (hours)",
        yaxis_title="Number of Dishes",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    
    return fig


def plot_kitchen_performance(df: pd.DataFrame) -> go.Figure:
    """Create a multi-panel chart showing kitchen performance metrics.
    
    Args:
        df: DataFrame with station utilization and queue data
        
    Returns:
        Plotly Figure object
    """
    if df.empty:
        return _empty_figure("No kitchen data available")
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Station Utilization", "Station Queues"),
        vertical_spacing=0.15,
    )
    
    # Find station utilization columns
    util_cols = [c for c in df.columns if c.endswith("_utilization") and c != "overall_station_utilization"]
    queue_cols = [c for c in df.columns if c.endswith("_queue") and not c.startswith(("guest", "host", "expo", "food_runner", "busser", "server"))]
    
    # Add utilization traces
    for i, col in enumerate(util_cols):
        station_name = col.replace("_utilization", "")
        color = COLORS["station_colors"][i % len(COLORS["station_colors"])]
        
        fig.add_trace(
            go.Scatter(
                x=df["time_hours"],
                y=df[col] * 100,
                mode="lines",
                name=station_name.replace("_", " ").title(),
                line=dict(color=color, width=2),
            ),
            row=1, col=1
        )
    
    # Add queue traces
    for i, col in enumerate(queue_cols):
        station_name = col.replace("_queue", "")
        color = COLORS["station_colors"][i % len(COLORS["station_colors"])]
        
        fig.add_trace(
            go.Scatter(
                x=df["time_hours"],
                y=df[col],
                mode="lines",
                name=station_name.replace("_", " ").title(),
                line=dict(color=color, width=2),
                showlegend=False,
            ),
            row=2, col=1
        )
    
    fig.update_layout(
        height=500,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    
    fig.update_yaxes(title_text="Utilization %", row=1, col=1, range=[0, 105])
    fig.update_yaxes(title_text="Queue Length", row=2, col=1)
    fig.update_xaxes(title_text="Time (hours)", row=2, col=1)
    
    return fig


def _empty_figure(message: str) -> go.Figure:
    """Create an empty figure with a message.
    
    Args:
        message: Message to display
        
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=14, color="gray"),
    )
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        template="plotly_white",
    )
    return fig

