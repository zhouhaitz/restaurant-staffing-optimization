"""Dish recipe configuration for restaurant simulation.

This module defines the recipes for different dish types, mapping each dish
to the cooking stations it requires and the preparation time at each station.

Recipe Format:
    Each recipe is a dictionary mapping dish type names to lists of components.
    Each component is a tuple of (station_name, prep_time_mu, prep_time_sigma).
    
    Components can run in PARALLEL at different stations.
    
Example:
    RECIPES = {
        "taco": [
            ("tortilla_station", 1.5, 0.3),  # Prepare tortilla
            ("guac_station", 1.0, 0.2),      # Prepare guac/salsa
            ("sautee_station", 2.0, 0.4)     # Cook protein
        ],
        "burrito": [
            ("tortilla_station", 2.0, 0.4),
            ("guac_station", 1.0, 0.2),
            ("sautee_station", 2.5, 0.5)
        ]
    }
"""
from __future__ import annotations

from typing import Dict, List, Tuple, Optional
import numpy as np


# ==========================================================================
# DEFAULT RECIPES
# ==========================================================================

# Default recipes for a Mexican restaurant
# Format: dish_type -> [(station_name, prep_time_mu, prep_time_sigma), ...]
# prep_time_mu and prep_time_sigma are parameters for lognormal distribution
DEFAULT_RECIPES: Dict[str, List[Tuple[str, float, float]]] = {
    "taco": [
        ("tortilla_station", 1.5, 0.3),
        ("guac_station", 1.0, 0.2),
        ("sautee_station", 2.0, 0.4),
    ],
    "burrito": [
        ("tortilla_station", 2.0, 0.4),
        ("guac_station", 1.2, 0.25),
        ("sautee_station", 2.5, 0.5),
    ],
    "quesadilla": [
        ("tortilla_station", 2.5, 0.4),
        ("sautee_station", 1.5, 0.3),
    ],
    "salad": [
        ("salad_station", 3.0, 0.5),
    ],
    "grilled_protein": [
        ("wood_grill", 5.0, 1.0),
    ],
    "nachos": [
        ("tortilla_station", 1.0, 0.2),
        ("guac_station", 1.5, 0.3),
        ("sautee_station", 1.5, 0.3),
    ],
    "bowl": [
        ("salad_station", 1.5, 0.3),
        ("guac_station", 1.0, 0.2),
        ("sautee_station", 2.0, 0.4),
    ],
}

# Default menu distribution (probability of each dish being ordered)
DEFAULT_MENU_DISTRIBUTION: Dict[str, float] = {
    "taco": 0.30,
    "burrito": 0.25,
    "quesadilla": 0.15,
    "salad": 0.10,
    "grilled_protein": 0.05,
    "nachos": 0.10,
    "bowl": 0.05,
}


# ==========================================================================
# SIMPLE RECIPES (for initial testing)
# ==========================================================================

# Simple single-station recipes for easier testing
SIMPLE_RECIPES: Dict[str, List[Tuple[str, float, float]]] = {
    "simple_taco": [
        ("sautee_station", 3.0, 0.5),
    ],
    "simple_salad": [
        ("salad_station", 2.5, 0.4),
    ],
    "simple_grill": [
        ("wood_grill", 4.0, 0.8),
    ],
}

SIMPLE_MENU_DISTRIBUTION: Dict[str, float] = {
    "simple_taco": 0.50,
    "simple_salad": 0.30,
    "simple_grill": 0.20,
}


# ==========================================================================
# RECIPE UTILITIES
# ==========================================================================

def get_recipes(custom_recipes: Optional[Dict[str, List[Tuple[str, float, float]]]] = None) -> Dict[str, List[Tuple[str, float, float]]]:
    """Get recipe configuration.
    
    Args:
        custom_recipes: Custom recipe configuration. If None, returns DEFAULT_RECIPES.
    
    Returns:
        Dictionary mapping dish types to component lists.
    """
    if custom_recipes is not None:
        return custom_recipes
    return DEFAULT_RECIPES


def get_menu_distribution(
    custom_distribution: Optional[Dict[str, float]] = None,
    recipes: Optional[Dict[str, List[Tuple[str, float, float]]]] = None
) -> Dict[str, float]:
    """Get menu distribution (probability of ordering each dish type).
    
    Args:
        custom_distribution: Custom distribution. If None, uses default or uniform.
        recipes: Recipe configuration (used for uniform distribution if no custom).
    
    Returns:
        Dictionary mapping dish types to selection probabilities.
    """
    if custom_distribution is not None:
        # Normalize to ensure sum is 1.0
        total = sum(custom_distribution.values())
        return {k: v / total for k, v in custom_distribution.items()}
    
    if recipes is not None:
        # Uniform distribution over available recipes
        n = len(recipes)
        return {k: 1.0 / n for k in recipes.keys()}
    
    return DEFAULT_MENU_DISTRIBUTION


def select_dish_type(
    rng: np.random.Generator,
    menu_distribution: Dict[str, float]
) -> str:
    """Randomly select a dish type based on menu distribution.
    
    Args:
        rng: NumPy random number generator.
        menu_distribution: Dictionary mapping dish types to probabilities.
    
    Returns:
        Selected dish type name.
    """
    dish_types = list(menu_distribution.keys())
    probabilities = list(menu_distribution.values())
    
    # Normalize probabilities
    total = sum(probabilities)
    probabilities = [p / total for p in probabilities]
    
    return str(rng.choice(dish_types, p=probabilities))


def get_dish_components(
    dish_type: str,
    recipes: Dict[str, List[Tuple[str, float, float]]]
) -> List[Tuple[str, float, float]]:
    """Get the component list for a dish type.
    
    Args:
        dish_type: The type of dish.
        recipes: Recipe configuration.
    
    Returns:
        List of (station_name, prep_time_mu, prep_time_sigma) tuples.
    """
    if dish_type not in recipes:
        # Fallback to a simple default
        return [("sautee_station", 2.0, 0.5)]
    return recipes[dish_type]


def validate_recipes(recipes: Dict[str, List[Tuple[str, float, float]]]) -> bool:
    """Validate recipe configuration.
    
    Args:
        recipes: Recipe configuration to validate.
    
    Returns:
        True if valid, raises ValueError otherwise.
    """
    valid_stations = {
        "wood_grill",
        "salad_station",
        "sautee_station",
        "tortilla_station",
        "guac_station",
    }
    
    for dish_type, components in recipes.items():
        if not components:
            raise ValueError(f"Dish '{dish_type}' has no components")
        
        for component in components:
            if len(component) != 3:
                raise ValueError(f"Component {component} for dish '{dish_type}' must have 3 elements")
            
            station_name, mu, sigma = component
            
            if station_name not in valid_stations:
                raise ValueError(f"Unknown station '{station_name}' in dish '{dish_type}'")
            
            if mu <= 0 or sigma <= 0:
                raise ValueError(f"Invalid prep time parameters for '{station_name}' in dish '{dish_type}'")
    
    return True


def get_total_expected_prep_time(
    dish_type: str,
    recipes: Dict[str, List[Tuple[str, float, float]]]
) -> float:
    """Calculate expected total prep time for a dish (parallel components).
    
    Since components run in parallel, total time is the MAX of component times.
    For lognormal distribution, E[X] = exp(mu + sigma^2/2).
    
    Args:
        dish_type: The type of dish.
        recipes: Recipe configuration.
    
    Returns:
        Expected prep time (max of component expected times).
    """
    components = get_dish_components(dish_type, recipes)
    
    expected_times = []
    for station_name, mu, sigma in components:
        # Expected value of lognormal distribution
        expected_time = np.exp(mu + (sigma ** 2) / 2)
        expected_times.append(expected_time)
    
    # Since components run in parallel, total time is the max
    return max(expected_times) if expected_times else 0.0


