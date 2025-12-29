"""Interactive visualizations for Executive Dashboard.

This module provides Plotly-based interactive charts for the executive dashboard,
including financial overviews, service quality breakdowns, and bottleneck visualizations.
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, List, Any
import numpy as np


def plot_financial_overview(financial_kpis: Dict[str, float], revpash_df: pd.DataFrame) -> go.Figure:
    """Create combined financial overview chart.
    
    Shows RevPASH over time and Revenue vs Labor Cost comparison.
    
    Args:
        financial_kpis: Dictionary of financial KPIs
        revpash_df: DataFrame with RevPASH over time
        
    Returns:
        Plotly figure
    """
    # Create subplots: 2 rows
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("RevPASH Over Time", "Revenue vs Labor Cost"),
        specs=[[{"type": "scatter"}], [{"type": "bar"}]],
        vertical_spacing=0.15,
        row_heights=[0.6, 0.4]
    )
    
    # Plot 1: RevPASH over time
    fig.add_trace(
        go.Scatter(
            x=revpash_df['time'],
            y=revpash_df['revpash'],
            mode='lines',
            name='RevPASH',
            line=dict(color='#1f77b4', width=2),
            fill='tozeroy',
            fillcolor='rgba(31, 119, 180, 0.3)'
        ),
        row=1, col=1
    )
    
    # Plot 2: Revenue vs Labor Cost
    categories = ['Gross Revenue', 'Net Revenue', 'Labor Cost']
    values = [
        financial_kpis.get('total_revenue', 0),
        financial_kpis.get('total_revenue', 0) - financial_kpis.get('total_labor_cost', 0),
        financial_kpis.get('total_labor_cost', 0)
    ]
    colors = ['#2ca02c', '#1f77b4', '#d62728']
    
    fig.add_trace(
        go.Bar(
            x=categories,
            y=values,
            marker_color=colors,
            text=[f'${v:,.0f}' for v in values],
            textposition='auto',
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Update layout
    fig.update_xaxes(title_text="Time (minutes)", row=1, col=1)
    fig.update_yaxes(title_text="RevPASH ($)", row=1, col=1)
    fig.update_xaxes(title_text="", row=2, col=1)
    fig.update_yaxes(title_text="Amount ($)", row=2, col=1)
    
    fig.update_layout(
        height=600,
        showlegend=False,
        hovermode='x unified'
    )
    
    return fig


def plot_service_quality_breakdown(service_kpis: Dict[str, float], service_times: Dict) -> go.Figure:
    """Create service quality breakdown visualizations.
    
    Shows wait time distribution and service quality score components.
    
    Args:
        service_kpis: Dictionary of service quality KPIs
        service_times: Dictionary with lists of service times
        
    Returns:
        Plotly figure
    """
    # Create subplots
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Wait Time Distribution", "Service Quality Components"),
        specs=[[{"type": "histogram"}, {"type": "bar"}]]
    )
    
    # Plot 1: Wait time histogram
    wait_times = service_times.get('wait_times', [0])
    if wait_times:
        fig.add_trace(
            go.Histogram(
                x=wait_times,
                nbinsx=20,
                name='Wait Times',
                marker_color='#ff7f0e',
                showlegend=False
            ),
            row=1, col=1
        )
    
    # Plot 2: Service quality components
    components = ['Wait Time', 'Kitchen Time', 'Delivery Time']
    avg_times = [
        service_kpis.get('avg_wait_time', 0),
        service_kpis.get('avg_kitchen_time', 0),
        service_kpis.get('avg_order_to_delivery', 0)
    ]
    targets = [5, 15, 5]  # Target times in minutes
    
    fig.add_trace(
        go.Bar(
            x=components,
            y=avg_times,
            name='Actual',
            marker_color='#1f77b4',
            text=[f'{t:.1f}m' for t in avg_times],
            textposition='auto'
        ),
        row=1, col=2
    )
    
    fig.add_trace(
        go.Scatter(
            x=components,
            y=targets,
            mode='markers+lines',
            name='Target',
            marker=dict(color='#d62728', size=10, symbol='diamond'),
            line=dict(color='#d62728', width=2, dash='dash')
        ),
        row=1, col=2
    )
    
    # Update layout
    fig.update_xaxes(title_text="Wait Time (minutes)", row=1, col=1)
    fig.update_yaxes(title_text="Frequency", row=1, col=1)
    fig.update_xaxes(title_text="", row=1, col=2)
    fig.update_yaxes(title_text="Time (minutes)", row=1, col=2)
    
    fig.update_layout(
        height=400,
        showlegend=True,
        legend=dict(x=0.7, y=0.5)
    )
    
    return fig


def plot_operational_efficiency(
    operational_kpis: Dict[str, float],
    queue_df: pd.DataFrame
) -> go.Figure:
    """Create operational efficiency visualization.
    
    Shows throughput metrics and queue lengths over time.
    
    Args:
        operational_kpis: Dictionary of operational KPIs
        queue_df: DataFrame with queue metrics over time
        
    Returns:
        Plotly figure
    """
    # Create subplots
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Utilization Rates", "Queue Lengths Over Time"),
        specs=[[{"type": "bar"}], [{"type": "scatter"}]],
        vertical_spacing=0.15,
        row_heights=[0.4, 0.6]
    )
    
    # Plot 1: Utilization rates
    util_categories = ['Tables', 'Stations', 'Staff']
    util_values = [
        operational_kpis.get('avg_table_utilization', 0) * 100,
        operational_kpis.get('avg_station_utilization', 0) * 100,
        operational_kpis.get('avg_staff_utilization', 0) * 100
    ]
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    
    fig.add_trace(
        go.Bar(
            x=util_categories,
            y=util_values,
            marker_color=colors,
            text=[f'{v:.1f}%' for v in util_values],
            textposition='auto',
            showlegend=False
        ),
        row=1, col=1
    )
    
    # Add target line at 80%
    fig.add_hline(y=80, line_dash="dash", line_color="red", 
                   annotation_text="Target: 80%", row=1, col=1)
    
    # Plot 2: Queue lengths
    if not queue_df.empty and 'time' in queue_df.columns:
        queue_columns = {
            'guest_queue': 'Guest Queue',
            'host_queue': 'Host Queue',
            'expo_queue': 'Expo Queue',
            'food_runner_queue': 'Food Runner Queue'
        }
        
        for col, name in queue_columns.items():
            if col in queue_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=queue_df['time'],
                        y=queue_df[col],
                        mode='lines',
                        name=name,
                        line=dict(width=2)
                    ),
                    row=2, col=1
                )
    
    # Update layout
    fig.update_xaxes(title_text="", row=1, col=1)
    fig.update_yaxes(title_text="Utilization (%)", row=1, col=1)
    fig.update_xaxes(title_text="Time (minutes)", row=2, col=1)
    fig.update_yaxes(title_text="Queue Length", row=2, col=1)
    
    fig.update_layout(
        height=600,
        showlegend=True,
        legend=dict(x=1.05, y=0.5)
    )
    
    return fig


def plot_bottleneck_severity(bottlenecks: Dict[str, List[Dict[str, Any]]]) -> go.Figure:
    """Create bottleneck severity visualization.
    
    Bar chart showing bottleneck scores by category and severity.
    
    Args:
        bottlenecks: Dictionary containing station, queue, and staff bottlenecks
        
    Returns:
        Plotly figure
    """
    # Collect all bottlenecks
    items = []
    scores = []
    colors = []
    categories = []
    
    severity_colors = {
        'critical': '#d62728',
        'warning': '#ff7f0e',
        'healthy': '#2ca02c',
        'info': '#17becf'
    }
    
    # Station bottlenecks
    for b in bottlenecks.get('stations', [])[:5]:  # Top 5
        items.append(b['station_name'])
        scores.append(b['score'])
        colors.append(severity_colors.get(b['severity'], '#7f7f7f'))
        categories.append('Station')
    
    # Queue bottlenecks
    for b in bottlenecks.get('queues', [])[:3]:  # Top 3
        items.append(b['queue_name'])
        scores.append(b['avg_length'] / 10.0)  # Normalize to 0-1 scale
        colors.append(severity_colors.get(b['severity'], '#7f7f7f'))
        categories.append('Queue')
    
    # Staff bottlenecks
    for b in bottlenecks.get('staff', []):
        items.append(b['staff_type'])
        if b['issue_type'] == 'overworked':
            scores.append(b['avg_utilization'])
        else:
            scores.append(1 - b['avg_utilization'])  # Invert for underutilized
        colors.append(severity_colors.get(b['severity'], '#7f7f7f'))
        categories.append('Staff')
    
    if not items:
        # No bottlenecks - show success message
        fig = go.Figure()
        fig.add_annotation(
            text="✓ No significant bottlenecks detected",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=20, color="green")
        )
        fig.update_layout(height=300)
        return fig
    
    # Create bar chart
    fig = go.Figure(data=[
        go.Bar(
            y=items,
            x=scores,
            orientation='h',
            marker_color=colors,
            text=[f'{s:.2f}' for s in scores],
            textposition='auto',
            hovertemplate='<b>%{y}</b><br>Score: %{x:.2f}<br>Category: %{customdata}<extra></extra>',
            customdata=categories
        )
    ])
    
    fig.update_layout(
        title="Bottleneck Severity Scores",
        xaxis_title="Severity Score",
        yaxis_title="",
        height=max(300, len(items) * 40),
        showlegend=False
    )
    
    return fig


def create_metrics_table(metrics_dict: Dict[str, float], category: str) -> pd.DataFrame:
    """Create formatted metrics table with statistics.
    
    Args:
        metrics_dict: Dictionary of metrics
        category: Category name for display
        
    Returns:
        Formatted DataFrame
    """
    data = []
    
    for key, value in metrics_dict.items():
        # Format key
        display_key = key.replace('_', ' ').title()
        
        # Format value based on type
        if 'percentage' in key or 'utilization' in key or 'rate' in key:
            formatted_value = f"{value:.1f}%"
        elif 'revenue' in key or 'cost' in key or 'revpash' in key:
            formatted_value = f"${value:,.2f}"
        elif 'time' in key:
            formatted_value = f"{value:.1f} min"
        elif 'score' in key:
            formatted_value = f"{value:.0f}/100"
        else:
            formatted_value = f"{value:.2f}"
        
        data.append({
            'Metric': display_key,
            'Value': formatted_value
        })
    
    return pd.DataFrame(data)

