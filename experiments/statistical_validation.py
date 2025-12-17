"""
Statistical validation framework for restaurant simulation configuration comparison.

Provides functions for:
- Pilot studies to estimate variance
- Sample size estimation for confidence intervals
- Common Random Numbers (CRN) paired comparisons
- Sequential sampling with adaptive stopping
"""
import time
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
from scipy import stats

from parameters import SingleDishParameters
from runner import run_single_dish_sim


def run_pilot_study(configs: List[SingleDishParameters], n_rep: int = 20, 
                   base_seed: int = 1000) -> Dict[str, Dict[str, np.ndarray]]:
    """
    Run pilot study to estimate variance for each configuration.
    
    Args:
        configs: List of SingleDishParameters configurations to test
        n_rep: Number of replications per configuration
        base_seed: Base seed value (will use base_seed + rep for each replication)
    
    Returns:
        Dictionary mapping config to metrics arrays:
        {
            config: {
                'net_revpash': array,
                'revpash': array,
                'table_turnover': array,
                'parties_served': array,
                'total_revenue': array,
                'runtime': array,
                ...
            }
        }
    """
    results = {}
    runtime_times = []
    
    print(f"Running pilot study: {len(configs)} configs × {n_rep} replications")
    print("=" * 70)
    
    for i, config in enumerate(configs):
        config_key = f"config_{i}_{config.num_servers}s_{config.num_cooks}c"
        config_results = {
            'net_revpash': [],
            'revpash': [],
            'table_turnover': [],
            'parties_served': [],
            'total_revenue': [],
            'parties_arrived': [],
            'service_rate': [],
            'avg_wait_table': [],
            'avg_kitchen_time': [],
            'avg_total_time': [],
            'server_utilization': [],
            'avg_cook_utilization': [],
            'runtime': []
        }
        
        print(f"Config {i+1}/{len(configs)}: {config.num_servers} servers, {config.num_cooks} cooks", end="")
        
        for rep in range(n_rep):
            # Create config with unique seed for this replication
            config_copy = SingleDishParameters(
                num_tables=config.num_tables,
                num_servers=config.num_servers,
                num_cooks=config.num_cooks,
                simulation_duration=config.simulation_duration,
                seed=base_seed + rep
            )
            
            # Run simulation and time it
            start_time = time.time()
            result = run_single_dish_sim(config_copy, verbose=False)
            elapsed = time.time() - start_time
            
            # Collect metrics
            config_results['net_revpash'].append(result.get('net_revpash', 0.0))
            config_results['revpash'].append(result.get('revpash', 0.0))
            config_results['table_turnover'].append(result.get('table_turnover', 0.0))
            config_results['parties_served'].append(result.get('parties_served', 0.0))
            config_results['total_revenue'].append(result.get('total_revenue', 0.0))
            config_results['parties_arrived'].append(result.get('parties_arrived', 0.0))
            config_results['service_rate'].append(result.get('service_rate', 0.0))
            config_results['avg_wait_table'].append(result.get('avg_wait_table', 0.0))
            config_results['avg_kitchen_time'].append(result.get('avg_kitchen_time', 0.0))
            config_results['avg_total_time'].append(result.get('avg_total_time', 0.0))
            config_results['server_utilization'].append(result.get('server_utilization', 0.0))
            config_results['avg_cook_utilization'].append(result.get('avg_cook_utilization', 0.0))
            config_results['runtime'].append(elapsed)
            
            if rep == 0:
                print(" ... ", end="", flush=True)
        
        # Convert lists to numpy arrays
        for key in config_results:
            config_results[key] = np.array(config_results[key])
        
        # Calculate mean runtime
        mean_runtime = np.mean(config_results['runtime'])
        runtime_times.append(mean_runtime)
        
        results[config_key] = config_results
        
        print(f"✓ (avg runtime: {mean_runtime:.2f}s)")
    
    print(f"\nPilot study complete. Mean runtime per replication: {np.mean(runtime_times):.2f}s")
    print("=" * 70)
    
    return results


def estimate_sample_size_for_ci(samples: np.ndarray, target_half_width: float, 
                                 alpha: float = 0.05) -> Dict[str, Any]:
    """
    Estimate required sample size for a target confidence interval half-width.
    
    Uses iterative refinement with t-distribution.
    
    Args:
        samples: Sample observations
        target_half_width: Desired CI half-width (absolute or relative)
        alpha: Significance level (default 0.05 for 95% CI)
    
    Returns:
        Dictionary with:
        - 'sample_std': sample standard deviation
        - 'sample_mean': sample mean
        - 'cv': coefficient of variation
        - 'initial_n': initial z-based estimate
        - 'final_n': final t-based estimate after iteration
        - 'iterations': number of iterations
    """
    n_current = len(samples)
    s = np.std(samples, ddof=1)
    mu = np.mean(samples)
    cv = s / mu if mu != 0 else 0.0
    
    # Check if target_half_width is relative (if < 1, assume relative)
    if target_half_width < 1.0 and abs(mu) > 0.01:
        # Relative half-width
        h_abs = target_half_width * abs(mu)
    else:
        # Absolute half-width
        h_abs = target_half_width
    
    # Safety check: avoid division by zero
    if h_abs <= 0:
        h_abs = abs(s) * 0.01  # Use 1% of std as default minimum
    
    # Initial estimate using z-distribution
    z_alpha_half = stats.norm.ppf(1 - alpha/2)
    n_initial = int(np.ceil((z_alpha_half * s / h_abs) ** 2)) if h_abs > 0 else 2
    
    # Iterative refinement with t-distribution
    n_estimate = n_initial
    max_iterations = 10
    iterations = 0
    
    for _ in range(max_iterations):
        if n_estimate < 2:
            n_estimate = 2
            break
        
        # Use t-distribution with n-1 degrees of freedom
        t_alpha_half = stats.t.ppf(1 - alpha/2, df=n_estimate - 1)
        n_new = int(np.ceil((t_alpha_half * s / h_abs) ** 2))
        
        if n_new == n_estimate:
            break
        n_estimate = n_new
        iterations += 1
    
    return {
        'sample_std': s,
        'sample_mean': mu,
        'cv': cv,
        'initial_n': n_initial,
        'final_n': n_estimate,
        'iterations': iterations,
        'target_half_width': target_half_width,
        'target_half_width_abs': h_abs
    }


def run_anova_oneway(pilot_results: Dict[str, Dict[str, np.ndarray]], 
                     metric: str = 'net_revpash') -> Dict[str, Any]:
    """
    Perform one-way ANOVA to test if there are significant differences 
    across configurations for a given metric.
    
    Args:
        pilot_results: Dictionary from run_pilot_study output
        metric: Metric name to test (default: 'net_revpash')
    
    Returns:
        Dictionary with:
        - 'f_statistic': F-statistic from ANOVA
        - 'p_value': p-value for the test
        - 'groups': List of group names (config keys)
        - 'group_means': Dictionary of means for each group
        - 'group_stds': Dictionary of standard deviations for each group
        - 'group_sizes': Dictionary of sample sizes for each group
    """
    # Extract data for each configuration
    groups = list(pilot_results.keys())
    data_groups = []
    
    group_means = {}
    group_stds = {}
    group_sizes = {}
    
    for group_key in groups:
        if metric not in pilot_results[group_key]:
            raise ValueError(f"Metric '{metric}' not found in pilot_results")
        
        group_data = pilot_results[group_key][metric]
        data_groups.append(group_data)
        
        group_means[group_key] = np.mean(group_data)
        group_stds[group_key] = np.std(group_data, ddof=1)
        group_sizes[group_key] = len(group_data)
    
    # Perform one-way ANOVA
    f_statistic, p_value = stats.f_oneway(*data_groups)
    
    return {
        'f_statistic': f_statistic,
        'p_value': p_value,
        'groups': groups,
        'group_means': group_means,
        'group_stds': group_stds,
        'group_sizes': group_sizes,
        'metric': metric
    }


def run_crn_paired(config_pair: Tuple[SingleDishParameters, SingleDishParameters],
                   n_rep: int = 50, base_seed: int = 2000) -> Dict[str, Any]:
    """
    Run paired comparison with Common Random Numbers (CRN).
    
    Runs both configs with identical seeds to reduce variance.
    
    Args:
        config_pair: Tuple of (config_A, config_B) to compare
        n_rep: Number of replications
        base_seed: Base seed value (will use base_seed + rep for each replication)
    
    Returns:
        Dictionary with:
        - 'paired_diffs': array of differences (A - B)
        - 'mean_diff': mean difference
        - 'std_diff': standard deviation of differences
        - 't_stat': t-statistic
        - 'p_value': p-value for two-sided test
        - 'ci_95': 95% confidence interval for mean difference
        - 'ci_lower': lower bound
        - 'ci_upper': upper bound
        - 'config_A_results': array of results for config A
        - 'config_B_results': array of results for config B
    """
    config_A, config_B = config_pair
    
    # Create config copies with same parameters except for what we're comparing
    config_A_list = []
    config_B_list = []
    
    for rep in range(n_rep):
        seed = base_seed + rep
        
        # Config A with this seed
        config_A_rep = SingleDishParameters(
            num_tables=config_A.num_tables,
            num_servers=config_A.num_servers,
            num_cooks=config_A.num_cooks,
            simulation_duration=config_A.simulation_duration,
            seed=seed
        )
        
        # Config B with SAME seed (CRN)
        config_B_rep = SingleDishParameters(
            num_tables=config_B.num_tables,
            num_servers=config_B.num_servers,
            num_cooks=config_B.num_cooks,
            simulation_duration=config_B.simulation_duration,
            seed=seed  # Same seed = CRN
        )
        
        config_A_list.append(config_A_rep)
        config_B_list.append(config_B_rep)
    
    print(f"Running CRN paired comparison: {n_rep} replications")
    print(f"  Config A: {config_A.num_servers} servers, {config_A.num_cooks} cooks")
    print(f"  Config B: {config_B.num_servers} servers, {config_B.num_cooks} cooks")
    print("=" * 70)
    
    # Run replications
    results_A = []
    results_B = []
    
    for rep in range(n_rep):
        if (rep + 1) % 10 == 0:
            print(f"  Progress: {rep + 1}/{n_rep} replications", end="\r")
        
        result_A = run_single_dish_sim(config_A_list[rep], verbose=False)
        result_B = run_single_dish_sim(config_B_list[rep], verbose=False)
        
        results_A.append(result_A.get('net_revpash', 0.0))
        results_B.append(result_B.get('net_revpash', 0.0))
    
    print(f"  Progress: {n_rep}/{n_rep} replications ✓")
    
    # Convert to arrays
    results_A = np.array(results_A)
    results_B = np.array(results_B)
    
    # Compute paired differences
    paired_diffs = results_A - results_B
    
    # Paired t-test
    n = len(paired_diffs)
    mean_diff = np.mean(paired_diffs)
    std_diff = np.std(paired_diffs, ddof=1)
    se_diff = std_diff / np.sqrt(n)
    
    # t-statistic
    t_stat = mean_diff / se_diff if se_diff > 0 else 0.0
    
    # p-value (two-sided)
    p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=n-1))
    
    # 95% confidence interval
    t_critical = stats.t.ppf(0.975, df=n-1)
    ci_lower = mean_diff - t_critical * se_diff
    ci_upper = mean_diff + t_critical * se_diff
    
    return {
        'paired_diffs': paired_diffs,
        'mean_diff': mean_diff,
        'std_diff': std_diff,
        't_stat': t_stat,
        'p_value': p_value,
        'ci_95': (ci_lower, ci_upper),
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'config_A_results': results_A,
        'config_B_results': results_B,
        'n': n
    }


def generate_coarse_grid(table_count: int, server_range: List[int], 
                         cook_range: List[int], 
                         base_params: Optional[SingleDishParameters] = None) -> List[SingleDishParameters]:
    """
    Generate all combinations of servers × cooks with fixed table count.
    
    Args:
        table_count: Fixed number of tables (no variation)
        server_range: List of server counts to test (e.g., [3, 4, 5, 6, 7])
        cook_range: List of cook counts to test (e.g., [3, 4, 5, 6, 7])
        base_params: Base parameters to use (defaults to SingleDishParameters defaults)
    
    Returns:
        List of SingleDishParameters configurations
    """
    if base_params is None:
        base_params = SingleDishParameters()
    
    configs = []
    for num_servers in server_range:
        for num_cooks in cook_range:
            config = SingleDishParameters(
                num_tables=table_count,
                num_servers=num_servers,
                num_cooks=num_cooks,
                simulation_duration=base_params.simulation_duration,
                lambda_base=base_params.lambda_base,
                lambda_peak_multiplier=base_params.lambda_peak_multiplier,
                peak_time=base_params.peak_time,
                peak_width=base_params.peak_width,
                server_hourly_wage=base_params.server_hourly_wage,
                cook_hourly_wage=base_params.cook_hourly_wage,
                price_per_dish=base_params.price_per_dish,
                # Copy other parameters as needed
                decision_base_mean=base_params.decision_base_mean,
                decision_per_person_mean=base_params.decision_per_person_mean,
                decision_std=base_params.decision_std,
                ordering_taking_mean=base_params.ordering_taking_mean,
                ordering_taking_std=base_params.ordering_taking_std,
                delivery_base_mean=base_params.delivery_base_mean,
                delivery_std=base_params.delivery_std,
                payment_base_mean=base_params.payment_base_mean,
                payment_per_person_mean=base_params.payment_per_person_mean,
                payment_std=base_params.payment_std,
                dining_base_mu=base_params.dining_base_mu,
                dining_per_person_mu=base_params.dining_per_person_mu,
                dining_sigma=base_params.dining_sigma,
                dish_mu=base_params.dish_mu,
                dish_sigma=base_params.dish_sigma,
                avg_dishes_per_person_low=base_params.avg_dishes_per_person_low,
                avg_dishes_per_person_high=base_params.avg_dishes_per_person_high,
                cook_concurrency=base_params.cook_concurrency,
                dual_task_penalty=base_params.dual_task_penalty,
                seed=base_params.seed  # Seed will be overridden per replication
            )
            configs.append(config)
    
    return configs


def rank_configs_by_metric(pilot_results: Dict[str, Dict[str, np.ndarray]], 
                           metric: str = 'net_revpash', 
                           top_n: Optional[int] = None) -> List[Tuple[str, float, float, int]]:
    """
    Rank configurations by mean performance for a given metric.
    
    Args:
        pilot_results: Dictionary from run_pilot_study output
        metric: Metric name to rank by (default: 'net_revpash')
        top_n: Optional: return only top N configurations
    
    Returns:
        List of tuples (config_key, mean, std, n) sorted by mean (descending)
    """
    rankings = []
    
    for config_key, config_data in pilot_results.items():
        if metric not in config_data:
            continue
        
        metric_data = config_data[metric]
        mean = np.mean(metric_data)
        std = np.std(metric_data, ddof=1)
        n = len(metric_data)
        
        rankings.append((config_key, mean, std, n))
    
    # Sort by mean (descending)
    rankings.sort(key=lambda x: x[1], reverse=True)
    
    if top_n is not None:
        rankings = rankings[:top_n]
    
    return rankings


def validate_sample_size(pilot_results: Dict[str, Dict[str, np.ndarray]], 
                         target_half_width_rel: float = 0.05, 
                         metric: str = 'net_revpash',
                         alpha: float = 0.05) -> Dict[str, Dict[str, Any]]:
    """
    Validate if pilot sample size (n=20) is sufficient for target CI width.
    
    Args:
        pilot_results: Dictionary from run_pilot_study output
        target_half_width_rel: Target relative half-width (e.g., 0.05 = 5% of mean)
        metric: Metric name to validate (default: 'net_revpash')
        alpha: Significance level (default 0.05 for 95% CI)
    
    Returns:
        Dictionary mapping config_key to validation results:
        {
            config_key: {
                'current_n': current sample size,
                'required_n': required sample size,
                'sufficient': boolean,
                'mean': sample mean,
                'std': sample std,
                'cv': coefficient of variation
            }
        }
    """
    validation_results = {}
    
    for config_key, config_data in pilot_results.items():
        if metric not in config_data:
            continue
        
        metric_data = config_data[metric]
        current_n = len(metric_data)
        
        # Estimate required sample size
        size_est = estimate_sample_size_for_ci(
            metric_data, 
            target_half_width=target_half_width_rel,
            alpha=alpha
        )
        
        required_n = size_est['final_n']
        sufficient = current_n >= required_n
        
        validation_results[config_key] = {
            'current_n': current_n,
            'required_n': required_n,
            'sufficient': sufficient,
            'mean': size_est['sample_mean'],
            'std': size_est['sample_std'],
            'cv': size_est['cv']
        }
    
    return validation_results


def sequential_sample(config: SingleDishParameters, metric: str = 'net_revpash',
                      h_rel: float = 0.05, batch: int = 5, n_max: int = 200,
                      base_seed: int = 3000) -> Dict[str, Any]:
    """
    Sequential sampling: run batches until relative CI half-width meets target.
    
    Args:
        config: Configuration to test
        metric: Metric name to track (default: 'net_revpash')
        h_rel: Target relative half-width (e.g., 0.05 = 5% of mean)
        batch: Batch size for each iteration
        n_max: Maximum number of replications
        base_seed: Base seed value
    
    Returns:
        Dictionary with:
        - 'final_n': final number of replications
        - 'ci_lower': lower bound of final CI
        - 'ci_upper': upper bound of final CI
        - 'ci_half_width': absolute half-width
        - 'ci_half_width_rel': relative half-width
        - 'mean': sample mean
        - 'std': sample standard deviation
        - 'all_results': array of all metric values
        - 'ci_history': list of (n, ci_lower, ci_upper, ci_half_width) tuples
    """
    print(f"Sequential sampling: target relative half-width = {h_rel*100:.1f}%")
    print(f"  Config: {config.num_servers} servers, {config.num_cooks} cooks")
    print(f"  Metric: {metric}")
    print("=" * 70)
    
    all_results = []
    ci_history = []
    n_current = 0
    
    while n_current < n_max:
        # Run batch
        batch_results = []
        for i in range(batch):
            seed = base_seed + n_current + i
            config_rep = SingleDishParameters(
                num_tables=config.num_tables,
                num_servers=config.num_servers,
                num_cooks=config.num_cooks,
                simulation_duration=config.simulation_duration,
                seed=seed
            )
            
            result = run_single_dish_sim(config_rep, verbose=False)
            batch_results.append(result.get(metric, 0.0))
        
        all_results.extend(batch_results)
        n_current = len(all_results)
        
        # Compute CI
        if n_current >= 2:
            results_array = np.array(all_results)
            mean = np.mean(results_array)
            std = np.std(results_array, ddof=1)
            
            # 95% CI
            t_critical = stats.t.ppf(0.975, df=n_current - 1)
            se = std / np.sqrt(n_current)
            ci_half_width = t_critical * se
            ci_lower = mean - ci_half_width
            ci_upper = mean + ci_half_width
            
            # Relative half-width
            ci_half_width_rel = ci_half_width / abs(mean) if abs(mean) > 0.01 else float('inf')
            
            ci_history.append((n_current, ci_lower, ci_upper, ci_half_width, ci_half_width_rel))
            
            print(f"  n={n_current:3d}: mean={mean:7.2f}, CI=[{ci_lower:7.2f}, {ci_upper:7.2f}], "
                  f"h_rel={ci_half_width_rel*100:5.2f}%", end="")
            
            # Check stopping criterion
            if ci_half_width_rel <= h_rel:
                print(f" ✓ (target met)")
                break
            else:
                print()
        
        if n_current < 2:
            continue
    
    # Final results
    results_array = np.array(all_results)
    mean = np.mean(results_array)
    std = np.std(results_array, ddof=1)
    
    if n_current >= 2:
        t_critical = stats.t.ppf(0.975, df=n_current - 1)
        se = std / np.sqrt(n_current)
        ci_half_width = t_critical * se
        ci_lower = mean - ci_half_width
        ci_upper = mean + ci_half_width
        ci_half_width_rel = ci_half_width / abs(mean) if abs(mean) > 0.01 else float('inf')
    else:
        ci_lower = mean
        ci_upper = mean
        ci_half_width = 0.0
        ci_half_width_rel = 0.0
    
    print(f"\nSequential sampling complete: n={n_current}, h_rel={ci_half_width_rel*100:.2f}%")
    print("=" * 70)
    
    return {
        'final_n': n_current,
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'ci_half_width': ci_half_width,
        'ci_half_width_rel': ci_half_width_rel,
        'mean': mean,
        'std': std,
        'all_results': results_array,
        'ci_history': ci_history
    }

