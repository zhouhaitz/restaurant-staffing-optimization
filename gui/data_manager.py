"""Data persistence and comparison utilities.

This module provides functions for:
- Saving/loading simulation configurations
- Saving/loading simulation results
- Comparing multiple simulation runs
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import sys

# Add experiments directory to path
experiments_path = Path(__file__).parent.parent / "experiments"
sys.path.insert(0, str(experiments_path))

from parameters import SingleDishParameters
from metrics_calculator import calculate_summary_statistics


def save_simulation_config(params: SingleDishParameters, filepath: str) -> bool:
    """Save simulation configuration to JSON file.
    
    Args:
        params: Simulation parameters
        filepath: Path to save JSON file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        config_dict = {
            "table_config": params.table_config,
            "simulation_duration": params.simulation_duration,
            "num_servers": params.num_servers,
            "num_hosts": params.num_hosts,
            "num_food_runners": params.num_food_runners,
            "num_bussers": params.num_bussers,
            "num_cooks": params.num_cooks,
            "wood_grill_capacity": params.wood_grill_capacity,
            "salad_station_capacity": params.salad_station_capacity,
            "sautee_station_capacity": params.sautee_station_capacity,
            "tortilla_station_capacity": params.tortilla_station_capacity,
            "guac_station_capacity": params.guac_station_capacity,
            "lambda_base": params.lambda_base,
            "lambda_peak_multiplier": params.lambda_peak_multiplier,
            "peak_time": params.peak_time,
            "peak_width": params.peak_width,
            "seed": params.seed,
            "price_per_dish": params.price_per_dish,
            "expo_capacity": params.expo_capacity,
            "saved_at": datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        return True
    
    except Exception as e:
        print(f"Error saving configuration: {e}")
        return False


def load_simulation_config(filepath: str, base_params: Optional[SingleDishParameters] = None) -> Optional[SingleDishParameters]:
    """Load simulation configuration from JSON file.
    
    Args:
        filepath: Path to JSON file
        base_params: Base parameters to copy recipes and other settings from
    
    Returns:
        SingleDishParameters object or None if error
    """
    try:
        with open(filepath, 'r') as f:
            config_dict = json.load(f)
        
        # If base_params not provided, need to load from default
        if base_params is None:
            from dish_loading import load_recipes_from_json
            base_config_path = Path(__file__).parent.parent / "experiments" / "comal_recipes.json"
            base_params = load_recipes_from_json(str(base_config_path))
        
        # Create new parameters with loaded config
        params = SingleDishParameters(
            table_config=config_dict.get("table_config", base_params.table_config),
            simulation_duration=config_dict.get("simulation_duration", base_params.simulation_duration),
            num_servers=config_dict.get("num_servers", base_params.num_servers),
            num_hosts=config_dict.get("num_hosts", base_params.num_hosts),
            num_food_runners=config_dict.get("num_food_runners", base_params.num_food_runners),
            num_bussers=config_dict.get("num_bussers", base_params.num_bussers),
            num_cooks=config_dict.get("num_cooks", base_params.num_cooks),
            wood_grill_capacity=config_dict.get("wood_grill_capacity", base_params.wood_grill_capacity),
            salad_station_capacity=config_dict.get("salad_station_capacity", base_params.salad_station_capacity),
            sautee_station_capacity=config_dict.get("sautee_station_capacity", base_params.sautee_station_capacity),
            tortilla_station_capacity=config_dict.get("tortilla_station_capacity", base_params.tortilla_station_capacity),
            guac_station_capacity=config_dict.get("guac_station_capacity", base_params.guac_station_capacity),
            lambda_base=config_dict.get("lambda_base", base_params.lambda_base),
            lambda_peak_multiplier=config_dict.get("lambda_peak_multiplier", base_params.lambda_peak_multiplier),
            peak_time=config_dict.get("peak_time", base_params.peak_time),
            peak_width=config_dict.get("peak_width", base_params.peak_width),
            seed=config_dict.get("seed", base_params.seed),
            price_per_dish=config_dict.get("price_per_dish", base_params.price_per_dish),
            expo_capacity=config_dict.get("expo_capacity", base_params.expo_capacity),
            # Copy from base
            dish_recipes=base_params.dish_recipes,
            menu_distribution=base_params.menu_distribution,
            menu_catalog=base_params.menu_catalog,
            enable_logging=True,
            enable_event_logging=True,
            min_snapshot_interval=2.0,
        )
        
        return params
    
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return None


def save_simulation_results(results: Dict, filepath: str, config: Optional[Dict] = None) -> bool:
    """Save simulation results to JSON file.
    
    Args:
        results: Log data structure (snapshots, events, metadata)
        filepath: Path to save JSON file
        config: Optional configuration dict to include
    
    Returns:
        True if successful, False otherwise
    """
    try:
        output = {
            "saved_at": datetime.now().isoformat(),
            "metadata": results.get("metadata", {}),
            "snapshots": results.get("snapshots", []),
            "events": results.get("events", [])
        }
        
        if config:
            output["config"] = config
        
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)
        
        return True
    
    except Exception as e:
        print(f"Error saving results: {e}")
        return False


def load_simulation_results(filepath: str) -> Optional[Dict]:
    """Load simulation results from JSON file.
    
    Args:
        filepath: Path to JSON file
    
    Returns:
        Dictionary with results or None if error
    """
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        return data
    
    except Exception as e:
        print(f"Error loading results: {e}")
        return None


def extract_run_metrics(results: Dict, run_name: str = "Run") -> Dict:
    """Extract key metrics from simulation results for comparison.
    
    Args:
        results: Simulation results with snapshots
        run_name: Name to identify this run
    
    Returns:
        Dictionary of key metrics
    """
    try:
        snapshots = results.get("snapshots", [])
        if not snapshots:
            return {"run_name": run_name, "error": "No snapshots"}
        
        # Calculate summary statistics
        stats = calculate_summary_statistics(snapshots)
        
        # Extract key metrics
        metrics = {
            "run_name": run_name,
            "duration_hours": stats.get("duration_hours", 0),
            "parties_served": stats.get("parties_served", 0),
            "total_revenue": stats.get("total_revenue", 0),
            "final_revpash": stats.get("final_revpash", 0),
            "average_table_utilization": stats.get("average_table_utilization", 0),
            "peak_table_utilization": stats.get("peak_table_utilization", 0),
            "average_guest_queue": stats.get("average_guest_queue", 0),
            "max_guest_queue": stats.get("max_guest_queue", 0),
        }
        
        # Add configuration if available
        config = results.get("config", {})
        if config:
            metrics["num_servers"] = config.get("num_servers", "N/A")
            metrics["num_cooks"] = config.get("num_cooks", "N/A")
            metrics["total_tables"] = len(config.get("table_config", []))
        
        return metrics
    
    except Exception as e:
        return {"run_name": run_name, "error": str(e)}


def compare_simulations(results_list: List[Dict], run_names: Optional[List[str]] = None) -> pd.DataFrame:
    """Compare multiple simulation runs.
    
    Args:
        results_list: List of simulation result dictionaries
        run_names: Optional list of names for each run
    
    Returns:
        DataFrame with comparison of key metrics
    """
    if run_names is None:
        run_names = [f"Run {i+1}" for i in range(len(results_list))]
    
    # Extract metrics for each run
    metrics_list = []
    for i, results in enumerate(results_list):
        metrics = extract_run_metrics(results, run_names[i])
        metrics_list.append(metrics)
    
    # Create DataFrame
    df = pd.DataFrame(metrics_list)
    
    return df


def format_comparison_table(comparison_df: pd.DataFrame) -> pd.DataFrame:
    """Format comparison DataFrame for display.
    
    Args:
        comparison_df: Raw comparison DataFrame
    
    Returns:
        Formatted DataFrame
    """
    if comparison_df.empty:
        return comparison_df
    
    # Create a copy for formatting
    df = comparison_df.copy()
    
    # Format specific columns
    if "total_revenue" in df.columns:
        df["total_revenue"] = df["total_revenue"].apply(lambda x: f"${x:,.2f}" if isinstance(x, (int, float)) else x)
    
    if "final_revpash" in df.columns:
        df["final_revpash"] = df["final_revpash"].apply(lambda x: f"${x:.2f}" if isinstance(x, (int, float)) else x)
    
    if "average_table_utilization" in df.columns:
        df["average_table_utilization"] = df["average_table_utilization"].apply(
            lambda x: f"{x:.1%}" if isinstance(x, (int, float)) else x
        )
    
    if "peak_table_utilization" in df.columns:
        df["peak_table_utilization"] = df["peak_table_utilization"].apply(
            lambda x: f"{x:.1%}" if isinstance(x, (int, float)) else x
        )
    
    if "duration_hours" in df.columns:
        df["duration_hours"] = df["duration_hours"].apply(lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else x)
    
    # Rename columns for display
    column_names = {
        "run_name": "Run Name",
        "duration_hours": "Duration (hrs)",
        "parties_served": "Parties Served",
        "total_revenue": "Total Revenue",
        "final_revpash": "RevPASH",
        "average_table_utilization": "Avg Table Util.",
        "peak_table_utilization": "Peak Table Util.",
        "average_guest_queue": "Avg Guest Queue",
        "max_guest_queue": "Max Guest Queue",
        "num_servers": "Servers",
        "num_cooks": "Cooks",
        "total_tables": "Tables"
    }
    
    df = df.rename(columns=column_names)
    
    return df


def save_comparison_report(comparison_df: pd.DataFrame, filepath: str) -> bool:
    """Save comparison report to CSV.
    
    Args:
        comparison_df: Comparison DataFrame
        filepath: Path to save CSV file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        comparison_df.to_csv(filepath, index=False)
        return True
    except Exception as e:
        print(f"Error saving comparison report: {e}")
        return False


def create_run_summary(results: Dict, config: Optional[Dict] = None) -> str:
    """Create a text summary of a simulation run.
    
    Args:
        results: Simulation results
        config: Optional configuration
    
    Returns:
        Formatted text summary
    """
    metrics = extract_run_metrics(results, "Current Run")
    
    summary = f"""
# Simulation Run Summary

## Performance Metrics
- **Duration**: {metrics.get('duration_hours', 0):.2f} hours
- **Parties Served**: {metrics.get('parties_served', 0)}
- **Total Revenue**: ${metrics.get('total_revenue', 0):,.2f}
- **RevPASH**: ${metrics.get('final_revpash', 0):.2f}

## Utilization
- **Average Table Utilization**: {metrics.get('average_table_utilization', 0):.1%}
- **Peak Table Utilization**: {metrics.get('peak_table_utilization', 0):.1%}

## Queue Performance
- **Average Guest Queue**: {metrics.get('average_guest_queue', 0):.1f}
- **Max Guest Queue**: {metrics.get('max_guest_queue', 0)}

"""
    
    if config:
        summary += f"""
## Configuration
- **Servers**: {config.get('num_servers', 'N/A')}
- **Cooks**: {config.get('num_cooks', 'N/A')}
- **Tables**: {len(config.get('table_config', []))}
- **Simulation Duration**: {config.get('simulation_duration', 'N/A')} minutes
"""
    
    return summary

