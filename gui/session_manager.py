"""Session state management for simulation data.

This module handles storing, loading, and managing multiple simulations
in Streamlit session state.
"""

import streamlit as st
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

try:
    from parameters import SingleDishParameters
except ImportError:
    import sys
    from pathlib import Path
    experiments_path = Path(__file__).parent.parent / "experiments"
    sys.path.insert(0, str(experiments_path))
    from parameters import SingleDishParameters


def save_simulation_to_session(
    simulation_data: Dict[str, Any],
    config: SingleDishParameters,
    label: Optional[str] = None
) -> str:
    """Save simulation data to session state.
    
    Args:
        simulation_data: Complete simulation data (log format)
        config: Simulation parameters used
        label: Optional label for this simulation
        
    Returns:
        Session key for this simulation
    """
    # Initialize simulations dict if it doesn't exist
    if 'simulations' not in st.session_state:
        st.session_state.simulations = {}
    
    # Generate unique key
    timestamp = datetime.now()
    session_key = f"sim_{timestamp.strftime('%Y%m%d_%H%M%S')}"
    
    # Create simulation entry
    sim_entry = {
        'data': simulation_data,
        'config': config,
        'timestamp': timestamp,
        'label': label or f"Simulation {len(st.session_state.simulations) + 1}",
        'metadata': {
            'duration': simulation_data.get('metadata', {}).get('simulation_duration', 0),
            'parties': simulation_data.get('metadata', {}).get('num_parties', 0),
            'revenue': simulation_data.get('metadata', {}).get('total_revenue', 0),
            'num_servers': config.num_servers,
            'num_cooks': config.num_cooks,
        }
    }
    
    # Save to session
    st.session_state.simulations[session_key] = sim_entry
    st.session_state.current_simulation_key = session_key
    
    return session_key


def load_simulation_from_session(session_key: str) -> Dict[str, Any]:
    """Load simulation data from session state.
    
    Args:
        session_key: Key of simulation to load
        
    Returns:
        Simulation data dictionary
        
    Raises:
        KeyError: If session_key not found
    """
    if 'simulations' not in st.session_state:
        raise KeyError("No simulations in session")
    
    if session_key not in st.session_state.simulations:
        raise KeyError(f"Simulation {session_key} not found")
    
    sim_entry = st.session_state.simulations[session_key]
    st.session_state.current_simulation_key = session_key
    
    return sim_entry['data']


def list_available_simulations() -> List[Dict[str, Any]]:
    """List all available simulations in session.
    
    Returns:
        List of simulation metadata dictionaries
    """
    if 'simulations' not in st.session_state:
        return []
    
    simulations = []
    for key, sim_entry in st.session_state.simulations.items():
        simulations.append({
            'key': key,
            'label': sim_entry['label'],
            'timestamp': sim_entry['timestamp'],
            'metadata': sim_entry['metadata']
        })
    
    # Sort by timestamp descending (most recent first)
    simulations.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return simulations


def get_current_simulation() -> Optional[Dict[str, Any]]:
    """Get currently active simulation.
    
    Returns:
        Current simulation data or None if no simulation loaded
    """
    if 'current_simulation_key' not in st.session_state:
        return None
    
    if 'simulations' not in st.session_state:
        return None
    
    key = st.session_state.current_simulation_key
    if key not in st.session_state.simulations:
        return None
    
    return st.session_state.simulations[key]['data']


def get_current_simulation_config() -> Optional[SingleDishParameters]:
    """Get configuration of currently active simulation.
    
    Returns:
        Configuration parameters or None
    """
    if 'current_simulation_key' not in st.session_state:
        return None
    
    if 'simulations' not in st.session_state:
        return None
    
    key = st.session_state.current_simulation_key
    if key not in st.session_state.simulations:
        return None
    
    return st.session_state.simulations[key]['config']


def clear_simulation_data() -> None:
    """Clear current simulation from session state."""
    if 'current_simulation_key' in st.session_state:
        del st.session_state.current_simulation_key
    
    if 'data' in st.session_state:
        st.session_state.data = None
    
    if 'player' in st.session_state:
        st.session_state.player = None
    
    if 'current_time' in st.session_state:
        st.session_state.current_time = 0.0
    
    if 'is_playing' in st.session_state:
        st.session_state.is_playing = False


def clear_all_simulations() -> None:
    """Clear all simulations from session state."""
    if 'simulations' in st.session_state:
        st.session_state.simulations = {}
    
    clear_simulation_data()


def get_simulation_summary(session_key: str) -> str:
    """Get a summary string for a simulation.
    
    Args:
        session_key: Key of simulation
        
    Returns:
        Summary string
    """
    if 'simulations' not in st.session_state:
        return "No simulation"
    
    if session_key not in st.session_state.simulations:
        return "Not found"
    
    sim_entry = st.session_state.simulations[session_key]
    meta = sim_entry['metadata']
    
    summary = (
        f"{sim_entry['label']} | "
        f"{meta['duration']}min | "
        f"{meta['parties']} parties | "
        f"${meta['revenue']:,.0f} revenue | "
        f"{meta['num_servers']}S {meta['num_cooks']}C"
    )
    
    return summary


def export_simulation_to_json(session_key: str, filepath: str) -> None:
    """Export a simulation to JSON file.
    
    Args:
        session_key: Key of simulation to export
        filepath: Path to save JSON file
    """
    if 'simulations' not in st.session_state:
        raise KeyError("No simulations in session")
    
    if session_key not in st.session_state.simulations:
        raise KeyError(f"Simulation {session_key} not found")
    
    sim_entry = st.session_state.simulations[session_key]
    data = sim_entry['data']
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

