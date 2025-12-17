"""Simulation parameters configuration."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class SingleDishParameters:
    # Structure
    num_tables: int = 20
    avg_seats_per_table: float = 4.0
    simulation_duration: float = 240.0  # minutes (4 hours)
    
    # Table configuration: list of table sizes.
    # Default: 23 tables of 2, 11 tables of 4, 6 tables of 6, 1 table of 10 (total: 41 tables)
    table_config: Optional[List[int]] = field(default_factory=lambda: [2]*23 + [4]*11 + [6]*6 + [10])

    # Arrival NHPP parameters (same shape as before, adjustable)
    # lambda_base: float = 0.08
    # lambda_peak_multiplier: float = 0.6
    # peak_time: float = 120.0
    # peak_width: float = 60.0

    # Fitted Parameters:
    lambda_base: float = 0.036463  # parties/min
    lambda_peak_multiplier: float = 0.491057  # parties/min
    peak_time: float = 57.39  # minutes (357.39 - 300.0, relative to simulation start)
    peak_width: float = 92.84  # minutes

    # ==========================================================================
    # STAFF RESOURCES
    # ==========================================================================
    
    # Front of House (FOH)
    num_servers: int = 6  # Also determines number of zones
    num_hosts: int = 1
    num_food_runners: int = 2
    num_bussers: int = 0
    
    # Back of House (BOH) - Cooking Stations
    # Each station has a capacity (number of concurrent dishes it can handle)
    wood_grill_capacity: int = 2
    salad_station_capacity: int = 3
    sautee_station_capacity: int = 2
    tortilla_station_capacity: int = 3
    guac_station_capacity: int = 2
    
    # Expo (quality check staging area)
    expo_capacity: int = 2  # Number of dishes that can be checked simultaneously
    expo_check_time_mean: float = 0.2  # minutes to check a dish
    expo_check_time_std: float = 0.05
    
    # Legacy: num_cooks kept for backward compatibility
    num_cooks: int = 9
    
    # ==========================================================================
    # LABOR COSTS (USD per hour)
    # ==========================================================================
    server_hourly_wage: float = 34.727143
    cook_hourly_wage: float = 22.6  # Line Cook
    host_hourly_wage: float = 20.4
    food_runner_hourly_wage: float = 21.8  # Runner
    busser_hourly_wage: float = 25.0

    # ==========================================================================
    # HOST & SEATING TIMING
    # ==========================================================================
    walking_to_table_mean: float = 0.5  # minutes to walk party to table
    walking_to_table_std: float = 0.15
    host_queue_processing_time: float = 0.1  # mini delay to process queue

    # ==========================================================================
    # SERVER STAGE SERVICE-TIME PARAMS
    # ==========================================================================
    # Decision time: party decides on orders (no server needed, scales with party size)
    decision_base_mean: float = 1.5  # Base decision time
    decision_per_person_mean: float = 0.5  # Additional time per person to decide
    decision_std: float = 0.8  # Decision time variability
    # Ordering time: server takes order (party already decided, shorter/fixed time)
    ordering_taking_mean: float = 1.5  # Time for server to take order
    ordering_taking_std: float = 0.5  # Ordering time variability
    delivery_base_mean: float = 1.0  # Base time per delivery trip (constant, not scaled by dish count)
    delivery_per_dish_mean: float = 0.3  # Deprecated: kept for backward compatibility but not used
    delivery_std: float = 0.5
    payment_base_mean: float = 2.0
    payment_per_person_mean: float = 0.3  # Additional time per person
    payment_std: float = 1.0
    
    # Cleanup time
    cleanup_base_mean: float = 3.0
    cleanup_per_person_mean: float = 0.3
    cleanup_std: float = 0.75

    # ==========================================================================
    # DINING TIME
    # ==========================================================================
    # Dining (Lognormal) tuned to ~30 minutes mean for party of 2, scales with party size
    dining_base_mu: float = 2.8  # Base mu parameter for lognormal
    dining_per_person_mu: float = 0.1  # Additional mu per person
    dining_sigma: float = 0.35
    # Legacy parameter kept for backward compatibility (computed from base)
    dining_mu: float = 3.3  # exp(mu + sigma^2/2) ≈ 27-33 for sigma ~0.35

    # ==========================================================================
    # COOKING STATION TIMING
    # ==========================================================================
    # Default dish prep times per station (Lognormal parameters: mu, sigma)
    # These are used if dish_recipes is None
    dish_mu: float = 2.0
    dish_sigma: float = 0.5
    
    # Station-specific prep times (mu, sigma) - used when component-based cooking is active
    # Example: wood_grill might take longer than salad station
    station_prep_times: Optional[Dict[str, tuple]] = None  # e.g., {"wood_grill": (2.2, 0.4), "salad_station": (1.5, 0.3)}

    # ==========================================================================
    # ORDER MODEL
    # ==========================================================================
    avg_dishes_per_person_low: float = 1.0
    avg_dishes_per_person_high: float = 1.5

    # Cook multitasking (legacy, for backward compatibility)
    cook_concurrency: int = 2
    dual_task_penalty: float = 1.25  # slowdown multiplier when cook runs 2 dishes

    # ==========================================================================
    # PRICING
    # ==========================================================================
    # Costs for RevPASH denominator only uses seats; revenue via dishes
    price_per_dish: float = 22.0
    drink_supplement: float = 0.00  # Lets not consider drinks for now

    # ==========================================================================
    # DISH RECIPES
    # ==========================================================================
    # Dish recipe configuration: maps dish types to list of station components
    # Each component is a tuple of (station_name, prep_time_mu, prep_time_sigma)
    # If None, uses legacy single-dish cooking model
    # 
    # Example configuration:
    # dish_recipes = {
    #     "taco": [
    #         ("tortilla_station", 1.5, 0.3),
    #         ("guac_station", 1.0, 0.2),
    #         ("sautee_station", 2.0, 0.4)
    #     ],
    #     "burrito": [
    #         ("tortilla_station", 2.0, 0.4),
    #         ("guac_station", 1.0, 0.2),
    #         ("sautee_station", 2.5, 0.5)
    #     ],
    #     "salad": [
    #         ("salad_station", 3.0, 0.5)
    #     ],
    #     "grilled_protein": [
    #         ("wood_grill", 5.0, 1.0)
    #     ]
    # }
    dish_recipes: Optional[Dict[str, List[tuple]]] = None
    
    # Menu: list of dish types available, with selection probabilities
    # If None, uses equal probability for all dishes in dish_recipes
    # Example: {"taco": 0.4, "burrito": 0.3, "salad": 0.2, "grilled_protein": 0.1}
    menu_distribution: Optional[Dict[str, float]] = None
    
    # Menu catalog: dish-specific pricing and descriptions
    # If None, uses legacy price_per_dish for all dishes
    # Example: {"taco": {"price": 16.0, "description": "..."}, ...}
    menu_catalog: Optional[Dict[str, Dict[str, Any]]] = None

    # ==========================================================================
    # LOGGING
    # ==========================================================================
    log_snapshot_interval: float = 30.0  # minutes between snapshot logs (legacy, used for periodic backup)
    enable_logging: bool = True  # Master switch for all logging
    
    # Event-driven logging (new)
    enable_event_logging: bool = True  # Enable event log alongside snapshots
    min_snapshot_interval: float = 0.5  # Minimum time between snapshots (minutes, default 30 seconds)
    enable_periodic_backup: bool = False  # Enable periodic backup snapshots (uses log_snapshot_interval)
    periodic_backup_interval: float = 5.0  # Interval for periodic backup snapshots if enabled (minutes)

    # ==========================================================================
    # RANDOM SEED
    # ==========================================================================
    seed: int = 42

    def lambda_t(self, t: float) -> float:
        """Calculate arrival rate at time t using NHPP with Gaussian peak."""
        return self.lambda_base + self.lambda_peak_multiplier * math.exp(-((t - self.peak_time) ** 2) / (2 * self.peak_width ** 2))
    
    def get_station_names(self) -> List[str]:
        """Return list of all station names."""
        return ["wood_grill", "salad_station", "sautee_station", "tortilla_station", "guac_station"]
    
    def get_station_capacity(self, station_name: str) -> int:
        """Return capacity for a specific station."""
        capacity_map = {
            "wood_grill": self.wood_grill_capacity,
            "salad_station": self.salad_station_capacity,
            "sautee_station": self.sautee_station_capacity,
            "tortilla_station": self.tortilla_station_capacity,
            "guac_station": self.guac_station_capacity,
        }
        return capacity_map.get(station_name, 1)

