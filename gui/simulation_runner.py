"""Simulation execution and result management for GUI.

This module provides functions to run simulations directly from the GUI,
convert results to the expected log format, and manage simulation configurations.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional, Callable
import time

# Add experiments directory to path FIRST (before gui imports)
# This ensures simulation.py imports the correct utils module
experiments_path = Path(__file__).parent.parent / "experiments"
if str(experiments_path) in sys.path:
    sys.path.remove(str(experiments_path))
sys.path.insert(0, str(experiments_path))

from parameters import SingleDishParameters
from simulation import RestaurantSimulation
from results import calculate_results


def run_simulation_with_progress(
    params: SingleDishParameters, 
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Dict[str, Any]:
    """Run simulation with progress tracking.
    
    Args:
        params: Simulation parameters
        progress_callback: Optional callback function(progress: float, status: str)
                          where progress is 0.0-1.0
    
    Returns:
        Dictionary containing simulation results and log data
    
    Raises:
        Exception: If simulation fails
    """
    try:
        if progress_callback:
            progress_callback(0.0, "Initializing simulation...")
        
        # Create simulation instance
        sim = RestaurantSimulation(params)
        
        if progress_callback:
            progress_callback(0.1, "Running simulation...")
        
        # Run simulation
        start_time = time.time()
        results = sim.run()
        elapsed_time = time.time() - start_time
        
        if progress_callback:
            progress_callback(0.8, "Collecting results...")
        
        # Convert to log format
        log_data = convert_simulation_to_log_format(sim, params)
        
        if progress_callback:
            progress_callback(1.0, f"Complete! ({elapsed_time:.1f}s)")
        
        return {
            'success': True,
            'log_data': log_data,
            'results': results,
            'elapsed_time': elapsed_time,
            'params': params
        }
        
    except Exception as e:
        if progress_callback:
            progress_callback(0.0, f"Error: {str(e)}")
        raise


def convert_simulation_to_log_format(
    sim: RestaurantSimulation, 
    params: SingleDishParameters
) -> Dict[str, Any]:
    """Convert simulation results to log file format.
    
    Args:
        sim: Completed simulation instance
        params: Simulation parameters
        
    Returns:
        Dictionary in log file format compatible with data_loader
    """
    # Extract metadata
    metadata = {
        "simulation_duration": params.simulation_duration,
        "num_parties": len(sim.parties),
        "num_dishes": len(sim.all_dishes),
        "total_revenue": sim.total_revenue,
        "num_snapshots": len(sim.snapshot_history),
        "num_events": len(sim.event_log),
        # Staff configuration for labor cost calculations
        "num_servers": params.num_servers,
        "num_cooks": params.num_cooks,
        "num_hosts": params.num_hosts,
        "num_food_runners": params.num_food_runners,
        "num_bussers": params.num_bussers,
        # Wages
        "wages": {
            "server_hourly_wage": params.server_hourly_wage,
            "cook_hourly_wage": params.cook_hourly_wage,
            "host_hourly_wage": params.host_hourly_wage,
            "food_runner_hourly_wage": params.food_runner_hourly_wage,
            "busser_hourly_wage": params.busser_hourly_wage,
        },
        # Additional config
        "table_config": params.table_config,
        "seed": params.seed,
    }
    
    # Build log structure
    log_data = {
        "metadata": metadata,
        "snapshots": sim.snapshot_history,
        "events": sim.event_log,
    }
    
    return log_data


def save_simulation_config(params: SingleDishParameters, filename: str) -> None:
    """Save simulation configuration to JSON file.
    
    Args:
        params: Simulation parameters
        filename: Name of file to save (without path)
    """
    # Create saved_configs directory if it doesn't exist
    config_dir = Path(__file__).parent / "saved_configs"
    config_dir.mkdir(exist_ok=True)
    
    filepath = config_dir / filename
    
    # Convert parameters to dictionary
    config_dict = {
        "simulation_duration": params.simulation_duration,
        "num_servers": params.num_servers,
        "num_cooks": params.num_cooks,
        "num_hosts": params.num_hosts,
        "num_food_runners": params.num_food_runners,
        "num_bussers": params.num_bussers,
        "table_config": params.table_config,
        "seed": params.seed,
        "server_hourly_wage": params.server_hourly_wage,
        "cook_hourly_wage": params.cook_hourly_wage,
        "host_hourly_wage": params.host_hourly_wage,
        "food_runner_hourly_wage": params.food_runner_hourly_wage,
        "busser_hourly_wage": params.busser_hourly_wage,
    }
    
    with open(filepath, 'w') as f:
        json.dump(config_dict, f, indent=2)


def load_simulation_config(filename: str) -> SingleDishParameters:
    """Load simulation configuration from JSON file.
    
    Args:
        filename: Name of file to load (without path)
        
    Returns:
        SingleDishParameters object
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    config_dir = Path(__file__).parent / "saved_configs"
    filepath = config_dir / filename
    
    if not filepath.exists():
        raise FileNotFoundError(f"Configuration file not found: {filename}")
    
    with open(filepath, 'r') as f:
        config_dict = json.load(f)
    
    # Create SingleDishParameters from loaded config
    # Note: This assumes default values for parameters not in config
    params = SingleDishParameters(
        simulation_duration=config_dict.get("simulation_duration", 240),
        num_servers=config_dict.get("num_servers", 6),
        num_cooks=config_dict.get("num_cooks", 9),
        num_hosts=config_dict.get("num_hosts", 1),
        num_food_runners=config_dict.get("num_food_runners", 2),
        num_bussers=config_dict.get("num_bussers", 0),
        table_config=config_dict.get("table_config", None),
        seed=config_dict.get("seed", 42),
        server_hourly_wage=config_dict.get("server_hourly_wage", 34.73),
        cook_hourly_wage=config_dict.get("cook_hourly_wage", 22.60),
        host_hourly_wage=config_dict.get("host_hourly_wage", 20.40),
        food_runner_hourly_wage=config_dict.get("food_runner_hourly_wage", 21.80),
        busser_hourly_wage=config_dict.get("busser_hourly_wage", 25.00),
    )
    
    return params


def estimate_simulation_runtime(params: SingleDishParameters) -> float:
    """Estimate simulation runtime in seconds.
    
    Uses heuristic: base time + complexity multiplier
    
    Args:
        params: Simulation parameters
        
    Returns:
        Estimated runtime in seconds
    """
    # Base: ~1 second per minute of simulation
    base_time = params.simulation_duration / 60.0
    
    # Complexity multiplier based on staff
    complexity = (params.num_servers + params.num_cooks) / 15.0
    
    estimated_time = base_time * (1 + complexity)
    
    return max(1.0, estimated_time)  # At least 1 second


def list_saved_configs() -> list[str]:
    """List all saved configuration files.
    
    Returns:
        List of configuration filenames
    """
    config_dir = Path(__file__).parent / "saved_configs"
    
    if not config_dir.exists():
        return []
    
    return [f.name for f in config_dir.glob("*.json")]

