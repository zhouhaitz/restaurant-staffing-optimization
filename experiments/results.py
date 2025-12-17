"""Results calculation and formatting for restaurant simulation."""
from typing import Dict, TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    from simulation import RestaurantSimulation


def calculate_results(sim: 'RestaurantSimulation') -> Dict[str, float]:
    """Calculate simulation results from simulation state.
    
    Args:
        sim: Simulation instance with state to calculate results from
    
    Returns:
        Dictionary of calculated metrics
    """
    # Finalize busy_time for cooks still active at simulation end
    for cook in sim.cooks:
        if cook.active_since is not None:
            cook.busy_time += (sim.p.simulation_duration - cook.active_since)
            cook.active_since = None
    
    # Finalize station busy times
    if hasattr(sim, 'stations'):
        for station in sim.stations.values():
            if station.active_since is not None:
                station.busy_time += (sim.p.simulation_duration - station.active_since)
                station.active_since = None
    
    # Track final queue length
    sim.queue_length_history.append((sim.p.simulation_duration, len(sim.pending_dishes)))
    
    # Categorize parties
    served = [p for p in sim.parties if p.departure_time is not None and p.departure_time <= sim.p.simulation_duration]
    parties_served = len(served)
    
    # Parties that got a table but didn't complete
    got_table = [p for p in sim.parties if p.table_assigned_time is not None]
    parties_with_table = len(got_table)
    parties_abandoned = parties_with_table - parties_served
    
    # Parties that never got a table (still waiting at simulation end)
    never_got_table = [p for p in sim.parties if p.table_assigned_time is None]
    parties_waiting_for_table = len(never_got_table)

    # Waits (for served parties only)
    waits_to_table = [max(0.0, (p.table_assigned_time or 0) - p.arrival_time) for p in served]
    waits_to_order_start = [max(0.0, (p.ordering_start or 0) - (p.table_assigned_time or 0)) for p in served]
    waits_kitchen = [max(0.0, (p.all_dishes_ready or 0) - (p.kitchen_start or 0)) for p in served]
    total_times = [max(0.0, (p.departure_time or 0) - p.arrival_time) for p in served]

    avg_wait_table = float(np.mean(waits_to_table)) if waits_to_table else 0.0
    avg_wait_order = float(np.mean(waits_to_order_start)) if waits_to_order_start else 0.0
    avg_wait_kitchen = float(np.mean(waits_kitchen)) if waits_kitchen else 0.0
    avg_total_time = float(np.mean(total_times)) if total_times else 0.0
    
    # Waits for ALL parties (including those that never got table)
    all_waits_to_table = []
    for p in sim.parties:
        if p.table_assigned_time is not None:
            all_waits_to_table.append(p.table_assigned_time - p.arrival_time)
        else:
            # Still waiting at simulation end
            all_waits_to_table.append(sim.p.simulation_duration - p.arrival_time)
    avg_wait_table_all = float(np.mean(all_waits_to_table)) if all_waits_to_table else 0.0
    max_wait_table = float(np.max(all_waits_to_table)) if all_waits_to_table else 0.0

    # Stage times (service duration, not including wait times)
    ordering_times = [max(0.0, (p.ordering_complete or 0) - (p.ordering_start or 0)) for p in served]
    delivery_times = [max(0.0, (p.delivery_complete or 0) - (p.delivery_start or 0)) for p in served]
    dining_times = [max(0.0, (p.dining_complete or 0) - (p.dining_start or 0)) for p in served]
    payment_times = [max(0.0, (p.payment_complete or 0) - (p.payment_start or 0)) for p in served]
    cleanup_times = [max(0.0, (p.departure_time or 0) - (p.cleanup_start or 0)) for p in served]
    
    avg_ordering_time = float(np.mean(ordering_times)) if ordering_times else 0.0
    avg_delivery_time = float(np.mean(delivery_times)) if delivery_times else 0.0
    avg_dining_time = float(np.mean(dining_times)) if dining_times else 0.0
    avg_payment_time = float(np.mean(payment_times)) if payment_times else 0.0
    avg_cleanup_time = float(np.mean(cleanup_times)) if cleanup_times else 0.0
    
    # Kitchen diagnostics: wait time vs service time
    # For each order, track time from kitchen_start to first dish start (wait) vs actual prep time
    kitchen_wait_times = []  # time from kitchen_start to first dish starting
    kitchen_service_times = []  # time from first dish start to last dish complete
    # Find order_id for each party
    party_to_order = {party_id: order_id for order_id, party_id in sim.order_to_party.items()}
    for p in served:
        if p.kitchen_start is not None and p.all_dishes_ready is not None:
            order_id = party_to_order.get(p.id)
            if order_id is not None:
                first_start = sim.first_dish_start_times.get(order_id)
                if first_start is not None:
                    wait_time = first_start - p.kitchen_start
                    service_time = p.all_dishes_ready - first_start
                    kitchen_wait_times.append(wait_time)
                    kitchen_service_times.append(service_time)
    avg_kitchen_wait = float(np.mean(kitchen_wait_times)) if kitchen_wait_times else 0.0
    avg_kitchen_service = float(np.mean(kitchen_service_times)) if kitchen_service_times else 0.0
    
    # Dish-level diagnostics: wait time vs prep time
    # For component-based dishes, use component times
    completed_dishes = []
    for d in sim.all_dishes:
        # A dish is complete if it has complete_time (all components done)
        if d.complete_time is not None:
            # Use first component start as dish start if not set
            if d.start_time is None and d.components:
                first_component_start = min((c.start_time for c in d.components if c.start_time is not None), default=None)
                if first_component_start is not None:
                    d.start_time = first_component_start  # Set for compatibility
            
            if d.start_time is not None:
                completed_dishes.append(d)
    
    dish_wait_times = []
    dish_prep_times = []
    for d in completed_dishes:
        if d.queue_time is not None and d.start_time is not None:
            dish_wait_times.append(d.start_time - d.queue_time)
        
        # For component-based: use max component prep time (parallel cooking)
        if d.components:
            component_prep_times = [c.actual_prep_time for c in d.components if c.actual_prep_time is not None]
            if component_prep_times:
                # Since components cook in parallel, dish prep time is max component time
                dish_prep_times.append(max(component_prep_times))
        elif d.prep_time is not None:  # Legacy fallback
            dish_prep_times.append(d.prep_time)
    
    avg_dish_wait = float(np.mean(dish_wait_times)) if dish_wait_times else 0.0
    avg_dish_prep = float(np.mean(dish_prep_times)) if dish_prep_times else 0.0
    max_dish_wait = float(np.max(dish_wait_times)) if dish_wait_times else 0.0
    
    # Dish-level kitchen time: time from order placement to dish ready for delivery
    # This measures: dish.expo_complete_time - party.kitchen_start
    dish_kitchen_times = []
    for d in sim.all_dishes:
        if d.expo_complete_time is not None:
            # Find the party for this dish's order
            party_id = sim.order_to_party.get(d.order_id)
            if party_id is not None:
                party = next((p for p in sim.parties if p.id == party_id), None)
                if party is not None and party.kitchen_start is not None:
                    dish_kitchen_time = d.expo_complete_time - party.kitchen_start
                    dish_kitchen_times.append(dish_kitchen_time)
    
    avg_dish_kitchen_time = float(np.mean(dish_kitchen_times)) if dish_kitchen_times else 0.0
    min_dish_kitchen_time = float(np.min(dish_kitchen_times)) if dish_kitchen_times else 0.0
    max_dish_kitchen_time = float(np.max(dish_kitchen_times)) if dish_kitchen_times else 0.0
    
    # Queue diagnostics
    if sim.queue_length_history:
        queue_lengths = [qlen for _, qlen in sim.queue_length_history]
        avg_queue_length = float(np.mean(queue_lengths))
        max_queue_length = float(np.max(queue_lengths))
    else:
        avg_queue_length = 0.0
        max_queue_length = 0.0
    
    # Guest count / Party size statistics
    all_party_sizes = [p.party_size for p in sim.parties]
    served_party_sizes = [p.party_size for p in served]
    avg_party_size_all = float(np.mean(all_party_sizes)) if all_party_sizes else 0.0
    avg_party_size_served = float(np.mean(served_party_sizes)) if served_party_sizes else 0.0
    min_party_size = int(np.min(all_party_sizes)) if all_party_sizes else 0
    max_party_size = int(np.max(all_party_sizes)) if all_party_sizes else 0
    total_guests_arrived = sum(all_party_sizes)
    total_guests_served = sum(served_party_sizes)
    
    # Check size statistics
    check_sizes = [p.check_total for p in served if p.check_total > 0]
    avg_check_size = float(np.mean(check_sizes)) if check_sizes else 0.0
    min_check_size = float(np.min(check_sizes)) if check_sizes else 0.0
    max_check_size = float(np.max(check_sizes)) if check_sizes else 0.0
    
    # Order size diagnostics
    served_orders = [p.total_dishes for p in served if p.total_dishes > 0]
    avg_dishes_per_order = float(np.mean(served_orders)) if served_orders else 0.0
    total_dishes_created = len(sim.all_dishes)
    total_dishes_completed = len(completed_dishes)
    dishes_in_queue_at_end = len(sim.pending_dishes)
    
    # Table allocation statistics
    tables_per_party = [len(p.tables_assigned) for p in served if p.tables_assigned]
    avg_tables_per_party = float(np.mean(tables_per_party)) if tables_per_party else 0.0
    max_tables_per_party = int(np.max(tables_per_party)) if tables_per_party else 0

    # Cook utilization: sum busy time across all stations
    # Normalized by cook_concurrency since each cook can handle multiple components
    if hasattr(sim, 'station_cook_busy_time'):
        total_cook_busy_time = sum(sim.station_cook_busy_time.values())
        # Total capacity = num_cooks × simulation_duration × cook_concurrency
        # This gives utilization in [0, 1] range even when cooks multitask
        total_cook_capacity = sim.p.num_cooks * sim.p.simulation_duration * sim.p.cook_concurrency
        avg_cook_util = total_cook_busy_time / total_cook_capacity if total_cook_capacity > 0 else 0.0
        
        # Update legacy cook.busy_time for backward compatibility
        if sim.p.num_cooks > 0:
            per_cook_busy = total_cook_busy_time / sim.p.num_cooks
            for cook in sim.cooks:
                cook.busy_time = per_cook_busy
    else:
        # Fallback to old method (shouldn't happen with new code)
        per_cook_util = [c.busy_time / sim.p.simulation_duration for c in sim.cooks]
        avg_cook_util = float(np.mean(per_cook_util)) if per_cook_util else 0.0
    
    # Server utilization
    total_server_time = sim.p.num_servers * sim.p.simulation_duration
    server_utilization = sim.server_busy_time / total_server_time if total_server_time > 0 else 0.0
    
    # Station utilization (new)
    station_utilization = {}
    station_dishes_prepared = {}
    if hasattr(sim, 'stations'):
        for name, station in sim.stations.items():
            station_time = station.capacity * sim.p.simulation_duration
            station_utilization[name] = station.busy_time / station_time if station_time > 0 else 0.0
            station_dishes_prepared[name] = station.dishes_prepared
    
    # Host utilization (new)
    host_utilization = 0.0
    if hasattr(sim, 'host_objects') and sim.host_objects:
        total_host_busy = sum(h.busy_time for h in sim.host_objects)
        total_host_time = sim.p.num_hosts * sim.p.simulation_duration
        host_utilization = total_host_busy / total_host_time if total_host_time > 0 else 0.0
    
    # Food runner utilization (new)
    food_runner_utilization = 0.0
    if hasattr(sim, 'food_runner_busy_time'):
        total_food_runner_time = sim.p.num_food_runners * sim.p.simulation_duration
        food_runner_utilization = sim.food_runner_busy_time / total_food_runner_time if total_food_runner_time > 0 else 0.0
    
    # Busser utilization (new)
    busser_utilization = 0.0
    if hasattr(sim, 'busser_busy_time'):
        total_busser_time = sim.p.num_bussers * sim.p.simulation_duration
        busser_utilization = sim.busser_busy_time / total_busser_time if total_busser_time > 0 else 0.0
    
    # Expo utilization (new)
    expo_utilization = 0.0
    if hasattr(sim, 'expo_busy_time'):
        total_expo_time = sim.p.expo_capacity * sim.p.simulation_duration
        expo_utilization = sim.expo_busy_time / total_expo_time if total_expo_time > 0 else 0.0

    # Calculate total seats from actual table configuration
    total_seats = sum(sim.table_sizes)
    total_tables = len(sim.table_sizes)
    
    # Table turnover
    table_turnover = parties_served / (total_tables * (sim.p.simulation_duration / 60.0)) if total_tables > 0 else 0.0

    # RevPASH (Revenue per Available Seat Hour)
    seat_hours = total_seats * (sim.p.simulation_duration / 60.0)
    revpash = (sim.total_revenue / seat_hours) if seat_hours > 0 else 0.0

    # Labor cost calculations
    simulation_duration_hours = sim.p.simulation_duration / 60.0
    
    # Server cost: all servers are paid for full simulation duration
    total_server_cost = sim.p.num_servers * simulation_duration_hours * sim.p.server_hourly_wage
    
    # Cook cost: all cooks are paid for full simulation duration (scheduled staff)
    total_cook_cost = sim.p.num_cooks * simulation_duration_hours * sim.p.cook_hourly_wage
    
    # Host cost (new)
    total_host_cost = sim.p.num_hosts * simulation_duration_hours * sim.p.host_hourly_wage
    
    # Food runner cost (new)
    total_food_runner_cost = sim.p.num_food_runners * simulation_duration_hours * sim.p.food_runner_hourly_wage
    
    # Busser cost (new)
    total_busser_cost = sim.p.num_bussers * simulation_duration_hours * sim.p.busser_hourly_wage
    
    # Total labor cost (updated to include all staff)
    total_labor_cost = total_server_cost + total_cook_cost + total_host_cost + total_food_runner_cost + total_busser_cost
    labor_cost_per_hour = total_labor_cost / simulation_duration_hours if simulation_duration_hours > 0 else 0.0

    # Net RevPASH (Primary KPI) = (Revenue - Labor Cost) / Seat Hours
    net_revpash = ((sim.total_revenue - total_labor_cost) / seat_hours) if seat_hours > 0 else 0.0

    result = {
        # Basic metrics
        "parties_arrived": len(sim.parties),
        "parties_served": parties_served,
        "parties_with_table": parties_with_table,
        "parties_abandoned": parties_abandoned,
        "parties_waiting_for_table": parties_waiting_for_table,
        "service_rate": parties_served / len(sim.parties) if sim.parties else 0.0,
        "total_tables": total_tables,
        "total_seats": total_seats,
        
        # Guest count / Party size statistics
        "total_guests_arrived": total_guests_arrived,
        "total_guests_served": total_guests_served,
        "avg_party_size_all": avg_party_size_all,
        "avg_party_size_served": avg_party_size_served,
        "min_party_size": min_party_size,
        "max_party_size": max_party_size,
        
        # Check size statistics
        "avg_check_size": avg_check_size,
        "min_check_size": min_check_size,
        "max_check_size": max_check_size,
        
        # Wait times (served parties)
        "avg_wait_table": avg_wait_table,
        "avg_wait_to_order": avg_wait_order,
        "avg_kitchen_time": avg_wait_kitchen,
        "avg_total_time": avg_total_time,
        
        # Wait times (ALL parties)
        "avg_wait_table_all": avg_wait_table_all,
        "max_wait_table": max_wait_table,
        
        # Stage service times
        "avg_ordering_time": avg_ordering_time,
        "avg_delivery_time": avg_delivery_time,
        "avg_dining_time": avg_dining_time,
        "avg_payment_time": avg_payment_time,
        "avg_cleanup_time": avg_cleanup_time,
        
        # Kitchen diagnostics
        "avg_kitchen_wait": avg_kitchen_wait,  # wait for first dish to start
        "avg_kitchen_service": avg_kitchen_service,  # time from first dish start to all complete
        
        # Dish-level diagnostics
        "avg_dish_wait": avg_dish_wait,
        "avg_dish_prep": avg_dish_prep,
        "max_dish_wait": max_dish_wait,
        "avg_dish_kitchen_time": avg_dish_kitchen_time,  # time from order to dish ready for delivery
        "min_dish_kitchen_time": min_dish_kitchen_time,
        "max_dish_kitchen_time": max_dish_kitchen_time,
        "total_dishes_created": total_dishes_created,
        "total_dishes_completed": total_dishes_completed,
        "dishes_in_queue_at_end": dishes_in_queue_at_end,
        "avg_dishes_per_order": avg_dishes_per_order,
        
        # Queue diagnostics
        "avg_queue_length": avg_queue_length,
        "max_queue_length": max_queue_length,
        "dish_assignments": sim.dish_assignments,
        
        # Table allocation statistics
        "avg_tables_per_party": avg_tables_per_party,
        "max_tables_per_party": max_tables_per_party,
        
        # Utilization
        "avg_cook_utilization": avg_cook_util,
        "server_utilization": server_utilization,
        "host_utilization": host_utilization,
        "food_runner_utilization": food_runner_utilization,
        "busser_utilization": busser_utilization,
        "expo_utilization": expo_utilization,
        
        # Station utilization
        **{f"{name}_utilization": util for name, util in station_utilization.items()},
        **{f"{name}_dishes_prepared": count for name, count in station_dishes_prepared.items()},
        
        # Business metrics
        "table_turnover": table_turnover,
        "revpash": revpash,
        "net_revpash": net_revpash,  # Primary KPI: (Revenue - Labor Cost) / Seat Hours
        "total_revenue": sim.total_revenue,
        
        # Labor costs
        "total_server_cost": total_server_cost,
        "total_cook_cost": total_cook_cost,
        "total_host_cost": total_host_cost,
        "total_food_runner_cost": total_food_runner_cost,
        "total_busser_cost": total_busser_cost,
        "total_labor_cost": total_labor_cost,
        "labor_cost_per_hour": labor_cost_per_hour,
    }
    return result


def format_results(results: Dict[str, float]) -> str:
    """Format simulation results in a readable, organized way."""
    lines = []
    lines.append("=" * 70)
    lines.append("RESTAURANT SIMULATION RESULTS")
    lines.append("=" * 70)
    
    # Primary KPI: Net RevPASH
    lines.append("\n🎯 PRIMARY KPI: NET REVPASH")
    lines.append("-" * 70)
    net_revpash = results.get('net_revpash', 0.0)
    lines.append(f"  Net RevPASH: ${net_revpash:.2f} per seat-hour")
    lines.append(f"  (Revenue - Labor Cost) / Seat Hours")
    revpash = results.get('revpash', 0.0)
    lines.append(f"  Gross RevPASH: ${revpash:.2f} per seat-hour")
    
    # Configuration
    lines.append("\n📊 CONFIGURATION")
    lines.append("-" * 70)
    duration = results.get('simulation_duration', 0)
    duration_str = f"{duration/60:.1f} hours" if duration > 0 else "N/A"
    total_tables = results.get('total_tables', results.get('num_tables', 'N/A'))
    total_seats = results.get('total_seats', 'N/A')
    lines.append(f"  Tables: {total_tables} (Total Seats: {total_seats})")
    lines.append(f"  Servers: {results.get('num_servers', 'N/A')}, Cooks: {results.get('num_cooks', 'N/A')}")
    lines.append(f"  Simulation Duration: {duration_str}")
    
    # Throughput & Service Rate
    lines.append("\n👥 THROUGHPUT & SERVICE RATE")
    lines.append("-" * 70)
    parties_arrived = results.get('parties_arrived', 0)
    parties_served = results.get('parties_served', 0)
    service_rate = results.get('service_rate', 0.0) * 100
    lines.append(f"  Parties Arrived: {parties_arrived}")
    lines.append(f"  Parties Served: {parties_served} ({service_rate:.1f}%)")
    lines.append(f"  Parties with Table: {results.get('parties_with_table', 0)}")
    lines.append(f"  Parties Abandoned: {results.get('parties_abandoned', 0)}")
    lines.append(f"  Parties Waiting for Table: {results.get('parties_waiting_for_table', 0)}")
    
    # Guest Count Statistics
    lines.append("\n👥 GUEST COUNT & PARTY SIZE")
    lines.append("-" * 70)
    lines.append(f"  Total Guests Arrived: {results.get('total_guests_arrived', 0)}")
    lines.append(f"  Total Guests Served: {results.get('total_guests_served', 0)}")
    lines.append(f"  Avg Party Size (All): {results.get('avg_party_size_all', 0):.2f} guests")
    lines.append(f"  Avg Party Size (Served): {results.get('avg_party_size_served', 0):.2f} guests")
    lines.append(f"  Party Size Range: {results.get('min_party_size', 0)} - {results.get('max_party_size', 0)} guests")
    
    # Revenue & Business Metrics
    lines.append("\n💰 REVENUE & BUSINESS METRICS")
    lines.append("-" * 70)
    lines.append(f"  Total Revenue: ${results.get('total_revenue', 0):,.2f}")
    lines.append(f"  Avg Check Size: ${results.get('avg_check_size', 0):.2f}")
    lines.append(f"  Check Size Range: ${results.get('min_check_size', 0):.2f} - ${results.get('max_check_size', 0):.2f}")
    lines.append(f"  RevPASH: ${results.get('revpash', 0):.2f} per seat-hour")
    lines.append(f"  Table Turnover: {results.get('table_turnover', 0):.3f} parties/table/hour")
    
    # Labor Costs
    lines.append("\n💼 LABOR COSTS")
    lines.append("-" * 70)
    lines.append(f"  Server Cost: ${results.get('total_server_cost', 0):,.2f}")
    lines.append(f"  Host Cost: ${results.get('total_host_cost', 0):,.2f}")
    lines.append(f"  Food Runner Cost: ${results.get('total_food_runner_cost', 0):,.2f}")
    lines.append(f"  Busser Cost: ${results.get('total_busser_cost', 0):,.2f}")
    lines.append(f"  Cook Cost: ${results.get('total_cook_cost', 0):,.2f}")
    lines.append(f"  Total Labor Cost: ${results.get('total_labor_cost', 0):,.2f}")
    lines.append(f"  Labor Cost per Hour: ${results.get('labor_cost_per_hour', 0):,.2f}")
    
    # Wait Times (All Parties)
    lines.append("\n⏱️  WAIT TIMES (ALL PARTIES)")
    lines.append("-" * 70)
    lines.append(f"  Avg Wait for Table: {results.get('avg_wait_table_all', 0):.2f} min")
    lines.append(f"  Max Wait for Table: {results.get('max_wait_table', 0):.2f} min")
    
    # Wait Times (Served Parties Only)
    lines.append("\n⏱️  WAIT TIMES (SERVED PARTIES ONLY)")
    lines.append("-" * 70)
    lines.append(f"  Avg Wait for Table: {results.get('avg_wait_table', 0):.2f} min")
    lines.append(f"  Avg Wait to Order: {results.get('avg_wait_to_order', 0):.2f} min")
    lines.append(f"  Avg Kitchen Time: {results.get('avg_kitchen_time', 0):.2f} min")
    lines.append(f"  Avg Total Time in System: {results.get('avg_total_time', 0):.2f} min")
    
    # Stage Service Times
    lines.append("\n🍽️  STAGE SERVICE TIMES")
    lines.append("-" * 70)
    lines.append(f"  Ordering: {results.get('avg_ordering_time', 0):.2f} min")
    lines.append(f"  Kitchen: {results.get('avg_kitchen_time', 0):.2f} min")
    lines.append(f"  Delivery: {results.get('avg_delivery_time', 0):.2f} min")
    lines.append(f"  Dining: {results.get('avg_dining_time', 0):.2f} min")
    lines.append(f"  Payment: {results.get('avg_payment_time', 0):.2f} min")
    lines.append(f"  Cleanup: {results.get('avg_cleanup_time', 0):.2f} min")
    
    # Kitchen Diagnostics
    lines.append("\n🔪 KITCHEN DIAGNOSTICS")
    lines.append("-" * 70)
    # Order-level metrics
    lines.append("  [ORDER-LEVEL]")
    lines.append(f"    Avg Order Kitchen Time: {results.get('avg_kitchen_time', 0):.2f} min")
    lines.append(f"    Avg Wait (order to first dish start): {results.get('avg_kitchen_wait', 0):.2f} min")
    lines.append(f"    Avg Kitchen Service (first to last dish): {results.get('avg_kitchen_service', 0):.2f} min")
    # Dish-level metrics
    lines.append("  [DISH-LEVEL]")
    lines.append(f"    Avg Dish Kitchen Time (order to ready): {results.get('avg_dish_kitchen_time', 0):.2f} min")
    lines.append(f"    Min Dish Kitchen Time: {results.get('min_dish_kitchen_time', 0):.2f} min")
    lines.append(f"    Max Dish Kitchen Time: {results.get('max_dish_kitchen_time', 0):.2f} min")
    lines.append(f"    Avg Dish Wait in Queue: {results.get('avg_dish_wait', 0):.2f} min")
    lines.append(f"    Avg Dish Prep Time: {results.get('avg_dish_prep', 0):.2f} min")
    lines.append(f"    Max Dish Wait: {results.get('max_dish_wait', 0):.2f} min")
    
    # Dish & Order Statistics
    lines.append("\n📦 DISH & ORDER STATISTICS")
    lines.append("-" * 70)
    lines.append(f"  Total Dishes Created: {results.get('total_dishes_created', 0)}")
    lines.append(f"  Total Dishes Completed: {results.get('total_dishes_completed', 0)}")
    lines.append(f"  Dishes in Queue at End: {results.get('dishes_in_queue_at_end', 0)}")
    lines.append(f"  Avg Dishes per Order: {results.get('avg_dishes_per_order', 0):.2f}")
    lines.append(f"  Dish Assignments: {results.get('dish_assignments', 0)}")
    
    # Queue Diagnostics
    lines.append("\n📊 QUEUE DIAGNOSTICS")
    lines.append("-" * 70)
    lines.append(f"  Avg Queue Length: {results.get('avg_queue_length', 0):.2f} dishes")
    lines.append(f"  Max Queue Length: {results.get('max_queue_length', 0)} dishes")
    
    # Table Allocation Statistics
    lines.append("\n🪑 TABLE ALLOCATION")
    lines.append("-" * 70)
    lines.append(f"  Avg Tables per Party: {results.get('avg_tables_per_party', 0):.2f}")
    lines.append(f"  Max Tables per Party: {results.get('max_tables_per_party', 0)}")
    
    # Resource Utilization
    lines.append("\n⚙️  RESOURCE UTILIZATION")
    lines.append("-" * 70)
    cook_util = results.get('avg_cook_utilization', 0) * 100
    server_util = results.get('server_utilization', 0) * 100
    host_util = results.get('host_utilization', 0) * 100
    food_runner_util = results.get('food_runner_utilization', 0) * 100
    busser_util = results.get('busser_utilization', 0) * 100
    expo_util = results.get('expo_utilization', 0) * 100
    lines.append(f"  Server Utilization: {server_util:.1f}%")
    lines.append(f"  Host Utilization: {host_util:.1f}%")
    lines.append(f"  Food Runner Utilization: {food_runner_util:.1f}%")
    lines.append(f"  Busser Utilization: {busser_util:.1f}%")
    lines.append(f"  Expo Utilization: {expo_util:.1f}%")
    lines.append(f"  Cook Utilization: {cook_util:.1f}%")
    
    # Station Utilization
    lines.append("\n🍳 STATION UTILIZATION")
    lines.append("-" * 70)
    for station in ["wood_grill", "salad_station", "sautee_station", "tortilla_station", "guac_station"]:
        util = results.get(f'{station}_utilization', 0) * 100
        prepared = results.get(f'{station}_dishes_prepared', 0)
        lines.append(f"  {station}: {util:.1f}% ({prepared} dishes)")
    
    lines.append("\n" + "=" * 70)
    return "\n".join(lines)


def print_results(results: Dict[str, float]):
    """Print formatted simulation results."""
    print(format_results(results))

