"""Ranking & selection procedures for comparing staffing configurations.

Pipeline (see README "Methodology"):
  1. run_pilot_study / estimate_n_required  - small pilot to estimate variance and size the study
  2. run_screening_parallel                 - cheap first-stage screen of every configuration
  3. subset_selection                       - Bonferroni-corrected "may be best" subset
  4. run_to_target_precision                - adaptive stopping rule: add replications until the
                                              95% CI half-width is within a target % of the mean
  5. compare_configurations_pairwise        - Welch CI on the difference between two configs

Common random numbers (paired runs sharing seeds) live in statistical_validation.run_crn_paired.
Run this module's functions from the notebook notebooks/statistical_testing.ipynb.
"""

import numpy as np
from scipy import stats
from dataclasses import replace
from typing import Dict, List, Optional, Tuple
from itertools import product
from multiprocessing import Pool

from parameters import SingleDishParameters
from runner import run_single_dish_sim


def run_replications(params: SingleDishParameters, 
                     n: int, 
                     metric: str = 'net_revpash',
                     base_seed: int = 1000) -> np.ndarray:
    """
    Run n independent replications of simulation.
    
    Args:
        params: Base simulation parameters
        n: Number of replications to run
        metric: Result metric to collect (default: 'net_revpash')
        base_seed: Base seed value (uses base_seed + rep for each replication)
    
    Returns:
        1D numpy array of n metric values
    """
    if n <= 0:
        raise ValueError("n must be positive")
    
    results = []
    for rep in range(n):
        # Create copy with unique seed for this replication
        params_rep = replace(params, seed=base_seed + rep)
        result = run_single_dish_sim(params_rep, verbose=False)
        results.append(result.get(metric, 0.0))
    
    return np.array(results)


def compute_ci(samples: np.ndarray, confidence: float = 0.95) -> Dict[str, float]:
    """
    Compute confidence interval from samples using t-distribution.
    
    Args:
        samples: Array of sample observations
        confidence: Confidence level (default 0.95 for 95% CI)
    
    Returns:
        Dictionary with:
        - 'mean': sample mean
        - 'std': sample standard deviation
        - 'ci_lower': lower bound of CI
        - 'ci_upper': upper bound of CI
        - 'half_width': absolute CI half-width
        - 'half_width_rel': relative CI half-width (half_width / |mean|)
        - 'n': sample size
    """
    if len(samples) == 0:
        raise ValueError("samples cannot be empty")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    
    n = len(samples)
    mean = np.mean(samples)
    std = np.std(samples, ddof=1)  # Sample std with Bessel's correction
    
    # Handle edge case: single sample
    if n == 1:
        return {
            'mean': mean,
            'std': 0.0,
            'ci_lower': mean,
            'ci_upper': mean,
            'half_width': 0.0,
            'half_width_rel': 0.0,
            'n': n
        }
    
    alpha = 1 - confidence
    t_critical = stats.t.ppf(1 - alpha/2, df=n - 1)
    
    se = std / np.sqrt(n)  # Standard error
    half_width = t_critical * se
    
    # Relative half-width (handle zero mean)
    half_width_rel = half_width / abs(mean) if abs(mean) > 1e-10 else np.inf
    
    return {
        'mean': mean,
        'std': std,
        'ci_lower': mean - half_width,
        'ci_upper': mean + half_width,
        'half_width': half_width,
        'half_width_rel': half_width_rel,
        'n': n
    }


def estimate_n_required(pilot_samples: np.ndarray,
                        target_relative_error: float = 0.05,
                        confidence: float = 0.95) -> Dict[str, float]:
    """
    Estimate required number of replications for target relative error.
    
    Uses iterative t-distribution formula: n >= (t * CV / rel_error)^2
    
    Args:
        pilot_samples: Array of n₀ pilot observations
        target_relative_error: Target relative CI half-width (e.g., 0.05 = 5%)
        confidence: Confidence level (default 0.95)
    
    Returns:
        Dictionary with:
        - 'n_pilot': number of pilot samples
        - 'n_required': estimated required replications
        - 'mean': sample mean from pilot
        - 'std': sample standard deviation from pilot
        - 'cv': coefficient of variation (std/mean)
        - 'target_relative_error': the target we're solving for
        - 'expected_relative_error': expected error if we use n_required
    """
    if len(pilot_samples) < 2:
        raise ValueError("Need at least 2 pilot samples")
    if not 0 < target_relative_error < 1:
        raise ValueError("target_relative_error must be between 0 and 1")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    
    n_pilot = len(pilot_samples)
    mean = np.mean(pilot_samples)
    std = np.std(pilot_samples, ddof=1)
    
    # Coefficient of variation
    cv = std / abs(mean) if abs(mean) > 1e-10 else np.inf
    
    alpha = 1 - confidence
    
    # Iterative calculation with t-distribution
    # Start with initial estimate based on z-distribution
    z_critical = stats.norm.ppf(1 - alpha/2)
    n_estimate = max(2, int(np.ceil((z_critical * cv / target_relative_error) ** 2)))
    
    # Iterate to refine with t-distribution (converges quickly)
    for _ in range(10):
        t_critical = stats.t.ppf(1 - alpha/2, df=n_estimate - 1)
        n_new = max(2, int(np.ceil((t_critical * cv / target_relative_error) ** 2)))
        
        if n_new == n_estimate:
            break
        n_estimate = n_new
    
    # Calculate expected relative error with n_estimate
    if n_estimate >= 2:
        t_final = stats.t.ppf(1 - alpha/2, df=n_estimate - 1)
        expected_rel_error = t_final * cv / np.sqrt(n_estimate)
    else:
        expected_rel_error = np.inf
    
    return {
        'n_pilot': n_pilot,
        'n_required': n_estimate,
        'mean': mean,
        'std': std,
        'cv': cv,
        'target_relative_error': target_relative_error,
        'expected_relative_error': expected_rel_error
    }


def run_pilot_study(configs: List[SingleDishParameters],
                    n_pilot: int = 30,
                    metric: str = 'net_revpash',
                    target_relative_error: float = 0.05,
                    base_seed: int = 1000) -> Dict[int, Dict]:
    """
    Run pilot study on multiple configurations.
    
    Args:
        configs: List of SingleDishParameters configurations
        n_pilot: Number of replications per configuration (default 30)
        metric: Result metric to collect (default: 'net_revpash')
        target_relative_error: Target relative error for n estimation
        base_seed: Base seed (each config gets base_seed + config_idx * 1000)
    
    Returns:
        Dictionary mapping config_index to:
        {
            'samples': array of metric values,
            'ci': confidence interval dict from compute_ci(),
            'n_estimate': dict from estimate_n_required(),
            'config': the SingleDishParameters used
        }
    """
    if not configs:
        raise ValueError("configs list cannot be empty")
    if n_pilot < 2:
        raise ValueError("n_pilot must be at least 2")
    
    results = {}
    total_configs = len(configs)
    
    print(f"Running pilot study: {total_configs} configs × {n_pilot} replications")
    print("=" * 60)
    
    for idx, config in enumerate(configs):
        # Use different seed range for each config
        config_base_seed = base_seed + idx * 1000
        
        # Run replications
        samples = run_replications(config, n_pilot, metric, config_base_seed)
        
        # Compute CI
        ci = compute_ci(samples)
        
        # Estimate required n
        n_est = estimate_n_required(samples, target_relative_error)
        
        results[idx] = {
            'samples': samples,
            'ci': ci,
            'n_estimate': n_est,
            'config': config
        }
        
        # Progress report
        print(f"Config {idx + 1}/{total_configs}: "
              f"mean={ci['mean']:.2f}, "
              f"CI=[{ci['ci_lower']:.2f}, {ci['ci_upper']:.2f}], "
              f"n_required={n_est['n_required']}")
    
    print("=" * 60)
    print(f"Pilot study complete.")
    
    return results


def run_to_target_precision(params: SingleDishParameters,
                            pilot_samples: np.ndarray,
                            metric: str = 'net_revpash',
                            target_relative_error: float = 0.05,
                            confidence: float = 0.95,
                            base_seed: int = 1000,
                            max_iterations: int = 5,
                            min_batch_size: int = 10) -> Dict:
    """
    Run additional replications until target precision is achieved.
    
    Starts with pilot samples, estimates required n, runs additional replications,
    and iteratively continues until target relative error is met.
    
    Args:
        params: Simulation parameters
        pilot_samples: Array of pilot observations (will be combined with new samples)
        metric: Result metric to collect (default: 'net_revpash')
        target_relative_error: Target relative CI half-width (e.g., 0.05 = 5%)
        confidence: Confidence level (default 0.95)
        base_seed: Base seed (new replications start from base_seed + len(pilot_samples))
        max_iterations: Maximum number of iterations to avoid infinite loops
        min_batch_size: Minimum additional replications to run per iteration
    
    Returns:
        Dictionary with:
        - 'all_samples': combined array of all samples
        - 'ci': final confidence interval dict
        - 'n_required': final estimated n_required
        - 'iterations': number of iterations performed
        - 'converged': whether target was achieved
        - 'history': list of (n, rel_error) tuples for each iteration
    """
    if len(pilot_samples) < 2:
        raise ValueError("Need at least 2 pilot samples")
    
    all_samples = pilot_samples.copy()
    current_seed = base_seed + len(pilot_samples)
    history = []
    iterations = 0
    
    print(f"Running to target precision: {target_relative_error*100:.1f}% relative error")
    print(f"Starting with {len(pilot_samples)} pilot samples")
    print("=" * 60)
    
    while iterations < max_iterations:
        iterations += 1
        
        # Compute current CI
        ci = compute_ci(all_samples, confidence)
        current_rel_error = ci['half_width_rel']
        
        history.append((len(all_samples), current_rel_error))
        
        print(f"Iteration {iterations}: n={len(all_samples)}, "
              f"mean={ci['mean']:.2f}, "
              f"rel_error={current_rel_error*100:.2f}%")
        
        # Check if target achieved
        if current_rel_error <= target_relative_error:
            print(f"✓ Target achieved! Relative error ≤ {target_relative_error*100:.1f}%")
            print("=" * 60)
            break
        
        # Estimate how many more we need
        n_est = estimate_n_required(all_samples, target_relative_error, confidence)
        n_required = n_est['n_required']
        current_n = len(all_samples)
        
        if n_required <= current_n:
            # We have enough, but precision not achieved yet
            # Run a small batch and check again
            additional_n = max(min_batch_size, current_n // 4)
        else:
            # Run enough to reach estimated requirement (or min batch)
            additional_n = max(min_batch_size, n_required - current_n)
        
        print(f"  Estimated n_required: {n_required}, running {additional_n} more replications...")
        
        # Run additional replications
        new_samples = run_replications(
            params, 
            n=additional_n, 
            metric=metric,
            base_seed=current_seed
        )
        
        # Combine with existing samples
        all_samples = np.concatenate([all_samples, new_samples])
        current_seed += additional_n
    
    # Final results
    final_ci = compute_ci(all_samples, confidence)
    final_n_est = estimate_n_required(all_samples, target_relative_error, confidence)
    
    converged = final_ci['half_width_rel'] <= target_relative_error
    
    if not converged and iterations >= max_iterations:
        print(f"⚠ Max iterations ({max_iterations}) reached. "
              f"Current relative error: {final_ci['half_width_rel']*100:.2f}%")
        print("=" * 60)
    
    return {
        'all_samples': all_samples,
        'ci': final_ci,
        'n_estimate': final_n_est,
        'iterations': iterations,
        'converged': converged,
        'history': history
    }


def generate_configuration_grid(base_params: SingleDishParameters,
                                 server_range: List[int],
                                 cook_range: List[int],
                                 host_range: List[int] = [1],
                                 food_runner_range: List[int] = [2],
                                 busser_range: List[int] = [0]) -> List[SingleDishParameters]:
    """
    Generate systematic grid of configurations by varying ALL staffing parameters.
    
    Args:
        base_params: Base parameters (will copy dish_recipes, menu, etc.)
        server_range: List of server counts to test (e.g., [4, 5, 6, 7, 8])
        cook_range: List of cook counts to test (e.g., [6, 7, 8, 9, 10])
        host_range: List of host counts to test (e.g., [1, 2])
        food_runner_range: List of food runner counts (e.g., [1, 2, 3])
        busser_range: List of busser counts (e.g., [0, 1, 2])
    
    Returns:
        List of SingleDishParameters configurations (Cartesian product of all ranges)
    
    Warning:
        Total configs = len(server_range) × len(cook_range) × len(host_range) × 
                        len(food_runner_range) × len(busser_range)
        Can be very large! Consider using smaller ranges or screening.
    """
    # Calculate total combinations
    total = (len(server_range) * len(cook_range) * len(host_range) * 
             len(food_runner_range) * len(busser_range))
    
    print(f"Generating configuration grid:")
    print(f"  Servers: {server_range} ({len(server_range)} values)")
    print(f"  Cooks: {cook_range} ({len(cook_range)} values)")
    print(f"  Hosts: {host_range} ({len(host_range)} values)")
    print(f"  Food Runners: {food_runner_range} ({len(food_runner_range)} values)")
    print(f"  Bussers: {busser_range} ({len(busser_range)} values)")
    print(f"  Total configurations: {total}")
    
    if total > 100:
        print(f"  ⚠ Warning: Large number of configurations! Consider screening or smaller ranges.")
    
    configs = []
    for servers, cooks, hosts, runners, bussers in product(
        server_range, cook_range, host_range, food_runner_range, busser_range
    ):
        config = replace(
            base_params,
            num_servers=servers,
            num_cooks=cooks,
            num_hosts=hosts,
            num_food_runners=runners,
            num_bussers=bussers
        )
        configs.append(config)
    
    return configs


def config_to_label(config: SingleDishParameters) -> str:
    """Generate a short label for a configuration."""
    return (f"S{config.num_servers}_C{config.num_cooks}_H{config.num_hosts}_"
            f"R{config.num_food_runners}_B{config.num_bussers}")


def compare_configurations_pairwise(samples_A: np.ndarray,
                                     samples_B: np.ndarray,
                                     confidence: float = 0.95) -> Dict:
    """
    Compare two configurations using confidence interval for the difference.
    
    Uses Welch's t-test (doesn't assume equal variances or sample sizes).
    
    Args:
        samples_A: Array of sample observations from configuration A
        samples_B: Array of sample observations from configuration B
        confidence: Confidence level (default 0.95)
    
    Returns:
        Dictionary with:
        - 'mean_A': mean of samples A
        - 'mean_B': mean of samples B
        - 'mean_diff': mean difference (A - B)
        - 'ci_lower': lower bound of CI for difference
        - 'ci_upper': upper bound of CI for difference
        - 'significant': True if CI doesn't contain zero (statistically different)
        - 'A_better': True if A is significantly better than B (mean_diff > 0 and significant)
        - 'B_better': True if B is significantly better than A (mean_diff < 0 and significant)
        - 'n_A': sample size A
        - 'n_B': sample size B
    """
    if len(samples_A) < 2 or len(samples_B) < 2:
        raise ValueError("Need at least 2 samples from each configuration")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    
    n_A = len(samples_A)
    n_B = len(samples_B)
    mean_A = np.mean(samples_A)
    mean_B = np.mean(samples_B)
    var_A = np.var(samples_A, ddof=1)
    var_B = np.var(samples_B, ddof=1)
    
    mean_diff = mean_A - mean_B
    
    # Welch's t-test (unequal variances)
    # Standard error of the difference
    se_diff = np.sqrt(var_A / n_A + var_B / n_B)
    
    # Welch-Satterthwaite degrees of freedom
    if se_diff > 0:
        df_num = (var_A / n_A + var_B / n_B) ** 2
        df_denom = ((var_A / n_A) ** 2 / (n_A - 1) + 
                    (var_B / n_B) ** 2 / (n_B - 1))
        df = df_num / df_denom if df_denom > 0 else min(n_A, n_B) - 1
    else:
        df = min(n_A, n_B) - 1
    
    alpha = 1 - confidence
    t_critical = stats.t.ppf(1 - alpha/2, df=df)
    
    half_width = t_critical * se_diff
    ci_lower = mean_diff - half_width
    ci_upper = mean_diff + half_width
    
    # Significance: CI doesn't contain zero
    significant = not (ci_lower <= 0 <= ci_upper)
    
    return {
        'mean_A': mean_A,
        'mean_B': mean_B,
        'mean_diff': mean_diff,
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'half_width': half_width,
        'significant': significant,
        'A_better': significant and mean_diff > 0,
        'B_better': significant and mean_diff < 0,
        'n_A': n_A,
        'n_B': n_B,
        'df': df
    }


def subset_selection(screening_results: Dict[int, Dict],
                     confidence: float = 0.95,
                     metric_key: str = 'ci') -> Dict:
    """
    Screen configurations to find "may be the best" subset.
    
    Uses one-sided confidence intervals with Bonferroni correction for
    multiple comparisons. A config is kept if it could potentially be the best.
    
    Args:
        screening_results: Dictionary from run_pilot_study or screening:
            {idx: {'samples': array, 'ci': {...}, 'config': SingleDishParameters}}
        confidence: Confidence level (default 0.95)
        metric_key: Key to access CI dict (default 'ci')
    
    Returns:
        Dictionary with:
        - 'best_idx': index of sample best configuration
        - 'best_mean': mean of best configuration
        - 'may_be_best': list of indices that could potentially be the best
        - 'not_best': list of indices that are statistically inferior
        - 'config_stats': dict mapping idx -> (mean, upper_bound)
    """
    if not screening_results:
        raise ValueError("screening_results cannot be empty")
    
    # Find sample best (highest mean - for net_revpash, higher is better)
    best_idx = max(screening_results.keys(), 
                   key=lambda i: screening_results[i][metric_key]['mean'])
    best_mean = screening_results[best_idx][metric_key]['mean']
    
    k = len(screening_results)  # Number of configurations
    alpha = 1 - confidence
    # Bonferroni correction: divide alpha by number of comparisons
    alpha_corrected = alpha / (k - 1) if k > 1 else alpha
    
    may_be_best = [best_idx]  # Best is always included
    not_best = []
    config_stats = {}
    
    for idx, data in screening_results.items():
        ci = data[metric_key]
        mean_i = ci['mean']
        std_i = ci['std']
        n_i = ci['n']
        
        # One-sided upper CI bound: can this config potentially be better than best?
        if n_i > 1:
            t_critical = stats.t.ppf(1 - alpha_corrected, df=n_i - 1)
            upper_bound = mean_i + t_critical * (std_i / np.sqrt(n_i))
        else:
            upper_bound = mean_i
        
        config_stats[idx] = {'mean': mean_i, 'upper_bound': upper_bound}
        
        if idx == best_idx:
            continue
        
        if upper_bound >= best_mean:
            # Could potentially be better
            may_be_best.append(idx)
        else:
            # Statistically inferior
            not_best.append(idx)
    
    # Sort by mean for readability
    may_be_best = sorted(may_be_best, 
                         key=lambda i: screening_results[i][metric_key]['mean'], 
                         reverse=True)
    not_best = sorted(not_best,
                      key=lambda i: screening_results[i][metric_key]['mean'],
                      reverse=True)
    
    print(f"Subset Selection Results (Bonferroni-corrected, α/{k-1 if k>1 else 1}):")
    print(f"  Sample best: Config {best_idx} (mean={best_mean:.3f})")
    print(f"  May be best: {len(may_be_best)} configs ({may_be_best})")
    print(f"  Not best: {len(not_best)} configs (screened out)")
    
    return {
        'best_idx': best_idx,
        'best_mean': best_mean,
        'may_be_best': may_be_best,
        'not_best': not_best,
        'config_stats': config_stats
    }


# Helper function for parallel execution (must be at module level for pickling)
def _run_single_replication(args: Tuple) -> float:
    """Helper function to run a single replication (for parallel execution)."""
    params, seed, metric = args
    params_rep = replace(params, seed=seed)
    result = run_single_dish_sim(params_rep, verbose=False)
    return result.get(metric, 0.0)


def run_replications_parallel(params: SingleDishParameters,
                              n: int,
                              metric: str = 'net_revpash',
                              base_seed: int = 1000,
                              n_jobs: int = -1) -> np.ndarray:
    """
    Run n replications in parallel using multiprocessing.
    
    Args:
        params: Base simulation parameters
        n: Number of replications to run
        metric: Result metric to collect (default: 'net_revpash')
        base_seed: Base seed value (uses base_seed + rep for each replication)
        n_jobs: Number of parallel workers (-1 = use all CPUs, 1 = sequential)
    
    Returns:
        1D numpy array of n metric values
    """
    if n <= 0:
        raise ValueError("n must be positive")
    
    # Prepare arguments for each replication
    args_list = [(params, base_seed + rep, metric) for rep in range(n)]
    
    if n_jobs == 1:
        # Sequential execution (fallback)
        results = [_run_single_replication(args) for args in args_list]
    else:
        # Parallel execution
        n_workers = None if n_jobs == -1 else n_jobs
        try:
            with Pool(n_workers) as pool:
                results = pool.map(_run_single_replication, args_list)
        except Exception as e:
            print(f"⚠ Parallel execution failed ({e}), falling back to sequential")
            results = [_run_single_replication(args) for args in args_list]
    
    return np.array(results)


def run_screening_parallel(configs: List[SingleDishParameters],
                           n_per_config: int = 10,
                           metric: str = 'net_revpash',
                           base_seed: int = 1000,
                           n_jobs: int = -1) -> Dict[int, Dict]:
    """
    Run quick screening study on all configurations (parallel).
    
    Args:
        configs: List of SingleDishParameters configurations
        n_per_config: Number of replications per configuration (default 10)
        metric: Result metric to collect (default: 'net_revpash')
        base_seed: Base seed (each config gets base_seed + config_idx * 1000)
        n_jobs: Number of parallel workers (-1 = use all CPUs)
    
    Returns:
        Dictionary mapping config_index to:
        {
            'samples': array of metric values,
            'ci': confidence interval dict,
            'config': the SingleDishParameters used
        }
    """
    if not configs:
        raise ValueError("configs list cannot be empty")
    
    total_configs = len(configs)
    total_runs = total_configs * n_per_config
    
    print(f"Screening {total_configs} configurations × {n_per_config} replications = {total_runs} total runs")
    print("=" * 60)
    
    results = {}
    for idx, config in enumerate(configs):
        # Use different seed range for each config
        config_base_seed = base_seed + idx * 1000
        
        # Run replications (sequential for now to avoid nested parallelism issues)
        # Each config runs sequentially but we process configs one at a time
        samples = run_replications(config, n_per_config, metric, config_base_seed)
        
        # Compute CI
        ci = compute_ci(samples)
        
        results[idx] = {
            'samples': samples,
            'ci': ci,
            'config': config
        }
        
        # Progress report
        label = config_to_label(config)
        print(f"[{idx+1}/{total_configs}] {label}: mean={ci['mean']:.2f}, "
              f"CI=[{ci['ci_lower']:.2f}, {ci['ci_upper']:.2f}]")
    
    print("=" * 60)
    print(f"Screening complete.")
    
    return results
