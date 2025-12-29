"""Configuration UI components for simulation parameter setup.

This module provides Streamlit UI components for:
- Staffing level configuration
- Table configuration
- Kitchen station capacity settings
- Arrival rate parameters (manual or CSV-based fitting)
- Advanced settings
"""

import streamlit as st
import sys
from pathlib import Path
from typing import Optional, Dict
import pandas as pd

# Add experiments directory to path
experiments_path = Path(__file__).parent.parent / "experiments"
sys.path.insert(0, str(experiments_path))

from parameters import SingleDishParameters
from dish_loading import load_recipes_from_json
from arrival_rate_fitting import fit_nhpp_from_csv, visualize_fitted_curve, preview_fitted_parameters


def estimate_simulation_runtime(params: SingleDishParameters) -> float:
    """Estimate simulation runtime in seconds.
    
    Formula:
    - Base: 1 second per minute of simulation duration
    - Complexity multiplier based on staffing: (servers + cooks) / 15
    
    Args:
        params: Simulation parameters
    
    Returns:
        Estimated runtime in seconds
    """
    base_time = params.simulation_duration / 60.0  # Convert minutes to assumed seconds
    complexity_multiplier = (params.num_servers + params.num_cooks) / 15.0
    estimated_time = base_time * (1 + complexity_multiplier)
    return estimated_time


def render_simulation_config_ui() -> Optional[SingleDishParameters]:
    """Render comprehensive simulation configuration UI.
    
    Returns:
        SingleDishParameters object if configuration is valid, None otherwise
    """
    st.header("🚀 Simulation Configuration")
    
    # Load base parameters from comal_recipes.json
    base_config_path = Path(__file__).parent.parent / "experiments" / "comal_recipes.json"
    
    try:
        base_params = load_recipes_from_json(str(base_config_path))
    except Exception as e:
        st.error(f"Error loading base configuration: {e}")
        return None
    
    # Initialize session state for parameters if not exists
    if 'config_params' not in st.session_state:
        st.session_state.config_params = {}
    
    # ========== STAFFING LEVELS ==========
    with st.expander("👥 Staffing Levels", expanded=True):
        st.markdown("Configure staff for front-of-house and kitchen operations")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Front of House**")
            num_servers = st.number_input(
                "Servers",
                min_value=0,
                max_value=20,
                value=base_params.num_servers,
                help="Each server handles a zone of tables",
                key="servers"
            )
            num_hosts = st.number_input(
                "Hosts",
                min_value=0,
                max_value=5,
                value=base_params.num_hosts,
                help="Hosts manage guest arrival and seating",
                key="hosts"
            )
        
        with col2:
            st.markdown("**Support Staff**")
            num_food_runners = st.number_input(
                "Food Runners",
                min_value=0,
                max_value=10,
                value=base_params.num_food_runners,
                help="Deliver food from kitchen to tables",
                key="runners"
            )
            num_bussers = st.number_input(
                "Bussers",
                min_value=0,
                max_value=10,
                value=base_params.num_bussers,
                help="Clear and clean tables",
                key="bussers"
            )
        
        with col3:
            st.markdown("**Kitchen**")
            num_cooks = st.number_input(
                "Cooks",
                min_value=0,
                max_value=30,
                value=base_params.num_cooks,
                help="Total cooks distributed across stations",
                key="cooks"
            )
    
    # ========== TABLE CONFIGURATION ==========
    with st.expander("🪑 Table Configuration", expanded=True):
        st.markdown("Configure restaurant seating capacity")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            col_a, col_b, col_c, col_d = st.columns(4)
            
            with col_a:
                num_tables_2 = st.number_input("2-Seat Tables", min_value=0, value=23, key="tables_2")
            with col_b:
                num_tables_4 = st.number_input("4-Seat Tables", min_value=0, value=11, key="tables_4")
            with col_c:
                num_tables_6 = st.number_input("6-Seat Tables", min_value=0, value=6, key="tables_6")
            with col_d:
                num_tables_10 = st.number_input("10-Seat Tables", min_value=0, value=1, key="tables_10")
        
        with col2:
            table_config = [2]*num_tables_2 + [4]*num_tables_4 + [6]*num_tables_6 + [10]*num_tables_10
            total_seats = sum(table_config)
            total_tables = len(table_config)
            
            st.metric("Total Tables", total_tables)
            st.metric("Total Seats", total_seats)
            if total_tables > 0:
                st.metric("Avg Seats/Table", f"{total_seats/total_tables:.1f}")
    
    # ========== KITCHEN STATION CAPACITIES ==========
    with st.expander("🍳 Kitchen Station Capacities", expanded=False):
        st.markdown("Configure simultaneous dish capacity for each kitchen station")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            wood_grill_cap = st.number_input("Wood Grill", min_value=1, value=base_params.wood_grill_capacity, key="wg_cap")
        with col2:
            salad_cap = st.number_input("Salad Station", min_value=1, value=base_params.salad_station_capacity, key="salad_cap")
        with col3:
            sautee_cap = st.number_input("Sauté Station", min_value=1, value=base_params.sautee_station_capacity, key="sautee_cap")
        with col4:
            tortilla_cap = st.number_input("Tortilla", min_value=1, value=base_params.tortilla_station_capacity, key="tortilla_cap")
        with col5:
            guac_cap = st.number_input("Guac Station", min_value=1, value=base_params.guac_station_capacity, key="guac_cap")
    
    # ========== ARRIVAL RATE PARAMETERS ==========
    with st.expander("📊 Arrival Rate Parameters", expanded=True):
        st.markdown("Configure guest arrival pattern (NHPP model)")
        
        arrival_method = st.radio(
            "Configuration Method",
            ["Manual Entry", "Fit from CSV Data"],
            horizontal=True,
            key="arrival_method"
        )
        
        if arrival_method == "Manual Entry":
            col1, col2 = st.columns(2)
            
            with col1:
                lambda_base = st.number_input(
                    "Base Arrival Rate (λ_base)",
                    min_value=0.0,
                    max_value=1.0,
                    value=base_params.lambda_base,
                    step=0.001,
                    format="%.6f",
                    help="Minimum arrival rate in parties/minute",
                    key="lambda_base"
                )
                lambda_peak = st.number_input(
                    "Peak Multiplier (λ_peak)",
                    min_value=0.0,
                    max_value=2.0,
                    value=base_params.lambda_peak_multiplier,
                    step=0.01,
                    format="%.6f",
                    help="Additional arrival rate at peak time",
                    key="lambda_peak"
                )
            
            with col2:
                peak_time = st.number_input(
                    "Peak Time (minutes)",
                    min_value=0.0,
                    max_value=360.0,
                    value=base_params.peak_time,
                    step=5.0,
                    help="Time of peak arrivals from simulation start",
                    key="peak_time"
                )
                peak_width = st.number_input(
                    "Peak Width (minutes)",
                    min_value=10.0,
                    max_value=200.0,
                    value=base_params.peak_width,
                    step=10.0,
                    help="Width of arrival peak (Gaussian std dev)",
                    key="peak_width"
                )
        
        else:  # Fit from CSV
            st.markdown("**Upload CSV with timestamp data**")
            st.caption("Expected format: Same as OrderDetails CSV with timestamp and guest count columns")
            
            uploaded_csv = st.file_uploader(
                "Upload CSV File",
                type=["csv"],
                help="CSV file with order timestamps",
                key="arrival_csv"
            )
            
            if uploaded_csv is not None:
                col1, col2 = st.columns(2)
                
                with col1:
                    start_hour = st.number_input("Start Hour (24h)", min_value=0, max_value=23, value=17, key="start_hour")
                    day_of_week = st.selectbox(
                        "Day of Week (optional)",
                        ["All Days", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                        key="day_filter"
                    )
                    use_parties = st.checkbox("Count orders as parties (vs. summing guests)", value=True, key="use_parties")
                
                with col2:
                    if st.button("Fit Parameters", type="primary", key="fit_button"):
                        with st.spinner("Fitting NHPP parameters..."):
                            try:
                                # Save uploaded file temporarily
                                temp_path = Path(__file__).parent / "temp_arrival_data.csv"
                                with open(temp_path, "wb") as f:
                                    f.write(uploaded_csv.getvalue())
                                
                                # Fit parameters
                                day_filter = None if day_of_week == "All Days" else day_of_week
                                fitted_params = fit_nhpp_from_csv(
                                    str(temp_path),
                                    start_hour=start_hour,
                                    day_of_week=day_filter,
                                    use_parties=use_parties
                                )
                                
                                # Store in session state
                                st.session_state.fitted_params = fitted_params
                                
                                # Clean up temp file
                                temp_path.unlink()
                                
                                st.success("Parameters fitted successfully!")
                            
                            except Exception as e:
                                st.error(f"Error fitting parameters: {e}")
                                if temp_path.exists():
                                    temp_path.unlink()
                
                # Show fitted parameters if available
                if 'fitted_params' in st.session_state:
                    fitted = st.session_state.fitted_params
                    
                    st.markdown("---")
                    st.markdown(preview_fitted_parameters(fitted))
                    
                    # Visualization
                    fig = visualize_fitted_curve(fitted)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Use fitted parameters
                    lambda_base = fitted['lambda_base']
                    lambda_peak = fitted['lambda_peak_multiplier']
                    peak_time = fitted['peak_time']
                    peak_width = fitted['peak_width']
                else:
                    # Use defaults if not fitted yet
                    lambda_base = base_params.lambda_base
                    lambda_peak = base_params.lambda_peak_multiplier
                    peak_time = base_params.peak_time
                    peak_width = base_params.peak_width
            else:
                # No CSV uploaded, use defaults
                lambda_base = base_params.lambda_base
                lambda_peak = base_params.lambda_peak_multiplier
                peak_time = base_params.peak_time
                peak_width = base_params.peak_width
    
    # ========== SIMULATION DURATION & ADVANCED ==========
    with st.expander("⚙️ Simulation Duration & Advanced Settings", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            duration_minutes = st.number_input(
                "Simulation Duration (minutes)",
                min_value=1.0,
                max_value=180.0,  # Max 3 minutes = 180 minutes simulation time
                value=min(base_params.simulation_duration, 180.0),
                step=10.0,
                help="Maximum: 3 minutes (180 minutes simulation time)",
                key="duration"
            )
            
            if duration_minutes > 180.0:
                st.error("⚠️ Maximum simulation duration is 3 minutes (180 minutes simulation time)")
                duration_minutes = 180.0
            
            seed = st.number_input(
                "Random Seed",
                min_value=0,
                value=42,
                help="For reproducible results",
                key="seed"
            )
        
        with col2:
            price_per_dish = st.number_input(
                "Price per Dish ($)",
                min_value=0.0,
                value=base_params.price_per_dish,
                step=1.0,
                key="price"
            )
            expo_capacity = st.number_input(
                "Expo Capacity",
                min_value=1,
                value=base_params.expo_capacity,
                help="Number of dishes that can be quality-checked simultaneously",
                key="expo_cap"
            )
    
    # Build parameters object
    params = SingleDishParameters(
        table_config=table_config if table_config else [4]*10,  # Default if empty
        simulation_duration=duration_minutes,
        num_servers=num_servers,
        num_hosts=num_hosts,
        num_food_runners=num_food_runners,
        num_bussers=num_bussers,
        num_cooks=num_cooks,
        wood_grill_capacity=wood_grill_cap,
        salad_station_capacity=salad_cap,
        sautee_station_capacity=sautee_cap,
        tortilla_station_capacity=tortilla_cap,
        guac_station_capacity=guac_cap,
        lambda_base=lambda_base,
        lambda_peak_multiplier=lambda_peak,
        peak_time=peak_time,
        peak_width=peak_width,
        seed=int(seed),
        price_per_dish=price_per_dish,
        expo_capacity=expo_capacity,
        # Copy recipes and other settings from base
        dish_recipes=base_params.dish_recipes,
        menu_distribution=base_params.menu_distribution,
        menu_catalog=base_params.menu_catalog,
        enable_logging=True,
        enable_event_logging=True,
        min_snapshot_interval=2.0,
    )
    
    # ========== TIME ESTIMATE & RUN BUTTON ==========
    st.markdown("---")
    
    # Estimate runtime
    estimated_time = estimate_simulation_runtime(params)
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.info(f"⏱️ Estimated runtime: **{estimated_time:.1f} seconds**")
    
    with col2:
        st.metric("Sim Duration", f"{duration_minutes:.0f} min")
    
    with col3:
        st.metric("Total Staff", num_servers + num_hosts + num_food_runners + num_bussers + num_cooks)
    
    return params

