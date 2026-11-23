"""Utility functions for random number generation."""
import numpy as np


def draw_lognormal(rng: np.random.Generator, mu: float, sigma: float) -> float:
    """Draw a lognormal random variable.
    
    Args:
        rng: NumPy random number generator
        mu: Mean parameter for lognormal distribution
        sigma: Standard deviation parameter for lognormal distribution
    
    Returns:
        Random value from lognormal distribution
    """
    return float(rng.lognormal(mean=mu, sigma=sigma))


def draw_normal_positive(rng: np.random.Generator, mean: float, std: float) -> float:
    """Draw a normal random variable truncated at >0.
    
    Args:
        rng: NumPy random number generator
        mean: Mean of the normal distribution
        std: Standard deviation of the normal distribution
    
    Returns:
        Random value from truncated normal distribution (always > 0)
    """
    val = -1.0
    while val <= 0:
        val = float(rng.normal(loc=mean, scale=std))
    return val


def generate_party_size(rng: np.random.Generator) -> int:
    """Generate party size using weighted distribution.
    
    Weights: 1=15%, 2=35%, 3=25%, 4=15%, 5=5%, 6=3%, 7=1%, 8=1%, 9=0.5%, 10=0.5%
    
    Args:
        rng: NumPy random number generator
    
    Returns:
        Party size (1-10)
    """
    sizes = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    weights = [0.15, 0.35, 0.25, 0.15, 0.05, 0.03, 0.01, 0.01, 0.005, 0.005]
    # Normalize weights to sum to exactly 1.0 (fix floating point precision issues)
    weights = np.array(weights)
    weights = weights / weights.sum()
    return int(rng.choice(sizes, p=weights))

