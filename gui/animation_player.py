"""Animation player for Restaurant Simulation GUI.

This module provides animated playback functionality for visualizing
the restaurant simulation state over time.
"""

from typing import Dict, List, Optional, Any, Tuple
import math
import plotly.graph_objects as go
from plotly.subplots import make_subplots

try:
    from .utils import (
        find_snapshot_index_at_time,
        get_snapshot_at_time,
        format_time_display,
        safe_divide,
    )
except ImportError:
    from utils import (
        find_snapshot_index_at_time,
        get_snapshot_at_time,
        format_time_display,
        safe_divide,
    )


# Status colors for visualization
STATUS_COLORS = {
    # Table statuses
    "available": "#28A745",  # Green
    "occupied": "#2E86AB",   # Blue
    "cleaning": "#F18F01",   # Orange
    
    # Party statuses
    "waiting_for_table": "#DC3545",  # Red
    "being_seated": "#FFC107",       # Yellow
    "deciding": "#17A2B8",           # Cyan
    "ordering": "#6F42C1",           # Purple
    "waiting_for_food": "#FD7E14",   # Orange
    "receiving_food": "#9B59B6",     # Purple - receiving dishes (some delivered)
    "dining": "#28A745",             # Green
    "paying": "#20C997",             # Teal
    "cleaning": "#F18F01",           # Orange
    "departed": "#6C757D",           # Gray
    
    # Dish statuses
    "queued": "#DC3545",      # Red
    "cooking": "#FFC107",     # Yellow
    "expo_queue": "#FD7E14",  # Orange
    "expo_check": "#17A2B8",  # Cyan
    "ready": "#28A745",       # Green
    "delivered": "#6C757D",   # Gray
    
    # Station status
    "busy": "#DC3545",
    "idle": "#28A745",
    
    # Cook status
    "cook_busy": "#DC3545",
    "cook_idle": "#28A745",
}


class AnimationPlayer:
    """Manages animated playback of restaurant simulation snapshots."""
    
    def __init__(
        self,
        snapshots: List[Dict],
        update_interval: float = 0.5
    ):
        """Initialize the animation player.
        
        Args:
            snapshots: List of snapshot dictionaries
            update_interval: Time between updates in seconds
        """
        self.snapshots = snapshots
        self.update_interval = update_interval
        self.current_index = 0
        self.is_playing = False
        self.playback_speed = 1.0
        
        # Calculate time range
        if snapshots:
            self.min_time = snapshots[0].get("time", 0)
            self.max_time = snapshots[-1].get("time", 0)
        else:
            self.min_time = 0
            self.max_time = 0
    
    def get_snapshot_at_time(self, target_time: float) -> Optional[Dict]:
        """Get the snapshot closest to the target time.
        
        Args:
            target_time: Target time in minutes
            
        Returns:
            Snapshot dictionary or None
        """
        return get_snapshot_at_time(self.snapshots, target_time)
    
    def get_current_snapshot(self) -> Optional[Dict]:
        """Get the current snapshot.
        
        Returns:
            Current snapshot dictionary or None
        """
        if 0 <= self.current_index < len(self.snapshots):
            return self.snapshots[self.current_index]
        return None
    
    def set_time(self, target_time: float) -> None:
        """Set the current time position.
        
        Args:
            target_time: Target time in minutes
        """
        self.current_index = find_snapshot_index_at_time(self.snapshots, target_time)
    
    def step_forward(self) -> bool:
        """Move to the next snapshot.
        
        Returns:
            True if moved, False if at end
        """
        if self.current_index < len(self.snapshots) - 1:
            self.current_index += 1
            return True
        return False
    
    def step_backward(self) -> bool:
        """Move to the previous snapshot.
        
        Returns:
            True if moved, False if at start
        """
        if self.current_index > 0:
            self.current_index -= 1
            return True
        return False
    
    def reset(self) -> None:
        """Reset to the beginning."""
        self.current_index = 0
        self.is_playing = False


def render_restaurant_layout(
    snapshot: Dict,
    width: int = 800,
    height: int = 600
) -> go.Figure:
    """Render the restaurant layout as a Plotly figure.
    
    Shows tables, their status, and party information.
    
    Args:
        snapshot: Snapshot dictionary
        width: Figure width in pixels
        height: Figure height in pixels
        
    Returns:
        Plotly Figure object
    """
    if not snapshot:
        return _empty_layout_figure("No snapshot data")
    
    tables = snapshot.get("tables", [])
    parties = snapshot.get("parties", [])
    
    if not tables:
        return _empty_layout_figure("No table data in snapshot")
    
    # Create party lookup
    party_map = {p.get("id"): p for p in parties}
    
    # Calculate grid layout for tables
    num_tables = len(tables)
    cols = math.ceil(math.sqrt(num_tables))
    rows = math.ceil(num_tables / cols)
    
    fig = go.Figure()
    
    # Add tables as scatter points with markers
    for i, table in enumerate(tables):
        row = i // cols
        col = i % cols
        
        x = col * 2 + 1
        y = (rows - row - 1) * 2 + 1
        
        table_id = table.get("id", i)
        table_size = table.get("size", 2)
        party_id = table.get("party_id")
        is_available = table.get("is_available", True)
        
        # Determine table status and color
        if party_id is not None:
            party = party_map.get(party_id, {})
            party_status = party.get("status", "occupied")
            if party_status == "cleaning":
                color = STATUS_COLORS["cleaning"]
                status_text = "Cleaning"
            else:
                color = STATUS_COLORS["occupied"]
                status_text = party_status.replace("_", " ").title()
        elif is_available:
            color = STATUS_COLORS["available"]
            status_text = "Available"
        else:
            color = STATUS_COLORS["cleaning"]
            status_text = "Unavailable"
        
        # Add table marker
        marker_size = 30 + table_size * 5
        
        fig.add_trace(go.Scatter(
            x=[x],
            y=[y],
            mode="markers+text",
            marker=dict(
                size=marker_size,
                color=color,
                line=dict(color="white", width=2),
                symbol="square",
            ),
            text=f"T{table_id}<br>{table_size}",
            textposition="middle center",
            textfont=dict(color="white", size=10),
            hovertemplate=(
                f"<b>Table {table_id}</b><br>"
                f"Size: {table_size}<br>"
                f"Status: {status_text}<br>"
                f"Party: {party_id if party_id else 'None'}"
                "<extra></extra>"
            ),
            showlegend=False,
        ))
    
    # Configure layout
    fig.update_layout(
        width=width,
        height=height,
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[0, cols * 2 + 1],
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[0, rows * 2 + 1],
            scaleanchor="x",
        ),
        plot_bgcolor="rgba(248, 249, 250, 1)",
        margin=dict(l=20, r=20, t=40, b=20),
        title=dict(
            text=f"Restaurant Layout - {format_time_display(snapshot.get('time', 0))}",
            x=0.5,
        ),
    )
    
    # Add legend for table status
    for status, color in [("Available", STATUS_COLORS["available"]),
                          ("Occupied", STATUS_COLORS["occupied"]),
                          ("Cleaning", STATUS_COLORS["cleaning"])]:
        fig.add_trace(go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            marker=dict(size=15, color=color, symbol="square"),
            name=status,
            showlegend=True,
        ))
    
    fig.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
        ),
    )
    
    return fig


def render_station_status(
    snapshot: Dict,
    width: int = 600,
    height: int = 300
) -> go.Figure:
    """Render kitchen station status as a bar chart.
    
    Args:
        snapshot: Snapshot dictionary
        width: Figure width
        height: Figure height
        
    Returns:
        Plotly Figure object
    """
    if not snapshot:
        return _empty_layout_figure("No snapshot data")
    
    stations = snapshot.get("stations", [])
    
    if not stations:
        return _empty_layout_figure("No station data")
    
    names = []
    busy_slots = []
    capacities = []
    queue_lengths = []
    
    for station in stations:
        names.append(station.get("name", "Unknown").title())
        busy_slots.append(station.get("busy_slots", 0))
        capacities.append(station.get("capacity", 1))
        queue_lengths.append(station.get("queue_length", 0))
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Station Utilization", "Queue Lengths"),
        specs=[[{"type": "bar"}, {"type": "bar"}]],
    )
    
    # Utilization bars
    fig.add_trace(
        go.Bar(
            x=names,
            y=busy_slots,
            name="Busy",
            marker_color=STATUS_COLORS["busy"],
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=names,
            y=[c - b for c, b in zip(capacities, busy_slots)],
            name="Idle",
            marker_color=STATUS_COLORS["idle"],
        ),
        row=1, col=1
    )
    
    # Queue length bars
    fig.add_trace(
        go.Bar(
            x=names,
            y=queue_lengths,
            name="Queue",
            marker_color="#F18F01",
            showlegend=False,
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        width=width,
        height=height,
        barmode="stack",
        template="plotly_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.25,
        ),
        margin=dict(l=40, r=40, t=60, b=40),
    )
    
    fig.update_yaxes(title_text="Slots", row=1, col=1)
    fig.update_yaxes(title_text="Count", row=1, col=2)
    
    return fig


def render_party_flow(
    snapshot: Dict,
    width: int = 800,
    height: int = 250
) -> go.Figure:
    """Render party flow through the restaurant as a funnel/sankey diagram.
    
    Args:
        snapshot: Snapshot dictionary
        width: Figure width
        height: Figure height
        
    Returns:
        Plotly Figure object
    """
    if not snapshot:
        return _empty_layout_figure("No snapshot data")
    
    parties = snapshot.get("parties", [])
    
    # Count parties by status, with additional breakdown for food delivery
    status_counts = {}
    receiving_food_count = 0  # Parties with some dishes delivered but not all
    
    for party in parties:
        status = party.get("status", "unknown")
        
        # Check if party is receiving food (some dishes delivered, not all)
        dishes_delivered = party.get("dishes_delivered_count", 0)
        total_dishes = party.get("total_dishes", 0)
        
        if status == "waiting_for_food" and dishes_delivered > 0 and dishes_delivered < total_dishes:
            status = "receiving_food"
        
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Define flow stages (updated with new states)
    stages = [
        "waiting_for_table",
        "being_seated",
        "deciding",
        "ordering",
        "waiting_for_food",
        "receiving_food",
        "dining",
        "paying",
        "cleaning",
        "departed",
    ]
    
    stage_labels = [
        "Waiting for Table",
        "Being Seated",
        "Deciding",
        "Ordering",
        "Waiting for Food",
        "Receiving Food",
        "Dining",
        "Paying",
        "Cleaning",
        "Departed",
    ]
    
    counts = [status_counts.get(s, 0) for s in stages]
    colors = [STATUS_COLORS.get(s, "#6C757D") for s in stages]
    
    fig = go.Figure(go.Funnel(
        y=stage_labels,
        x=counts,
        textposition="inside",
        textinfo="value",
        marker=dict(color=colors),
        connector=dict(line=dict(color="royalblue", dash="solid", width=2)),
    ))
    
    fig.update_layout(
        width=width,
        height=height,
        title="Party Flow",
        template="plotly_white",
        margin=dict(l=20, r=20, t=60, b=20),
    )
    
    return fig


def render_current_metrics(
    snapshot: Dict,
    total_seats: int = 0
) -> Dict[str, Any]:
    """Extract current metrics from a snapshot for display.
    
    Args:
        snapshot: Snapshot dictionary
        total_seats: Total seat count for RevPASH calculation
        
    Returns:
        Dictionary of current metrics
    """
    if not snapshot:
        return {}
    
    time_minutes = snapshot.get("time", 0)
    time_hours = time_minutes / 60.0
    revenue = snapshot.get("total_revenue", 0)
    
    # RevPASH
    revpash = safe_divide(revenue, total_seats * time_hours, 0) if time_hours > 0 and total_seats > 0 else 0
    
    # Table utilization
    tables = snapshot.get("tables", [])
    occupied = sum(1 for t in tables if t.get("party_id") is not None)
    table_util = safe_divide(occupied, len(tables), 0) if tables else 0
    
    # Party counts
    parties_in_system = snapshot.get("parties_in_system", 0)
    parties_served = snapshot.get("parties_served", 0)
    
    # Queue lengths
    guest_queue = snapshot.get("guest_queue_length", 0)
    expo_queue = snapshot.get("expo_queue_length", 0)
    food_runner_queue = snapshot.get("food_runner_queue", 0)
    
    # Dish counts
    dishes = snapshot.get("dishes", [])
    dishes_cooking = sum(1 for d in dishes if d.get("status") == "cooking")
    dishes_ready = sum(1 for d in dishes if d.get("status") in ["ready", "expo_check", "expo_queue"])
    dishes_delivered = sum(1 for d in dishes if d.get("status") == "delivered")
    total_dishes = len(dishes)
    
    # Station utilization
    stations = snapshot.get("stations", [])
    total_station_busy = sum(s.get("busy_slots", 0) for s in stations)
    total_station_capacity = sum(s.get("capacity", 1) for s in stations)
    station_util = safe_divide(total_station_busy, total_station_capacity, 0)
    
    # Active delivery tasks
    tasks = snapshot.get("tasks", [])
    active_deliveries = sum(1 for t in tasks if t.get("task_type") == "DELIVERY")
    
    return {
        "time": time_minutes,
        "time_formatted": format_time_display(time_minutes),
        "revenue": revenue,
        "revpash": revpash,
        "table_utilization": table_util,
        "occupied_tables": occupied,
        "total_tables": len(tables),
        "parties_in_system": parties_in_system,
        "parties_served": parties_served,
        "guest_queue": guest_queue,
        "expo_queue": expo_queue,
        "food_runner_queue": food_runner_queue,
        "dishes_cooking": dishes_cooking,
        "dishes_ready": dishes_ready,
        "dishes_delivered": dishes_delivered,
        "total_dishes": total_dishes,
        "station_utilization": station_util,
        "active_deliveries": active_deliveries,
    }


def _empty_layout_figure(message: str) -> go.Figure:
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

