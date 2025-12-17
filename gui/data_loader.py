"""Data loading and parsing for Restaurant Simulation GUI.

This module handles loading JSON log files exported from the restaurant simulation,
validating the structure, and filtering to maximum time ranges.
"""

import json
from typing import Dict, List, Tuple, Optional, Any, Union
from pathlib import Path
import io

try:
    from .utils import convert_hours_to_minutes
except ImportError:
    from utils import convert_hours_to_minutes


class LogValidationError(Exception):
    """Raised when log file validation fails."""
    pass


def load_log_file(file_source: Union[str, Path, io.BytesIO]) -> Dict[str, Any]:
    """Load and parse a JSON log file from the restaurant simulation.
    
    Handles the format produced by `simulation.export_all_logs_to_json()`.
    
    Args:
        file_source: Either a file path (str or Path) or a file-like object
                    (e.g., from Streamlit file uploader)
        
    Returns:
        Dictionary containing:
            - metadata: Simulation metadata
            - snapshots: List of state snapshots
            - events: List of events (may be empty if not included)
            
    Raises:
        LogValidationError: If the file is invalid or missing required fields
        FileNotFoundError: If the file path doesn't exist
        json.JSONDecodeError: If the file is not valid JSON
    """
    try:
        # Handle different input types
        if isinstance(file_source, (str, Path)):
            with open(file_source, 'r') as f:
                data = json.load(f)
        elif hasattr(file_source, 'read'):
            # File-like object (e.g., from Streamlit uploader)
            content = file_source.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            data = json.loads(content)
        else:
            raise LogValidationError(f"Unsupported file source type: {type(file_source)}")
    except json.JSONDecodeError as e:
        raise LogValidationError(f"Invalid JSON format: {e}")
    except FileNotFoundError:
        raise LogValidationError(f"File not found: {file_source}")
    
    # Validate structure
    validate_log_structure(data)
    
    return data


def validate_log_structure(data: Dict[str, Any]) -> None:
    """Validate the structure of loaded log data.
    
    Args:
        data: Loaded JSON data dictionary
        
    Raises:
        LogValidationError: If required fields are missing or invalid
    """
    if not isinstance(data, dict):
        raise LogValidationError("Log data must be a dictionary")
    
    # Check for required top-level fields
    if "metadata" not in data:
        raise LogValidationError("Missing 'metadata' field in log file")
    
    if "snapshots" not in data:
        raise LogValidationError("Missing 'snapshots' field in log file")
    
    metadata = data["metadata"]
    if not isinstance(metadata, dict):
        raise LogValidationError("'metadata' must be a dictionary")
    
    snapshots = data["snapshots"]
    if not isinstance(snapshots, list):
        raise LogValidationError("'snapshots' must be a list")
    
    # Validate snapshots have required fields
    if snapshots:
        first_snapshot = snapshots[0]
        required_fields = ["time"]
        for field in required_fields:
            if field not in first_snapshot:
                raise LogValidationError(f"Snapshots missing required field: '{field}'")
    
    # Events are optional
    events = data.get("events", [])
    if not isinstance(events, list):
        raise LogValidationError("'events' must be a list if present")


def filter_time_range(
    snapshots: List[Dict],
    events: List[Dict],
    max_hours: float = 4.0,
    start_time_minutes: float = 0.0
) -> Tuple[List[Dict], List[Dict]]:
    """Filter snapshots and events to a maximum time range.
    
    Args:
        snapshots: List of snapshot dictionaries
        events: List of event dictionaries
        max_hours: Maximum duration in hours (default: 4.0)
        start_time_minutes: Start time offset in minutes (default: 0.0)
        
    Returns:
        Tuple of (filtered_snapshots, filtered_events)
    """
    max_minutes = convert_hours_to_minutes(max_hours)
    end_time = start_time_minutes + max_minutes
    
    filtered_snapshots = [
        s for s in snapshots
        if start_time_minutes <= s.get("time", 0) <= end_time
    ]
    
    filtered_events = [
        e for e in events
        if start_time_minutes <= e.get("timestamp", 0) <= end_time
    ]
    
    return filtered_snapshots, filtered_events


def get_log_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """Get a summary of the log file contents.
    
    Args:
        data: Loaded log data dictionary
        
    Returns:
        Summary dictionary with key statistics
    """
    metadata = data.get("metadata", {})
    snapshots = data.get("snapshots", [])
    events = data.get("events", [])
    
    # Calculate time range
    if snapshots:
        times = [s.get("time", 0) for s in snapshots]
        min_time = min(times)
        max_time = max(times)
        duration_minutes = max_time - min_time
    else:
        min_time = max_time = duration_minutes = 0
    
    # Count event types
    event_type_counts = {}
    for event in events:
        event_type = event.get("event_type", "unknown")
        event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
    
    # Get final revenue if available
    final_revenue = 0
    if snapshots:
        final_revenue = snapshots[-1].get("total_revenue", 0)
    
    return {
        "simulation_duration": metadata.get("simulation_duration", duration_minutes),
        "num_parties": metadata.get("num_parties", 0),
        "num_dishes": metadata.get("num_dishes", 0),
        "total_revenue": metadata.get("total_revenue", final_revenue),
        "num_snapshots": len(snapshots),
        "num_events": len(events),
        "time_range": (min_time, max_time),
        "duration_minutes": duration_minutes,
        "duration_hours": duration_minutes / 60.0,
        "event_type_counts": event_type_counts,
    }


def extract_parties(snapshots: List[Dict]) -> List[Dict]:
    """Extract all unique parties from snapshots.
    
    Args:
        snapshots: List of snapshot dictionaries
        
    Returns:
        List of unique party dictionaries (latest state for each party)
    """
    parties_by_id = {}
    
    for snapshot in snapshots:
        for party in snapshot.get("parties", []):
            party_id = party.get("id")
            if party_id is not None:
                parties_by_id[party_id] = party
    
    return list(parties_by_id.values())


def extract_dishes(snapshots: List[Dict]) -> List[Dict]:
    """Extract all unique dishes from snapshots.
    
    Args:
        snapshots: List of snapshot dictionaries
        
    Returns:
        List of unique dish dictionaries (latest state for each dish)
    """
    dishes_by_id = {}
    
    for snapshot in snapshots:
        for dish in snapshot.get("dishes", []):
            dish_id = dish.get("id")
            if dish_id is not None:
                dishes_by_id[dish_id] = dish
    
    return list(dishes_by_id.values())


def get_events_in_range(
    events: List[Dict],
    start_time: float,
    end_time: float
) -> List[Dict]:
    """Get events within a specific time range.
    
    Args:
        events: List of event dictionaries
        start_time: Start time in minutes
        end_time: End time in minutes
        
    Returns:
        List of events within the time range
    """
    return [
        e for e in events
        if start_time <= e.get("timestamp", 0) <= end_time
    ]


def group_events_by_type(events: List[Dict]) -> Dict[str, List[Dict]]:
    """Group events by their event type.
    
    Args:
        events: List of event dictionaries
        
    Returns:
        Dictionary mapping event types to lists of events
    """
    grouped = {}
    
    for event in events:
        event_type = event.get("event_type", "unknown")
        if event_type not in grouped:
            grouped[event_type] = []
        grouped[event_type].append(event)
    
    return grouped


def load_and_prepare_data(
    file_source: Union[str, Path, io.BytesIO],
    max_hours: float = 4.0
) -> Dict[str, Any]:
    """Load, validate, and prepare log data for visualization.
    
    This is the main entry point for loading log data. It:
    1. Loads the JSON file
    2. Validates the structure
    3. Filters to the maximum time range
    4. Computes summary statistics
    
    Args:
        file_source: File path or file-like object
        max_hours: Maximum time range in hours (default: 4.0)
        
    Returns:
        Dictionary containing:
            - metadata: Original metadata
            - snapshots: Filtered snapshots
            - events: Filtered events
            - summary: Computed summary statistics
    """
    # Load and validate
    data = load_log_file(file_source)
    
    # Filter to time range
    snapshots = data.get("snapshots", [])
    events = data.get("events", [])
    filtered_snapshots, filtered_events = filter_time_range(
        snapshots, events, max_hours=max_hours
    )
    
    # Prepare result
    result = {
        "metadata": data.get("metadata", {}),
        "snapshots": filtered_snapshots,
        "events": filtered_events,
        "summary": get_log_summary({
            "metadata": data.get("metadata", {}),
            "snapshots": filtered_snapshots,
            "events": filtered_events,
        }),
    }
    
    return result

