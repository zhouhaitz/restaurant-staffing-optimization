"""Utility functions for the Restaurant Simulation GUI.

Helper functions for time conversion, data extraction, and common operations.
"""

from typing import Dict, List, Optional, Any
import bisect


def convert_minutes_to_hours(minutes: float) -> float:
    """Convert simulation time from minutes to hours.
    
    Args:
        minutes: Time in minutes
        
    Returns:
        Time in hours
    """
    return minutes / 60.0


def convert_hours_to_minutes(hours: float) -> float:
    """Convert time from hours to minutes.
    
    Args:
        hours: Time in hours
        
    Returns:
        Time in minutes
    """
    return hours * 60.0


def format_time_display(minutes: float) -> str:
    """Format simulation time for display.
    
    Args:
        minutes: Time in minutes
        
    Returns:
        Formatted string like "1h 30m" or "45m"
    """
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    
    if hours > 0:
        return f"{hours}h {mins}m"
    else:
        return f"{mins}m"


def get_total_seats_from_snapshots(snapshots: List[Dict]) -> int:
    """Extract total seat count from snapshot data.
    
    Calculates total seats by summing table sizes from the first snapshot
    that contains table information.
    
    Args:
        snapshots: List of snapshot dictionaries
        
    Returns:
        Total number of seats across all tables
    """
    if not snapshots:
        return 0
    
    # Find first snapshot with table data
    for snapshot in snapshots:
        tables = snapshot.get("tables", [])
        if tables:
            return sum(table.get("size", 0) for table in tables)
    
    return 0


def get_total_tables_from_snapshots(snapshots: List[Dict]) -> int:
    """Extract total table count from snapshot data.
    
    Args:
        snapshots: List of snapshot dictionaries
        
    Returns:
        Total number of tables
    """
    if not snapshots:
        return 0
    
    for snapshot in snapshots:
        tables = snapshot.get("tables", [])
        if tables:
            return len(tables)
    
    return 0


def get_simulation_parameters_from_metadata(metadata: Dict) -> Dict[str, Any]:
    """Extract simulation parameters from log metadata.
    
    Args:
        metadata: Metadata dictionary from log file
        
    Returns:
        Dictionary of simulation parameters
    """
    return {
        "simulation_duration": metadata.get("simulation_duration", 0),
        "num_parties": metadata.get("num_parties", 0),
        "num_dishes": metadata.get("num_dishes", 0),
        "total_revenue": metadata.get("total_revenue", 0),
        "num_snapshots": metadata.get("num_snapshots", 0),
        "num_events": metadata.get("num_events", 0),
    }


def find_snapshot_index_at_time(snapshots: List[Dict], target_time: float) -> int:
    """Find the index of the snapshot closest to the target time.
    
    Uses binary search for efficiency.
    
    Args:
        snapshots: List of snapshot dictionaries with 'time' field
        target_time: Target time in minutes
        
    Returns:
        Index of the closest snapshot
    """
    if not snapshots:
        return 0
    
    times = [s.get("time", 0) for s in snapshots]
    
    # Use bisect to find insertion point
    idx = bisect.bisect_left(times, target_time)
    
    # Handle edge cases
    if idx == 0:
        return 0
    if idx == len(times):
        return len(times) - 1
    
    # Return closer of the two adjacent snapshots
    if target_time - times[idx - 1] < times[idx] - target_time:
        return idx - 1
    return idx


def get_snapshot_at_time(snapshots: List[Dict], target_time: float) -> Optional[Dict]:
    """Get the snapshot closest to the target time.
    
    Args:
        snapshots: List of snapshot dictionaries
        target_time: Target time in minutes
        
    Returns:
        Snapshot dictionary or None if no snapshots
    """
    if not snapshots:
        return None
    
    idx = find_snapshot_index_at_time(snapshots, target_time)
    return snapshots[idx]


def get_time_range(snapshots: List[Dict]) -> tuple:
    """Get the time range covered by snapshots.
    
    Args:
        snapshots: List of snapshot dictionaries
        
    Returns:
        Tuple of (min_time, max_time) in minutes
    """
    if not snapshots:
        return (0.0, 0.0)
    
    times = [s.get("time", 0) for s in snapshots]
    return (min(times), max(times))


def count_occupied_tables(snapshot: Dict) -> int:
    """Count the number of occupied tables in a snapshot.
    
    Args:
        snapshot: Snapshot dictionary
        
    Returns:
        Number of occupied tables
    """
    tables = snapshot.get("tables", [])
    return sum(1 for t in tables if t.get("party_id") is not None)


def count_available_tables(snapshot: Dict) -> int:
    """Count the number of available tables in a snapshot.
    
    Args:
        snapshot: Snapshot dictionary
        
    Returns:
        Number of available tables
    """
    tables = snapshot.get("tables", [])
    return sum(1 for t in tables if t.get("is_available", False))


def get_station_names(snapshots: List[Dict]) -> List[str]:
    """Extract unique station names from snapshots.
    
    Args:
        snapshots: List of snapshot dictionaries
        
    Returns:
        List of station names
    """
    station_names = set()
    
    for snapshot in snapshots:
        stations = snapshot.get("stations", [])
        for station in stations:
            name = station.get("name")
            if name:
                station_names.add(name)
    
    return sorted(list(station_names))


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero.
    
    Args:
        numerator: The numerator
        denominator: The denominator
        default: Value to return if denominator is zero
        
    Returns:
        Result of division or default value
    """
    if denominator == 0:
        return default
    return numerator / denominator


def extract_staff_config_from_metadata(metadata: Dict) -> Dict[str, int]:
    """Extract staff configuration from simulation metadata.
    
    Args:
        metadata: Metadata dictionary from log file
        
    Returns:
        Dictionary with staff counts (num_servers, num_cooks, etc.)
    """
    staff_config = {}
    
    # Try to extract from metadata
    if metadata:
        staff_config['num_servers'] = metadata.get('num_servers', 0)
        staff_config['num_cooks'] = metadata.get('num_cooks', 0)
        staff_config['num_hosts'] = metadata.get('num_hosts', 0)
        staff_config['num_food_runners'] = metadata.get('num_food_runners', 0)
        staff_config['num_bussers'] = metadata.get('num_bussers', 0)
    
    # If not found in metadata, return defaults
    if not any(staff_config.values()):
        staff_config = {
            'num_servers': 6,
            'num_cooks': 9,
            'num_hosts': 1,
            'num_food_runners': 2,
            'num_bussers': 0
        }
    
    return staff_config


