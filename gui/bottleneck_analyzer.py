"""Bottleneck identification and analysis for Restaurant Simulation.

This module analyzes simulation data to identify operational bottlenecks
in stations, queues, and staffing, and provides actionable recommendations.
"""

from typing import Dict, List, Any, Tuple
import pandas as pd
import numpy as np


def analyze_station_bottlenecks(station_util_df: pd.DataFrame, queue_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Analyze kitchen stations to identify bottlenecks.
    
    Calculates a bottleneck score based on:
    - Utilization (40% weight)
    - Queue length (30% weight)
    - Wait time proxy (30% weight)
    
    Args:
        station_util_df: DataFrame with station utilization data
        queue_df: DataFrame with queue metrics
        
    Returns:
        List of bottleneck dicts with station name, score, severity, and metrics
    """
    if station_util_df.empty:
        return []
    
    bottlenecks = []
    
    # Find station columns
    station_names = [col.replace('_utilization', '') for col in station_util_df.columns 
                     if col.endswith('_utilization') and col != 'overall_station_utilization']
    
    for station_name in station_names:
        util_col = f"{station_name}_utilization"
        queue_col = f"{station_name}_queue"
        
        if util_col not in station_util_df.columns:
            continue
            
        # Calculate average metrics
        avg_utilization = station_util_df[util_col].mean()
        
        # Get queue data if available
        avg_queue_length = 0.0
        if queue_col in queue_df.columns:
            avg_queue_length = queue_df[queue_col].mean()
        elif queue_col in station_util_df.columns:
            avg_queue_length = station_util_df[queue_col].mean()
        
        # Normalize metrics
        normalized_utilization = min(avg_utilization, 1.0)
        normalized_queue = min(avg_queue_length / 5.0, 1.0)  # 5+ is considered max
        
        # Calculate bottleneck score
        bottleneck_score = (
            0.4 * normalized_utilization +
            0.3 * normalized_queue +
            0.3 * normalized_queue  # Using queue as proxy for wait time
        )
        
        # Determine severity
        if bottleneck_score > 0.7:
            severity = "critical"
        elif bottleneck_score > 0.5:
            severity = "warning"
        else:
            severity = "healthy"
        
        # Only include if it's a potential bottleneck
        if bottleneck_score > 0.4:
            bottlenecks.append({
                'station_name': station_name.replace('_', ' ').title(),
                'score': bottleneck_score,
                'severity': severity,
                'avg_utilization': avg_utilization,
                'avg_queue_length': avg_queue_length,
                'recommendation': _generate_station_recommendation(
                    station_name, avg_utilization, avg_queue_length, severity
                )
            })
    
    # Sort by score descending
    bottlenecks.sort(key=lambda x: x['score'], reverse=True)
    
    return bottlenecks


def analyze_queue_bottlenecks(queue_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Analyze system queues to identify bottlenecks.
    
    Args:
        queue_df: DataFrame with queue metrics over time
        
    Returns:
        List of queue bottleneck dicts with queue name, average length, and recommendations
    """
    if queue_df.empty:
        return []
    
    bottlenecks = []
    
    # Queue columns to analyze
    queue_columns = {
        'guest_queue': 'Guest Queue (Arrivals)',
        'host_queue': 'Host Queue (Seating)',
        'expo_queue': 'Expo Queue (Quality Check)',
        'food_runner_queue': 'Food Runner Queue (Delivery)'
    }
    
    for queue_col, display_name in queue_columns.items():
        if queue_col not in queue_df.columns:
            continue
        
        avg_length = queue_df[queue_col].mean()
        max_length = queue_df[queue_col].max()
        p95_length = queue_df[queue_col].quantile(0.95)
        
        # Identify bottlenecks (average > 3 or p95 > 5)
        if avg_length > 3.0 or p95_length > 5.0:
            severity = "critical" if avg_length > 5.0 else "warning"
            
            bottlenecks.append({
                'queue_name': display_name,
                'avg_length': avg_length,
                'max_length': max_length,
                'p95_length': p95_length,
                'severity': severity,
                'recommendation': _generate_queue_recommendation(queue_col, avg_length, severity)
            })
    
    # Sort by average length descending
    bottlenecks.sort(key=lambda x: x['avg_length'], reverse=True)
    
    return bottlenecks


def analyze_staff_bottlenecks(staff_util_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Analyze staff utilization to identify over/underutilized staff types.
    
    Args:
        staff_util_df: DataFrame with staff utilization metrics
        
    Returns:
        List of staff bottleneck dicts with staff type, utilization, and recommendations
    """
    if staff_util_df.empty:
        return []
    
    bottlenecks = []
    
    # Staff types to analyze
    staff_types = {
        'host_utilization': 'Hosts',
        'server_utilization': 'Servers',
        'food_runner_utilization': 'Food Runners',
        'busser_utilization': 'Bussers'
    }
    
    for util_col, display_name in staff_types.items():
        if util_col not in staff_util_df.columns:
            continue
        
        avg_utilization = staff_util_df[util_col].mean()
        max_utilization = staff_util_df[util_col].max()
        p95_utilization = staff_util_df[util_col].quantile(0.95)
        
        # Identify issues
        if avg_utilization > 0.90 or p95_utilization > 0.95:
            # Overworked
            severity = "critical" if avg_utilization > 0.95 else "warning"
            issue_type = "overworked"
        elif avg_utilization < 0.30:
            # Underutilized
            severity = "info"
            issue_type = "underutilized"
        else:
            # Normal range
            continue
        
        bottlenecks.append({
            'staff_type': display_name,
            'avg_utilization': avg_utilization,
            'max_utilization': max_utilization,
            'p95_utilization': p95_utilization,
            'issue_type': issue_type,
            'severity': severity,
            'recommendation': _generate_staff_recommendation(
                display_name, avg_utilization, issue_type, severity
            )
        })
    
    # Sort by severity and utilization
    severity_order = {'critical': 0, 'warning': 1, 'info': 2}
    bottlenecks.sort(key=lambda x: (severity_order.get(x['severity'], 3), -x['avg_utilization']))
    
    return bottlenecks


def generate_recommendations(bottlenecks: Dict[str, List[Dict[str, Any]]]) -> List[str]:
    """Generate actionable recommendations from all bottleneck analyses.
    
    Args:
        bottlenecks: Dict containing 'stations', 'queues', and 'staff' bottleneck lists
        
    Returns:
        List of recommendation strings
    """
    recommendations = []
    
    # Station recommendations
    station_bottlenecks = bottlenecks.get('stations', [])
    for bottleneck in station_bottlenecks[:3]:  # Top 3
        if bottleneck['severity'] in ['critical', 'warning']:
            recommendations.append(bottleneck['recommendation'])
    
    # Queue recommendations
    queue_bottlenecks = bottlenecks.get('queues', [])
    for bottleneck in queue_bottlenecks[:2]:  # Top 2
        recommendations.append(bottleneck['recommendation'])
    
    # Staff recommendations
    staff_bottlenecks = bottlenecks.get('staff', [])
    for bottleneck in staff_bottlenecks:
        if bottleneck['severity'] in ['critical', 'warning']:
            recommendations.append(bottleneck['recommendation'])
    
    # If no recommendations, add positive feedback
    if not recommendations:
        recommendations.append("✓ All systems operating within normal parameters")
        recommendations.append("✓ No critical bottlenecks identified")
    
    return recommendations


# Helper functions for generating specific recommendations

def _generate_station_recommendation(station_name: str, utilization: float, queue_length: float, severity: str) -> str:
    """Generate station-specific recommendation."""
    display_name = station_name.replace('_', ' ').title()
    
    if severity == "critical":
        if utilization > 0.85:
            return f"🔴 {display_name}: Add capacity or redistribute workload (util: {utilization*100:.0f}%)"
        else:
            return f"🔴 {display_name}: Queue averaging {queue_length:.1f} - add capacity"
    elif severity == "warning":
        return f"🟡 {display_name}: Monitor closely (util: {utilization*100:.0f}%, queue: {queue_length:.1f})"
    else:
        return f"🟢 {display_name}: Operating normally"


def _generate_queue_recommendation(queue_name: str, avg_length: float, severity: str) -> str:
    """Generate queue-specific recommendation."""
    if 'guest' in queue_name.lower():
        action = "Add hosts or streamline seating process"
    elif 'host' in queue_name.lower():
        action = "Review host workflow or add host staff"
    elif 'expo' in queue_name.lower():
        action = "Increase expo capacity or add quality check staff"
    elif 'runner' in queue_name.lower():
        action = "Add food runners"
    else:
        action = "Review queue workflow"
    
    symbol = "🔴" if severity == "critical" else "🟡"
    return f"{symbol} {queue_name}: Avg {avg_length:.1f} customers waiting - {action}"


def _generate_staff_recommendation(staff_type: str, utilization: float, issue_type: str, severity: str) -> str:
    """Generate staff-specific recommendation."""
    if issue_type == "overworked":
        symbol = "🔴" if severity == "critical" else "🟡"
        return f"{symbol} {staff_type}: {utilization*100:.0f}% utilized - Add {1 if utilization < 0.95 else 2} more staff"
    else:  # underutilized
        return f"ℹ️ {staff_type}: {utilization*100:.0f}% utilized - Consider reducing staff or expanding responsibilities"


def get_overall_health_status(bottlenecks: Dict[str, List[Dict[str, Any]]]) -> Tuple[str, str]:
    """Determine overall system health status.
    
    Args:
        bottlenecks: Dict containing all bottleneck analyses
        
    Returns:
        Tuple of (status: str, color: str) where status is "Healthy", "Warning", or "Critical"
    """
    # Count critical and warning issues
    critical_count = 0
    warning_count = 0
    
    for category in ['stations', 'queues', 'staff']:
        for bottleneck in bottlenecks.get(category, []):
            if bottleneck.get('severity') == 'critical':
                critical_count += 1
            elif bottleneck.get('severity') == 'warning':
                warning_count += 1
    
    # Determine overall status
    if critical_count > 0:
        return ("Critical", "🔴")
    elif warning_count > 2:
        return ("Warning", "🟡")
    elif warning_count > 0:
        return ("Caution", "🟡")
    else:
        return ("Healthy", "🟢")

