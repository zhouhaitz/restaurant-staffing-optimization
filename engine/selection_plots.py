"""Plotting helpers for the selection workflow (used by notebooks/statistical_testing.ipynb)."""
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List

from parameters import SingleDishParameters
from selection import compute_ci, config_to_label

plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

# =============================================================================
# VISUALIZATION FUNCTIONS
# =============================================================================

def plot_configuration_grid(configs: List[SingleDishParameters],
                            server_range: List[int],
                            cook_range: List[int],
                            host_range: List[int],
                            food_runner_range: List[int],
                            busser_range: List[int]):
    """
    Visualize the configuration grid showing parameter ranges and total count.
    """
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    
    # Plot 1: Parameter ranges as bar chart
    ax1 = axes[0]
    params = ['Servers', 'Cooks', 'Hosts', 'Food Runners', 'Bussers']
    ranges = [server_range, cook_range, host_range, food_runner_range, busser_range]
    counts = [len(r) for r in ranges]
    colors = sns.color_palette("husl", len(params))
    
    bars = ax1.bar(params, counts, color=colors, edgecolor='black', linewidth=1.2)
    ax1.set_ylabel('Number of Values', fontsize=11)
    ax1.set_title('Parameter Variations', fontsize=12, fontweight='bold')
    ax1.set_ylim(0, max(counts) + 1)
    
    # Add value labels on bars
    for bar, count in zip(bars, counts):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                str(count), ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax1.tick_params(axis='x', rotation=30)
    
    # Plot 2: Range details as text table
    ax2 = axes[1]
    ax2.axis('off')
    table_data = []
    for name, rng in zip(params, ranges):
        table_data.append([name, f"{min(rng)} - {max(rng)}", str(len(rng))])
    
    table = ax2.table(cellText=table_data,
                      colLabels=['Parameter', 'Range', 'Count'],
                      loc='center',
                      cellLoc='center',
                      colColours=['#E8E8E8']*3)
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.5)
    ax2.set_title('Configuration Ranges', fontsize=12, fontweight='bold', pad=20)
    
    # Plot 3: Total configurations breakdown
    ax3 = axes[2]
    total = len(configs)
    breakdown = ' × '.join([str(c) for c in counts])
    
    ax3.text(0.5, 0.6, f'{total}', fontsize=48, fontweight='bold', 
             ha='center', va='center', color='#2E86AB')
    ax3.text(0.5, 0.35, 'Total Configurations', fontsize=14, ha='center', va='center')
    ax3.text(0.5, 0.2, f'({breakdown})', fontsize=11, ha='center', va='center', color='gray')
    ax3.axis('off')
    ax3.set_title('Grid Size', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    plt.show()


def plot_screening_results(screening_results: Dict[int, Dict], top_n: int = 30):
    """
    Visualize screening results with multiple plots.
    """
    # Extract data
    indices = list(screening_results.keys())
    means = [screening_results[i]['ci']['mean'] for i in indices]
    half_widths = [screening_results[i]['ci']['half_width'] for i in indices]
    labels = [config_to_label(screening_results[i]['config']) for i in indices]
    
    # Sort by mean (descending)
    sorted_data = sorted(zip(indices, means, half_widths, labels), 
                         key=lambda x: x[1], reverse=True)
    
    # Take top_n for detailed view
    top_data = sorted_data[:top_n]
    top_indices, top_means, top_hws, top_labels = zip(*top_data) if top_data else ([], [], [], [])
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # Plot 1: Top N configurations with error bars
    ax1 = axes[0, 0]
    y_pos = np.arange(len(top_means))
    colors = plt.cm.RdYlGn(np.linspace(0.8, 0.2, len(top_means)))
    
    ax1.barh(y_pos, top_means, xerr=top_hws, color=colors, 
             edgecolor='black', linewidth=0.5, capsize=3)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(top_labels, fontsize=8)
    ax1.set_xlabel('Net RevPASH (mean ± CI half-width)', fontsize=10)
    ax1.set_title(f'Top {len(top_means)} Configurations by Mean', fontsize=12, fontweight='bold')
    ax1.invert_yaxis()
    ax1.axvline(x=0, color='black', linestyle='--', linewidth=0.8, alpha=0.5)
    
    # Plot 2: Distribution of all means (histogram)
    ax2 = axes[0, 1]
    ax2.hist(means, bins=30, color='steelblue', edgecolor='black', alpha=0.7)
    ax2.axvline(x=np.mean(means), color='red', linestyle='--', linewidth=2, 
                label=f'Mean: {np.mean(means):.2f}')
    ax2.axvline(x=np.max(means), color='green', linestyle='--', linewidth=2,
                label=f'Max: {np.max(means):.2f}')
    ax2.set_xlabel('Net RevPASH', fontsize=10)
    ax2.set_ylabel('Frequency', fontsize=10)
    ax2.set_title('Distribution of Configuration Means', fontsize=12, fontweight='bold')
    ax2.legend(fontsize=9)
    
    # Plot 3: Mean vs CI Width (precision scatter)
    ax3 = axes[1, 0]
    scatter = ax3.scatter(means, half_widths, c=means, cmap='RdYlGn', 
                          s=50, alpha=0.7, edgecolors='black', linewidth=0.5)
    ax3.set_xlabel('Mean Net RevPASH', fontsize=10)
    ax3.set_ylabel('CI Half-Width (uncertainty)', fontsize=10)
    ax3.set_title('Mean vs Uncertainty', fontsize=12, fontweight='bold')
    plt.colorbar(scatter, ax=ax3, label='Mean')
    
    # Highlight best config
    best_idx = np.argmax(means)
    ax3.scatter([means[best_idx]], [half_widths[best_idx]], 
                color='red', s=150, marker='*', zorder=5, label='Best')
    ax3.legend()
    
    # Plot 4: Summary statistics
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    stats_text = f"""
    SCREENING SUMMARY
    ─────────────────────────────
    Total configurations: {len(means)}
    
    Net RevPASH Statistics:
      Mean:   {np.mean(means):.3f}
      Std:    {np.std(means):.3f}
      Min:    {np.min(means):.3f}
      Max:    {np.max(means):.3f}
      Range:  {np.max(means) - np.min(means):.3f}
    
    Best Configuration:
      {labels[best_idx]}
      Mean: {means[best_idx]:.3f}
    
    Positive configs: {sum(1 for m in means if m > 0)} / {len(means)}
    """
    ax4.text(0.1, 0.5, stats_text, fontsize=11, family='monospace',
             verticalalignment='center', transform=ax4.transAxes)
    
    plt.tight_layout()
    plt.show()


def plot_subset_selection(screening_results: Dict[int, Dict], 
                          selection: Dict,
                          top_n_display: int = 20):
    """
    Visualize subset selection results showing which configs were kept/screened.
    """
    # Extract data
    indices = list(screening_results.keys())
    means = [screening_results[i]['ci']['mean'] for i in indices]
    half_widths = [screening_results[i]['ci']['half_width'] for i in indices]
    labels = [config_to_label(screening_results[i]['config']) for i in indices]
    
    # Sort by mean
    sorted_data = sorted(zip(indices, means, half_widths, labels), 
                         key=lambda x: x[1], reverse=True)
    
    may_be_best = set(selection['may_be_best'])
    best_idx = selection['best_idx']
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Plot 1: Top configs with selection status
    ax1 = axes[0]
    display_data = sorted_data[:top_n_display]
    
    y_pos = np.arange(len(display_data))
    colors = []
    for idx, mean, hw, label in display_data:
        if idx == best_idx:
            colors.append('#FFD700')  # Gold for best
        elif idx in may_be_best:
            colors.append('#90EE90')  # Light green for may-be-best
        else:
            colors.append('#FFB6C1')  # Light red for screened out
    
    bars = ax1.barh(y_pos, [d[1] for d in display_data], 
                    xerr=[d[2] for d in display_data],
                    color=colors, edgecolor='black', linewidth=0.8, capsize=3)
    
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels([d[3] for d in display_data], fontsize=8)
    ax1.set_xlabel('Net RevPASH (mean ± CI)', fontsize=10)
    ax1.set_title(f'Top {len(display_data)} Configs: Selection Status', fontsize=12, fontweight='bold')
    ax1.invert_yaxis()
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#FFD700', edgecolor='black', label='Sample Best'),
        Patch(facecolor='#90EE90', edgecolor='black', label='May Be Best'),
        Patch(facecolor='#FFB6C1', edgecolor='black', label='Screened Out')
    ]
    ax1.legend(handles=legend_elements, loc='lower right', fontsize=9)
    
    # Plot 2: Selection summary pie chart and stats
    ax2 = axes[1]
    
    n_may_be_best = len(may_be_best)
    n_screened_out = len(indices) - n_may_be_best
    
    # Pie chart
    sizes = [n_may_be_best, n_screened_out]
    labels_pie = [f'May Be Best\n({n_may_be_best})', f'Screened Out\n({n_screened_out})']
    colors_pie = ['#90EE90', '#FFB6C1']
    explode = (0.05, 0)
    
    ax2.pie(sizes, explode=explode, labels=labels_pie, colors=colors_pie,
            autopct='%1.1f%%', shadow=True, startangle=90,
            textprops={'fontsize': 11})
    ax2.set_title('Subset Selection Results', fontsize=12, fontweight='bold')
    
    # Add text summary below
    reduction = (1 - n_may_be_best / len(indices)) * 100
    summary = f"Reduced search space by {reduction:.1f}%"
    ax2.text(0.5, -0.1, summary, fontsize=11, ha='center', transform=ax2.transAxes,
             fontweight='bold', color='#2E86AB')
    
    plt.tight_layout()
    plt.show()


def plot_precision_convergence(final_results: Dict[int, Dict],
                               screening_results: Dict[int, Dict]):
    """
    Visualize precision study convergence for each promising config.
    """
    n_configs = len(final_results)
    if n_configs == 0:
        print("No final results to plot.")
        return
    
    # Determine subplot layout
    n_cols = min(2, n_configs)
    n_rows = (n_configs + n_cols - 1) // n_cols
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(6*n_cols, 4*n_rows))
    if n_configs == 1:
        axes = np.array([axes])
    axes = axes.flatten() if n_configs > 1 else [axes]
    
    for i, (idx, result) in enumerate(final_results.items()):
        ax = axes[i]
        label = config_to_label(screening_results[idx]['config'])
        
        # Get convergence history if available
        history = result.get('history', [])
        if history:
            # History is a list of tuples: (n, rel_error)
            ns = [h[0] for h in history]
            rel_errors = [h[1] * 100 for h in history]
            
            ax.plot(ns, rel_errors, 'bo-', linewidth=2, markersize=8)
            ax.axhline(y=5.0, color='red', linestyle='--', linewidth=2, 
                      label='Target (5%)')
            
            # Shade achieved region
            ax.fill_between([ns[0], ns[-1]], [0, 0], [5, 5], alpha=0.2, color='green')
            
            ax.set_xlabel('Number of Replications', fontsize=10)
            ax.set_ylabel('Relative Error (%)', fontsize=10)
            ax.set_title(f'{label}', fontsize=11, fontweight='bold')
            ax.legend(loc='upper right', fontsize=9)
            ax.grid(True, alpha=0.3)
            ax.set_ylim(0, max(rel_errors) * 1.1)
        else:
            # No iteration history, show final result
            final_ci = result['ci']
            ax.bar([0], [final_ci['half_width_rel']*100], color='steelblue', 
                   edgecolor='black')
            ax.axhline(y=5.0, color='red', linestyle='--', linewidth=2)
            ax.set_ylabel('Relative Error (%)', fontsize=10)
            ax.set_title(f'{label}', fontsize=11, fontweight='bold')
            ax.set_xticks([])
    
    # Hide unused subplots
    for j in range(i+1, len(axes)):
        axes[j].axis('off')
    
    plt.suptitle('Precision Convergence per Configuration', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.show()
    
    # Also show final comparison bar chart
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    
    labels = [config_to_label(screening_results[idx]['config']) for idx in final_results.keys()]
    means = [final_results[idx]['ci']['mean'] for idx in final_results.keys()]
    half_widths = [final_results[idx]['ci']['half_width'] for idx in final_results.keys()]
    n_samples = [len(final_results[idx]['all_samples']) for idx in final_results.keys()]
    
    x = np.arange(len(labels))
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(labels)))
    
    bars = ax2.bar(x, means, yerr=half_widths, color=colors, 
                   edgecolor='black', linewidth=1.2, capsize=5)
    
    # Add sample size labels
    for bar, n in zip(bars, n_samples):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + half_widths[bars.index(bar)] + 0.05,
                f'n={n}', ha='center', va='bottom', fontsize=9)
    
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=30, ha='right', fontsize=9)
    ax2.set_ylabel('Net RevPASH', fontsize=11)
    ax2.set_title('Final Precision Results (Promising Configurations)', fontsize=12, fontweight='bold')
    ax2.grid(True, axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.show()


def plot_pairwise_comparisons(final_results: Dict[int, Dict],
                              screening_results: Dict[int, Dict],
                              confidence: float = 0.95):
    """
    Visualize pairwise comparisons with heatmap and CI plots.
    """
    indices = list(final_results.keys())
    n = len(indices)
    
    if n < 2:
        print("Need at least 2 configurations for pairwise comparison.")
        return
    
    labels = [config_to_label(screening_results[idx]['config']) for idx in indices]
    
    # Compute all pairwise differences
    diff_matrix = np.zeros((n, n))
    sig_matrix = np.zeros((n, n))  # 1 if significant, 0 otherwise
    
    for i, idx_i in enumerate(indices):
        for j, idx_j in enumerate(indices):
            if i != j:
                comp = compare_configurations_pairwise(
                    final_results[idx_i]['all_samples'],
                    final_results[idx_j]['all_samples'],
                    confidence=confidence
                )
                diff_matrix[i, j] = comp['mean_diff']
                sig_matrix[i, j] = 1 if comp['significant'] else 0
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Plot 1: Heatmap of differences
    ax1 = axes[0]
    mask = np.eye(n, dtype=bool)
    
    sns.heatmap(diff_matrix, annot=True, fmt='.3f', cmap='RdYlGn', center=0,
                xticklabels=labels, yticklabels=labels, mask=mask,
                ax=ax1, cbar_kws={'label': 'Difference (Row - Col)'},
                linewidths=0.5, linecolor='white')
    
    # Add stars for significant differences
    for i in range(n):
        for j in range(n):
            if i != j and sig_matrix[i, j]:
                ax1.text(j + 0.5, i + 0.75, '*', fontsize=14, 
                        color='black', ha='center', va='center', fontweight='bold')
    
    ax1.set_title('Pairwise Mean Differences\n(* = statistically significant)', 
                  fontsize=12, fontweight='bold')
    ax1.tick_params(axis='x', rotation=45)
    ax1.tick_params(axis='y', rotation=0)
    
    # Plot 2: CI comparison bars
    ax2 = axes[1]
    
    # Sort by mean
    sorted_indices = sorted(indices, key=lambda i: final_results[i]['ci']['mean'], reverse=True)
    sorted_labels = [config_to_label(screening_results[idx]['config']) for idx in sorted_indices]
    sorted_means = [final_results[idx]['ci']['mean'] for idx in sorted_indices]
    sorted_lowers = [final_results[idx]['ci']['ci_lower'] for idx in sorted_indices]
    sorted_uppers = [final_results[idx]['ci']['ci_upper'] for idx in sorted_indices]
    
    y_pos = np.arange(len(sorted_labels))
    
    # Plot CI ranges as horizontal lines with points
    for i, (mean, lower, upper, label) in enumerate(zip(sorted_means, sorted_lowers, sorted_uppers, sorted_labels)):
        color = plt.cm.viridis(i / len(sorted_labels))
        ax2.hlines(y=i, xmin=lower, xmax=upper, color=color, linewidth=3, alpha=0.7)
        ax2.plot(mean, i, 'o', color=color, markersize=10, markeredgecolor='black')
    
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(sorted_labels, fontsize=9)
    ax2.set_xlabel('Net RevPASH', fontsize=11)
    ax2.set_title('Final Confidence Intervals (Ranked)', fontsize=12, fontweight='bold')
    ax2.invert_yaxis()
    ax2.grid(True, axis='x', alpha=0.3)
    
    # Add annotation
    ax2.text(0.02, 0.98, 'Higher is better ↑', transform=ax2.transAxes,
             fontsize=9, verticalalignment='top', style='italic', color='gray')
    
    plt.tight_layout()
    plt.show()
    
    # Print summary
    print("\nPairwise Comparison Summary:")
    print("=" * 50)
    best_idx = sorted_indices[0]
    best_label = config_to_label(screening_results[best_idx]['config'])
    print(f"Best configuration: {best_label}")
    print(f"Mean: {final_results[best_idx]['ci']['mean']:.3f}")
    
    n_sig = int(np.sum(sig_matrix) / 2)  # Each pair counted twice
    print(f"\nSignificant differences found: {n_sig} pairs")
    
    if n_sig == 0:
        print("⚠ No statistically significant differences between top configurations.")
        print("  Consider: running more replications OR accepting they perform similarly.")

