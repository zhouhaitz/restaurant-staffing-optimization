"""Arrival rate parameter fitting from CSV data.

This module provides functions to:
- Parse CSV files with order/guest data
- Calculate hourly arrival rates
- Fit NHPP (Non-Homogeneous Poisson Process) parameters using Gaussian peak model
- Visualize fitted curves
"""

import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
from typing import Dict, Tuple, Optional
import plotly.graph_objects as go
from datetime import datetime


def gaussian_nhpp_model(t: np.ndarray, lambda_base: float, lambda_peak: float, 
                        peak_time: float, peak_width: float) -> np.ndarray:
    """Gaussian NHPP model: lambda(t) = lambda_base + lambda_peak * exp(-((t-peak_time)^2)/(2*peak_width^2))
    
    Args:
        t: Time in minutes
        lambda_base: Base arrival rate (parties/min)
        lambda_peak: Peak multiplier (parties/min)
        peak_time: Time of peak arrivals (minutes)
        peak_width: Width of peak (minutes)
    
    Returns:
        Arrival rate at time t
    """
    return lambda_base + lambda_peak * np.exp(-((t - peak_time) ** 2) / (2 * peak_width ** 2))


def fit_nhpp_from_csv(
    csv_path: str,
    start_hour: int = 17,
    day_of_week: Optional[str] = None,
    count_column: str = '# of Guests',
    timestamp_column: str = 'Opened',
    dining_option: str = 'Dine In',
    use_parties: bool = True
) -> Dict[str, float]:
    """Fit NHPP parameters from CSV data with order timestamps.
    
    Args:
        csv_path: Path to CSV file (same format as OrderDetails CSV)
        start_hour: Starting hour for time offset calculation (default: 17 for 5 PM)
        day_of_week: Filter for specific day (e.g., 'Friday'). If None, uses all days.
        count_column: Column name for guest/party count
        timestamp_column: Column name for timestamp
        dining_option: Filter for dining option (default: 'Dine In')
        use_parties: If True, count orders as parties; if False, sum guest counts
    
    Returns:
        Dictionary with fitted parameters:
        - lambda_base: Base arrival rate (parties/min)
        - lambda_peak_multiplier: Peak multiplier (parties/min)
        - peak_time: Time of peak arrivals (minutes from start)
        - peak_width: Width of peak (minutes)
        - r_squared: R² goodness of fit
        - observed_data: DataFrame with observed hourly data
    """
    # Read CSV
    df = pd.read_csv(csv_path)
    
    # Parse timestamp
    df[timestamp_column] = pd.to_datetime(df[timestamp_column], errors='coerce')
    
    # Filter for dining option if column exists
    if 'Dining Options' in df.columns:
        df = df[df['Dining Options'] == dining_option].copy()
    
    # Add day of week
    df['DayOfWeek'] = df[timestamp_column].dt.day_name()
    
    # Filter for specific day if requested
    if day_of_week:
        df = df[df['DayOfWeek'] == day_of_week].copy()
    
    if len(df) == 0:
        raise ValueError(f"No data found for day: {day_of_week if day_of_week else 'all days'}")
    
    # Add hour offset from start_hour
    df['hour_offset'] = df[timestamp_column].dt.hour - start_hour
    
    # Filter for valid hours (0-5 typically represents 5 PM to 10 PM)
    df = df[df['hour_offset'] >= 0].copy()
    
    # Calculate arrivals per hour
    if use_parties:
        # Count number of orders (parties) per hour
        hourly_arrivals = df.groupby('hour_offset').size()
    else:
        # Sum guest counts per hour
        hourly_arrivals = df.groupby('hour_offset')[count_column].sum()
    
    # Get number of unique days in dataset for averaging
    num_days = df[timestamp_column].dt.date.nunique()
    
    # Calculate average arrivals per hour
    avg_hourly_arrivals = hourly_arrivals / num_days
    
    # Convert to minutes (time_minutes) and parties/min (arrival_rates_per_minute)
    time_hours = np.array(avg_hourly_arrivals.index)
    time_minutes = time_hours * 60  # Convert to minutes from start
    arrival_rates_per_hour = np.array(avg_hourly_arrivals.values)
    arrival_rates_per_minute = arrival_rates_per_hour / 60  # Convert to per minute
    
    # Initial parameter guesses
    lambda_base_guess = arrival_rates_per_minute.min()
    lambda_peak_guess = arrival_rates_per_minute.max() - lambda_base_guess
    peak_time_guess = time_minutes[np.argmax(arrival_rates_per_minute)]
    peak_width_guess = 60.0  # 1 hour
    
    initial_guess = [lambda_base_guess, lambda_peak_guess, peak_time_guess, peak_width_guess]
    
    # Parameter bounds (all positive, reasonable ranges)
    bounds = (
        [0, 0, 0, 10],  # Lower bounds
        [1.0, 2.0, 360, 200]  # Upper bounds
    )
    
    try:
        # Fit the model
        popt, pcov = curve_fit(
            gaussian_nhpp_model,
            time_minutes,
            arrival_rates_per_minute,
            p0=initial_guess,
            bounds=bounds,
            maxfev=10000
        )
        
        lambda_base, lambda_peak_multiplier, peak_time, peak_width = popt
        
        # Calculate R²
        predicted_rates = gaussian_nhpp_model(time_minutes, *popt)
        ss_res = np.sum((arrival_rates_per_minute - predicted_rates) ** 2)
        ss_tot = np.sum((arrival_rates_per_minute - np.mean(arrival_rates_per_minute)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # Create observed data DataFrame for visualization
        observed_data = pd.DataFrame({
            'time_minutes': time_minutes,
            'time_hours': time_hours,
            'arrival_rate_per_minute': arrival_rates_per_minute,
            'arrival_rate_per_hour': arrival_rates_per_hour
        })
        
        return {
            'lambda_base': float(lambda_base),
            'lambda_peak_multiplier': float(lambda_peak_multiplier),
            'peak_time': float(peak_time),
            'peak_width': float(peak_width),
            'r_squared': float(r_squared),
            'observed_data': observed_data,
            'num_days_averaged': num_days
        }
        
    except Exception as e:
        raise RuntimeError(f"Failed to fit NHPP parameters: {str(e)}")


def visualize_fitted_curve(
    params: Dict,
    observed_data: Optional[pd.DataFrame] = None,
    title: str = "Arrival Rate: Fitted NHPP Model"
) -> go.Figure:
    """Visualize fitted NHPP curve with observed data.
    
    Args:
        params: Dictionary with fitted parameters (from fit_nhpp_from_csv)
        observed_data: DataFrame with observed data (optional, included in params)
        title: Plot title
    
    Returns:
        Plotly figure
    """
    if observed_data is None:
        observed_data = params.get('observed_data')
    
    if observed_data is None:
        raise ValueError("No observed data provided for visualization")
    
    # Create fine-grained time array for smooth curve
    time_min = observed_data['time_minutes'].min()
    time_max = observed_data['time_minutes'].max()
    time_fine = np.linspace(time_min, time_max, 200)
    
    # Calculate fitted curve
    fitted_rates = gaussian_nhpp_model(
        time_fine,
        params['lambda_base'],
        params['lambda_peak_multiplier'],
        params['peak_time'],
        params['peak_width']
    )
    
    # Create figure
    fig = go.Figure()
    
    # Add observed data
    fig.add_trace(go.Scatter(
        x=observed_data['time_minutes'],
        y=observed_data['arrival_rate_per_minute'],
        mode='markers',
        name='Observed Data',
        marker=dict(size=10, color='blue'),
        hovertemplate='Time: %{x:.0f} min<br>Rate: %{y:.6f} parties/min<extra></extra>'
    ))
    
    # Add fitted curve
    fig.add_trace(go.Scatter(
        x=time_fine,
        y=fitted_rates,
        mode='lines',
        name='Fitted Curve',
        line=dict(color='red', width=2),
        hovertemplate='Time: %{x:.0f} min<br>Rate: %{y:.6f} parties/min<extra></extra>'
    ))
    
    # Update layout
    fig.update_layout(
        title=f"{title}<br>R² = {params['r_squared']:.4f}",
        xaxis_title="Time (minutes from start)",
        yaxis_title="Arrival Rate (parties/minute)",
        hovermode='x unified',
        legend=dict(x=0.02, y=0.98),
        height=500
    )
    
    return fig


def preview_fitted_parameters(params: Dict) -> str:
    """Generate a formatted string preview of fitted parameters.
    
    Args:
        params: Dictionary with fitted parameters
    
    Returns:
        Formatted string with parameter values
    """
    return f"""
**Fitted NHPP Parameters:**

- **λ_base**: {params['lambda_base']:.6f} parties/min
- **λ_peak**: {params['lambda_peak_multiplier']:.6f} parties/min
- **Peak time**: {params['peak_time']:.2f} minutes ({params['peak_time']/60:.2f} hours)
- **Peak width**: {params['peak_width']:.2f} minutes
- **R² (goodness of fit)**: {params['r_squared']:.4f}
- **Days averaged**: {params.get('num_days_averaged', 'N/A')}

*These parameters can be used directly in the simulation configuration.*
"""

