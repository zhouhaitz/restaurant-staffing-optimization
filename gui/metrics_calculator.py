"""Metrics calculation for Restaurant Simulation GUI.

This module calculates key performance metrics including:
- RevPASH (Revenue Per Available Seat Hour)
- Table utilization
- Staff utilization (hosts, servers, food runners, bussers)
- Station utilization
"""

from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import sys
from pathlib import Path
import importlib.util

# Load gui/utils.py explicitly to avoid conflict with experiments/utils.py
gui_utils_path = Path(__file__).parent / "utils.py"
spec = importlib.util.spec_from_file_location("gui_utils", gui_utils_path)
gui_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gui_utils)

# Import required functions from gui_utils
convert_minutes_to_hours = gui_utils.convert_minutes_to_hours
get_total_seats_from_snapshots = gui_utils.get_total_seats_from_snapshots
get_total_tables_from_snapshots = gui_utils.get_total_tables_from_snapshots
count_occupied_tables = gui_utils.count_occupied_tables
safe_divide = gui_utils.safe_divide
get_station_names = gui_utils.get_station_names


def calculate_revpash(
    snapshots: List[Dict],
    total_seats: Optional[int] = None
) -> pd.DataFrame:
    """Calculate Revenue Per Available Seat Hour (RevPASH) over time.
    
    RevPASH = Revenue / (Total Seats × Hours)
    
    Args:
        snapshots: List of snapshot dictionaries
        total_seats: Total seat count (if None, extracted from snapshots)
        
    Returns:
        DataFrame with columns: time_minutes, time_hours, revenue, revpash
    """
    if not snapshots:
        return pd.DataFrame(columns=["time_minutes", "time_hours", "revenue", "revpash"])
    
    if total_seats is None:
        total_seats = get_total_seats_from_snapshots(snapshots)
    
    if total_seats == 0:
        total_seats = 1  # Avoid division by zero
    
    data = []
    for snapshot in snapshots:
        time_minutes = snapshot.get("time", 0)
        time_hours = convert_minutes_to_hours(time_minutes)
        revenue = snapshot.get("total_revenue", 0)
        
        # RevPASH calculation
        if time_hours > 0:
            revpash = safe_divide(revenue, total_seats * time_hours, 0.0)
        else:
            revpash = 0.0
        
        data.append({
            "time_minutes": time_minutes,
            "time_hours": time_hours,
            "revenue": revenue,
            "revpash": revpash,
        })
    
    return pd.DataFrame(data)


def calculate_instantaneous_revpash(
    snapshots: List[Dict],
    total_seats: Optional[int] = None,
    window_minutes: float = 15.0
) -> pd.DataFrame:
    """Calculate instantaneous RevPASH using a rolling window.
    
    This calculates RevPASH based on revenue generated in recent window,
    which gives a better picture of current performance.
    
    Args:
        snapshots: List of snapshot dictionaries
        total_seats: Total seat count
        window_minutes: Rolling window size in minutes
        
    Returns:
        DataFrame with columns: time_minutes, time_hours, instant_revpash
    """
    if not snapshots:
        return pd.DataFrame(columns=["time_minutes", "time_hours", "instant_revpash"])
    
    if total_seats is None:
        total_seats = get_total_seats_from_snapshots(snapshots)
    
    if total_seats == 0:
        total_seats = 1
    
    window_hours = convert_minutes_to_hours(window_minutes)
    
    data = []
    for i, snapshot in enumerate(snapshots):
        time_minutes = snapshot.get("time", 0)
        time_hours = convert_minutes_to_hours(time_minutes)
        current_revenue = snapshot.get("total_revenue", 0)
        
        # Find revenue at window start
        window_start_time = max(0, time_minutes - window_minutes)
        prev_revenue = 0
        for j in range(i, -1, -1):
            if snapshots[j].get("time", 0) <= window_start_time:
                prev_revenue = snapshots[j].get("total_revenue", 0)
                break
        
        revenue_in_window = current_revenue - prev_revenue
        instant_revpash = safe_divide(revenue_in_window, total_seats * window_hours, 0.0)
        
        data.append({
            "time_minutes": time_minutes,
            "time_hours": time_hours,
            "instant_revpash": instant_revpash,
        })
    
    return pd.DataFrame(data)


def calculate_table_utilization(
    snapshots: List[Dict],
    total_tables: Optional[int] = None
) -> pd.DataFrame:
    """Calculate table utilization over time.
    
    Table Utilization = Occupied Tables / Total Tables
    
    Args:
        snapshots: List of snapshot dictionaries
        total_tables: Total table count (if None, extracted from snapshots)
        
    Returns:
        DataFrame with columns: time_minutes, time_hours, occupied, available, 
                               total, utilization
    """
    if not snapshots:
        return pd.DataFrame(columns=[
            "time_minutes", "time_hours", "occupied", "available", 
            "total", "utilization"
        ])
    
    if total_tables is None:
        total_tables = get_total_tables_from_snapshots(snapshots)
    
    data = []
    for snapshot in snapshots:
        time_minutes = snapshot.get("time", 0)
        time_hours = convert_minutes_to_hours(time_minutes)
        
        tables = snapshot.get("tables", [])
        occupied = sum(1 for t in tables if t.get("party_id") is not None)
        available = sum(1 for t in tables if t.get("is_available", False))
        total = len(tables) if tables else total_tables
        
        utilization = safe_divide(occupied, total, 0.0)
        
        data.append({
            "time_minutes": time_minutes,
            "time_hours": time_hours,
            "occupied": occupied,
            "available": available,
            "total": total,
            "utilization": utilization,
        })
    
    return pd.DataFrame(data)


def calculate_staff_utilization(
    snapshots: List[Dict],
    staff_counts: Optional[Dict[str, int]] = None
) -> pd.DataFrame:
    """Calculate staff utilization over time.
    
    Tracks utilization for hosts, servers, food runners, and bussers.
    
    Args:
        snapshots: List of snapshot dictionaries
        staff_counts: Dictionary with staff type counts (e.g., {'hosts': 2, 'servers': 4})
                     If None, inferred from snapshots
        
    Returns:
        DataFrame with utilization metrics for each staff type
    """
    if not snapshots:
        return pd.DataFrame()
    
    # Infer staff counts from snapshots if not provided
    if staff_counts is None:
        staff_counts = _infer_staff_counts(snapshots)
    
    data = []
    for snapshot in snapshots:
        time_minutes = snapshot.get("time", 0)
        time_hours = convert_minutes_to_hours(time_minutes)
        
        row = {
            "time_minutes": time_minutes,
            "time_hours": time_hours,
        }
        
        # Host utilization - based on host queue and guest queue
        host_queue = snapshot.get("host_queue_length", 0)
        guest_queue = snapshot.get("guest_queue_length", 0)
        num_hosts = staff_counts.get("hosts", 1)
        # Estimate host busy: if there are parties being seated (between guest queue and table)
        parties_being_seated = sum(
            1 for p in snapshot.get("parties", [])
            if p.get("status") == "being_seated"
        )
        row["host_busy"] = min(parties_being_seated, num_hosts)
        row["host_total"] = num_hosts
        row["host_utilization"] = safe_divide(row["host_busy"], num_hosts, 0.0)
        
        # Server utilization - based on zone queues
        num_servers = staff_counts.get("servers", 1)
        server_queue_total = 0
        for key, value in snapshot.items():
            if key.startswith("server_zone_") and key.endswith("_queue"):
                server_queue_total += value
        # Servers are busy if there are tasks in their zone queues
        # or if there are parties ordering/paying
        parties_with_server = sum(
            1 for p in snapshot.get("parties", [])
            if p.get("status") in ["ordering", "paying"]
        )
        row["server_busy"] = min(parties_with_server + server_queue_total, num_servers)
        row["server_total"] = num_servers
        row["server_utilization"] = safe_divide(row["server_busy"], num_servers, 0.0)
        
        # Food runner utilization
        num_food_runners = staff_counts.get("food_runners", 1)
        food_runner_queue = snapshot.get("food_runner_queue", 0)
        # Count active delivery tasks
        delivery_tasks = sum(
            1 for t in snapshot.get("tasks", [])
            if t.get("task_type") == "DELIVERY" and t.get("started_time") is not None
        )
        row["food_runner_busy"] = min(delivery_tasks, num_food_runners)
        row["food_runner_total"] = num_food_runners
        row["food_runner_utilization"] = safe_divide(row["food_runner_busy"], num_food_runners, 0.0)
        
        # Busser utilization
        num_bussers = staff_counts.get("bussers", 1)
        busser_queue = snapshot.get("busser_queue", 0)
        # Count active cleaning tasks
        cleaning_tasks = sum(
            1 for t in snapshot.get("tasks", [])
            if t.get("task_type") == "CLEANING" and t.get("started_time") is not None
        )
        row["busser_busy"] = min(cleaning_tasks, num_bussers)
        row["busser_total"] = num_bussers
        row["busser_utilization"] = safe_divide(row["busser_busy"], num_bussers, 0.0)
        
        # Overall staff utilization
        total_busy = (row["host_busy"] + row["server_busy"] + 
                     row["food_runner_busy"] + row["busser_busy"])
        total_staff = num_hosts + num_servers + num_food_runners + num_bussers
        row["overall_utilization"] = safe_divide(total_busy, total_staff, 0.0)
        
        data.append(row)
    
    return pd.DataFrame(data)


def _infer_staff_counts(snapshots: List[Dict]) -> Dict[str, int]:
    """Infer staff counts from snapshot data.
    
    Uses maximum observed active staff as the count.
    
    Args:
        snapshots: List of snapshot dictionaries
        
    Returns:
        Dictionary with staff counts
    """
    # Default counts
    counts = {
        "hosts": 1,
        "servers": 2,
        "food_runners": 2,
        "bussers": 1,
    }
    
    # Try to infer from zone queues (number of server zones = number of servers)
    for snapshot in snapshots:
        num_zones = sum(1 for k in snapshot.keys() if k.startswith("server_zone_"))
        if num_zones > counts["servers"]:
            counts["servers"] = num_zones
    
    return counts


def calculate_station_utilization(snapshots: List[Dict]) -> pd.DataFrame:
    """Calculate kitchen station utilization over time.
    
    Station Utilization = Busy Slots / Capacity
    
    Args:
        snapshots: List of snapshot dictionaries
        
    Returns:
        DataFrame with utilization for each station
    """
    if not snapshots:
        return pd.DataFrame()
    
    # Get all station names
    station_names = get_station_names(snapshots)
    
    if not station_names:
        return pd.DataFrame()
    
    data = []
    for snapshot in snapshots:
        time_minutes = snapshot.get("time", 0)
        time_hours = convert_minutes_to_hours(time_minutes)
        
        row = {
            "time_minutes": time_minutes,
            "time_hours": time_hours,
        }
        
        stations = snapshot.get("stations", [])
        station_map = {s.get("name"): s for s in stations}
        
        total_busy = 0
        total_capacity = 0
        
        for name in station_names:
            station = station_map.get(name, {})
            busy = station.get("busy_slots", 0)
            capacity = station.get("capacity", 1)
            queue_length = station.get("queue_length", 0)
            
            row[f"{name}_busy"] = busy
            row[f"{name}_capacity"] = capacity
            row[f"{name}_queue"] = queue_length
            row[f"{name}_utilization"] = safe_divide(busy, capacity, 0.0)
            
            total_busy += busy
            total_capacity += capacity
        
        row["overall_station_utilization"] = safe_divide(total_busy, total_capacity, 0.0)
        
        data.append(row)
    
    return pd.DataFrame(data)


def calculate_queue_metrics(snapshots: List[Dict]) -> pd.DataFrame:
    """Calculate queue length metrics over time.
    
    Args:
        snapshots: List of snapshot dictionaries
        
    Returns:
        DataFrame with queue lengths for different queues
    """
    if not snapshots:
        return pd.DataFrame()
    
    data = []
    for snapshot in snapshots:
        time_minutes = snapshot.get("time", 0)
        time_hours = convert_minutes_to_hours(time_minutes)
        
        row = {
            "time_minutes": time_minutes,
            "time_hours": time_hours,
            "guest_queue": snapshot.get("guest_queue_length", 0),
            "host_queue": snapshot.get("host_queue_length", 0),
            "expo_queue": snapshot.get("expo_queue_length", 0),
            "food_runner_queue": snapshot.get("food_runner_queue", 0),
            "busser_queue": snapshot.get("busser_queue", 0),
        }
        
        # Add station queues
        for key, value in snapshot.items():
            if "_queue" in key and key not in row:
                row[key] = value
        
        data.append(row)
    
    return pd.DataFrame(data)


def calculate_throughput_metrics(snapshots: List[Dict]) -> pd.DataFrame:
    """Calculate throughput metrics over time.
    
    Args:
        snapshots: List of snapshot dictionaries
        
    Returns:
        DataFrame with throughput metrics
    """
    if not snapshots:
        return pd.DataFrame()
    
    data = []
    for snapshot in snapshots:
        time_minutes = snapshot.get("time", 0)
        time_hours = convert_minutes_to_hours(time_minutes)
        
        parties_served = snapshot.get("parties_served", 0)
        parties_in_system = snapshot.get("parties_in_system", 0)
        
        # Count dishes by status
        dishes = snapshot.get("dishes", [])
        dishes_delivered = sum(1 for d in dishes if d.get("status") == "delivered")
        dishes_cooking = sum(1 for d in dishes if d.get("status") == "cooking")
        dishes_queued = sum(1 for d in dishes if d.get("status") == "queued")
        
        row = {
            "time_minutes": time_minutes,
            "time_hours": time_hours,
            "parties_served": parties_served,
            "parties_in_system": parties_in_system,
            "total_parties": parties_served + parties_in_system,
            "dishes_delivered": dishes_delivered,
            "dishes_cooking": dishes_cooking,
            "dishes_queued": dishes_queued,
            "total_dishes": len(dishes),
            "parties_per_hour": safe_divide(parties_served, time_hours, 0.0) if time_hours > 0 else 0,
            "dishes_per_hour": safe_divide(dishes_delivered, time_hours, 0.0) if time_hours > 0 else 0,
        }
        
        data.append(row)
    
    return pd.DataFrame(data)


def calculate_service_times(snapshots: List[Dict]) -> Dict[str, List[float]]:
    """Calculate service time distributions from party data.
    
    Args:
        snapshots: List of snapshot dictionaries
        
    Returns:
        Dictionary with lists of service times for different phases
    """
    if not snapshots:
        return {}
    
    # Get the last snapshot to find completed parties
    last_snapshot = snapshots[-1]
    parties = last_snapshot.get("parties", [])
    
    wait_times = []
    dining_times = []
    total_times = []
    order_to_delivery_times = []  # Order complete to first dish delivered
    kitchen_times = []  # Kitchen start to all dishes ready at expo
    first_to_all_delivery_times = []  # First dish to all dishes delivered
    seating_to_order_times = []  # Seated to ordering complete
    
    for party in parties:
        arrival = party.get("arrival_time")
        seated = party.get("table_assigned_time")
        ordering_start = party.get("ordering_start")
        ordering_complete = party.get("ordering_complete")
        kitchen_start = party.get("kitchen_start")
        all_dishes_ready = party.get("all_dishes_ready")
        first_delivery = party.get("first_delivery_time")
        all_delivered = party.get("all_dishes_delivered")
        dining_start = party.get("dining_start")
        dining_complete = party.get("dining_complete")
        departure = party.get("departure_time")
        
        # Wait time (arrival to seating)
        if arrival is not None and seated is not None:
            wait_times.append(seated - arrival)
        
        # Seating to order complete time
        if seated is not None and ordering_complete is not None:
            seating_to_order_times.append(ordering_complete - seated)
        
        # Kitchen time (order placed to all dishes ready at expo)
        if kitchen_start is not None and all_dishes_ready is not None:
            kitchen_times.append(all_dishes_ready - kitchen_start)
        
        # Order to first delivery time
        if ordering_complete is not None and first_delivery is not None:
            order_to_delivery_times.append(first_delivery - ordering_complete)
        
        # First dish to all dishes delivered
        if first_delivery is not None and all_delivered is not None:
            first_to_all_delivery_times.append(all_delivered - first_delivery)
        
        # Dining time
        if dining_start is not None and dining_complete is not None:
            dining_times.append(dining_complete - dining_start)
        
        # Total time (arrival to departure)
        if arrival is not None and departure is not None:
            total_times.append(departure - arrival)
    
    return {
        "wait_times": wait_times,
        "seating_to_order_times": seating_to_order_times,
        "kitchen_times": kitchen_times,
        "order_to_delivery_times": order_to_delivery_times,
        "first_to_all_delivery_times": first_to_all_delivery_times,
        "dining_times": dining_times,
        "total_times": total_times,
    }


def calculate_summary_statistics(snapshots: List[Dict]) -> Dict[str, Any]:
    """Calculate summary statistics for the simulation.
    
    Args:
        snapshots: List of snapshot dictionaries
        
    Returns:
        Dictionary with summary statistics
    """
    if not snapshots:
        return {}
    
    last_snapshot = snapshots[-1]
    first_snapshot = snapshots[0]
    
    total_seats = get_total_seats_from_snapshots(snapshots)
    total_tables = get_total_tables_from_snapshots(snapshots)
    
    start_time = first_snapshot.get("time", 0)
    end_time = last_snapshot.get("time", 0)
    duration_hours = convert_minutes_to_hours(end_time - start_time)
    
    total_revenue = last_snapshot.get("total_revenue", 0)
    parties_served = last_snapshot.get("parties_served", 0)
    
    # Calculate RevPASH
    revpash = safe_divide(total_revenue, total_seats * duration_hours, 0.0) if duration_hours > 0 else 0
    
    # Calculate average table utilization
    table_df = calculate_table_utilization(snapshots, total_tables)
    avg_table_utilization = table_df["utilization"].mean() if not table_df.empty else 0
    
    # Calculate average station utilization
    station_df = calculate_station_utilization(snapshots)
    avg_station_utilization = (
        station_df["overall_station_utilization"].mean() 
        if not station_df.empty and "overall_station_utilization" in station_df.columns 
        else 0
    )
    
    # Service times
    service_times = calculate_service_times(snapshots)
    avg_wait_time = np.mean(service_times.get("wait_times", [0])) if service_times.get("wait_times") else 0
    avg_total_time = np.mean(service_times.get("total_times", [0])) if service_times.get("total_times") else 0
    avg_kitchen_time = np.mean(service_times.get("kitchen_times", [0])) if service_times.get("kitchen_times") else 0
    avg_order_to_delivery = np.mean(service_times.get("order_to_delivery_times", [0])) if service_times.get("order_to_delivery_times") else 0
    avg_dining_time = np.mean(service_times.get("dining_times", [0])) if service_times.get("dining_times") else 0
    
    # Count total dishes delivered
    dishes = last_snapshot.get("dishes", [])
    total_dishes = len(dishes)
    dishes_delivered = sum(1 for d in dishes if d.get("status") == "delivered")
    
    return {
        "total_revenue": total_revenue,
        "revpash": revpash,
        "duration_hours": duration_hours,
        "total_seats": total_seats,
        "total_tables": total_tables,
        "parties_served": parties_served,
        "parties_per_hour": safe_divide(parties_served, duration_hours, 0.0),
        "revenue_per_party": safe_divide(total_revenue, parties_served, 0.0),
        "avg_table_utilization": avg_table_utilization,
        "avg_station_utilization": avg_station_utilization,
        "avg_wait_time": avg_wait_time,
        "avg_kitchen_time": avg_kitchen_time,
        "avg_order_to_delivery": avg_order_to_delivery,
        "avg_dining_time": avg_dining_time,
        "avg_total_time": avg_total_time,
        "total_dishes": total_dishes,
        "dishes_delivered": dishes_delivered,
        "dishes_per_hour": safe_divide(dishes_delivered, duration_hours, 0.0),
    }


def calculate_percentile_times(service_times: Dict[str, List[float]], percentile: int = 95) -> Dict[str, float]:
    """Calculate percentile service times for various metrics.
    
    Args:
        service_times: Dictionary with lists of service times from calculate_service_times()
        percentile: Percentile to calculate (default: 95)
        
    Returns:
        Dictionary with percentile values for each time metric
    """
    percentiles = {}
    
    time_metrics = [
        'wait_times',
        'seating_to_order_times',
        'kitchen_times',
        'order_to_delivery_times',
        'first_to_all_delivery_times',
        'dining_times',
        'total_times'
    ]
    
    for metric in time_metrics:
        times = service_times.get(metric, [])
        if times and len(times) > 0:
            percentiles[f'{metric}_p{percentile}'] = float(np.percentile(times, percentile))
        else:
            percentiles[f'{metric}_p{percentile}'] = 0.0
    
    return percentiles

