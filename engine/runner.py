"""Convenience function to run restaurant simulation."""
from typing import Dict, Optional

from parameters import SingleDishParameters
from simulation import SingleDishRestaurantSim
from results import print_results


def run_single_dish_sim(params: Optional[SingleDishParameters] = None, verbose: bool = False) -> Dict[str, float]:
    """Convenience function to run the simulation and return results.
    
    Args:
        params: Simulation parameters (uses defaults if None)
        verbose: If True, print formatted results
    
    Returns:
        Dictionary of simulation results
    """
    params = params or SingleDishParameters()
    sim = SingleDishRestaurantSim(params)
    results = sim.run()
    
    # Add config to results for formatting
    results['num_tables'] = params.num_tables
    results['num_servers'] = params.num_servers
    results['num_cooks'] = params.num_cooks
    results['simulation_duration'] = params.simulation_duration
    
    if verbose:
        print_results(results)
    
    return results

