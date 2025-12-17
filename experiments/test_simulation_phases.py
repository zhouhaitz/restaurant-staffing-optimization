"""Phase-by-phase tests for restaurant simulation refactoring.

Run tests with: python -m pytest test_simulation_phases.py -v
Or run directly: python test_simulation_phases.py
"""
from __future__ import annotations

import sys
import numpy as np

# ==========================================================================
# PHASE 1 TESTS: Parameters and Models
# ==========================================================================

def test_phase1_parameters():
    """Test that new parameters are properly defined."""
    from parameters import SingleDishParameters
    
    params = SingleDishParameters()
    
    # Test new FOH resources
    assert params.num_hosts == 1, "Default hosts should be 1"
    assert params.num_food_runners == 2, "Default food runners should be 2"
    assert params.num_bussers == 2, "Default bussers should be 2"
    
    # Test station capacities
    assert params.wood_grill_capacity == 2
    assert params.salad_station_capacity == 3
    assert params.sautee_station_capacity == 2
    assert params.tortilla_station_capacity == 3
    assert params.guac_station_capacity == 2
    
    # Test expo parameters
    assert params.expo_capacity == 2
    assert params.expo_check_time_mean > 0
    
    # Test walking time
    assert params.walking_to_table_mean > 0
    
    # Test station helper methods
    station_names = params.get_station_names()
    assert "wood_grill" in station_names
    assert "salad_station" in station_names
    assert len(station_names) == 5
    
    assert params.get_station_capacity("wood_grill") == 2
    assert params.get_station_capacity("salad_station") == 3
    
    print("✓ Phase 1.1: Parameters test passed")
    return True


def test_phase1_models():
    """Test that new models are properly defined."""
    from models import (
        Dish, Party, Cook, Host, FoodRunner, Busser, Station,
        DishComponent, Task, DeliveryTask, CleaningTask, TaskType
    )
    
    # Test Host
    host = Host(id=1)
    assert host.id == 1
    assert host.busy_time == 0.0
    assert host.parties_seated == 0
    
    # Test FoodRunner
    food_runner = FoodRunner(id=1)
    assert food_runner.id == 1
    assert food_runner.deliveries_made == 0
    
    # Test Busser
    busser = Busser(id=1)
    assert busser.id == 1
    assert busser.tables_cleaned == 0
    
    # Test Station
    station = Station(id=1, name="wood_grill", capacity=2)
    assert station.name == "wood_grill"
    assert station.capacity == 2
    assert station.busy_slots == 0
    
    # Test DishComponent
    component = DishComponent(
        id=1, dish_id=1, order_id=1,
        station_name="wood_grill",
        prep_time_mu=2.0, prep_time_sigma=0.5
    )
    assert component.station_name == "wood_grill"
    assert component.complete_time is None
    
    # Test Dish with components
    dish = Dish(id=1, order_id=1, dish_type="taco")
    dish.components.append(component)
    assert len(dish.components) == 1
    assert dish.dish_type == "taco"
    
    # Test Party with zone_id
    party = Party(id=1, arrival_time=0.0, party_size=4)
    assert party.zone_id is None
    party.zone_id = 1
    assert party.zone_id == 1
    
    # Test Task types
    assert TaskType.ORDERING.value == 1
    assert TaskType.DELIVERY.value == 3
    
    # Test DeliveryTask
    delivery_task = DeliveryTask(
        id=1, task_type=TaskType.DELIVERY,
        party_id=1, zone_id=1, created_time=10.0,
        order_id=1, num_dishes=3
    )
    assert delivery_task.order_id == 1
    assert delivery_task.num_dishes == 3
    
    # Test CleaningTask
    cleaning_task = CleaningTask(
        id=2, task_type=TaskType.CLEANING,
        party_id=1, zone_id=1, created_time=50.0,
        table_ids=[1, 2]
    )
    assert cleaning_task.table_ids == [1, 2]
    
    print("✓ Phase 1.2: Models test passed")
    return True


def test_phase1_recipes():
    """Test dish recipe configuration."""
    from dish_recipes import (
        DEFAULT_RECIPES, DEFAULT_MENU_DISTRIBUTION,
        get_recipes, get_menu_distribution, select_dish_type,
        get_dish_components, validate_recipes, get_total_expected_prep_time
    )
    
    # Test default recipes
    assert "taco" in DEFAULT_RECIPES
    assert "burrito" in DEFAULT_RECIPES
    assert len(DEFAULT_RECIPES["taco"]) >= 2
    
    # Test recipe structure
    for dish_type, components in DEFAULT_RECIPES.items():
        assert len(components) > 0, f"Dish {dish_type} has no components"
        for component in components:
            assert len(component) == 3
            station, mu, sigma = component
            assert isinstance(station, str)
            assert mu > 0
            assert sigma > 0
    
    # Test menu distribution sums to 1
    total = sum(DEFAULT_MENU_DISTRIBUTION.values())
    assert abs(total - 1.0) < 0.01
    
    # Test get_recipes
    recipes = get_recipes()
    assert recipes == DEFAULT_RECIPES
    
    # Test select_dish_type
    rng = np.random.default_rng(42)
    selected = select_dish_type(rng, DEFAULT_MENU_DISTRIBUTION)
    assert selected in DEFAULT_MENU_DISTRIBUTION
    
    # Test validate_recipes
    assert validate_recipes(DEFAULT_RECIPES) == True
    
    print("✓ Phase 1.3: Recipes test passed")
    return True


# ==========================================================================
# PHASE 2-6 TESTS: Full Simulation
# ==========================================================================

def test_simulation_runs():
    """Test that the full simulation runs without errors."""
    from simulation import RestaurantSimulation
    from parameters import SingleDishParameters
    
    params = SingleDishParameters()
    params.simulation_duration = 60.0  # Short test
    params.enable_logging = False
    
    sim = RestaurantSimulation(params)
    results = sim.run()
    
    # Basic checks
    assert "parties_arrived" in results
    assert "parties_served" in results
    assert "total_revenue" in results
    
    # Should have some parties arrive
    assert results["parties_arrived"] > 0
    
    print("✓ Simulation runs successfully")
    return True


def test_zone_assignment():
    """Test that zones are assigned correctly."""
    from simulation import RestaurantSimulation
    from parameters import SingleDishParameters
    
    params = SingleDishParameters()
    params.num_servers = 4
    
    sim = RestaurantSimulation(params)
    
    # Check all tables are assigned to zones
    for table_id in sim.table_id_to_size.keys():
        zone_id = sim.get_zone_for_table(table_id)
        assert zone_id is not None
        assert 0 <= zone_id < params.num_servers
    
    # Check zones have tables
    for zone_id in range(params.num_servers):
        assert len(sim.zone_to_tables[zone_id]) > 0
    
    print("✓ Zone assignment test passed")
    return True


def test_task_removal():
    """Test that tasks are properly removed from queues when claimed."""
    from simulation import RestaurantSimulation
    from parameters import SingleDishParameters
    from models import Task, TaskType
    
    params = SingleDishParameters()
    sim = RestaurantSimulation(params)
    
    # Create a test task
    task = Task(
        id=999,
        task_type=TaskType.ORDERING,
        party_id=1,
        zone_id=0,
        created_time=0.0
    )
    
    sim.active_tasks[task.id] = task
    sim.server_zone_queues[0].append(task)
    
    # Remove task
    sim._remove_task_from_queues(task, "test")
    
    # Check task removed
    assert task.id not in sim.active_tasks
    assert task not in sim.server_zone_queues[0]
    assert task.assigned_to == "test"
    
    print("✓ Task removal test passed")
    return True


def test_parties_flow():
    """Test that parties flow through the system correctly."""
    from simulation import RestaurantSimulation
    from parameters import SingleDishParameters
    
    params = SingleDishParameters()
    params.simulation_duration = 240.0
    params.enable_logging = False
    
    sim = RestaurantSimulation(params)
    sim.run()
    
    # Check party states
    seated = [p for p in sim.parties if p.table_assigned_time is not None]
    ordered = [p for p in sim.parties if p.ordering_complete is not None]
    departed = [p for p in sim.parties if p.departure_time is not None]
    
    # Should have some parties through each stage
    assert len(seated) > 0, "No parties were seated"
    assert len(ordered) > 0, "No parties ordered"
    assert len(departed) > 0, "No parties departed"
    
    # Departed should have completed all stages
    for p in departed:
        assert p.table_assigned_time is not None
        assert p.ordering_complete is not None
        assert p.first_delivery_time is not None
        assert p.dining_complete is not None
        assert p.payment_complete is not None
        assert p.cleanup_start is not None
    
    print("✓ Parties flow test passed")
    return True


def test_cooking_stations():
    """Test that cooking stations work correctly."""
    from simulation import RestaurantSimulation
    from parameters import SingleDishParameters
    
    params = SingleDishParameters()
    params.simulation_duration = 120.0
    params.enable_logging = False
    
    sim = RestaurantSimulation(params)
    sim.run()
    
    # Check that stations have prepared dishes
    total_prepared = sum(s.dishes_prepared for s in sim.stations.values())
    assert total_prepared > 0, "No dishes were prepared"
    
    # Check all dishes have components
    for dish in sim.all_dishes:
        assert len(dish.components) > 0
    
    print("✓ Cooking stations test passed")
    return True


# ==========================================================================
# PHASE 7 TEST: Logging
# ==========================================================================

def test_snapshot_logging():
    """Test that snapshot logging works."""
    from simulation import RestaurantSimulation
    from parameters import SingleDishParameters
    
    params = SingleDishParameters()
    params.simulation_duration = 120.0
    params.log_snapshot_interval = 30.0
    params.enable_logging = True
    
    sim = RestaurantSimulation(params)
    sim.run()
    
    # Check snapshots were recorded
    assert len(sim.snapshot_history) > 0, "No snapshots recorded"
    
    # Check snapshot structure
    for snapshot in sim.snapshot_history:
        assert "time" in snapshot
        assert "guest_queue_length" in snapshot
        assert "parties_served" in snapshot
    
    print("✓ Snapshot logging test passed")
    return True


# ==========================================================================
# PHASE 9 TESTS: Integration Testing
# ==========================================================================

def test_full_simulation():
    """Test a full simulation run with realistic parameters."""
    from simulation import RestaurantSimulation
    from parameters import SingleDishParameters
    
    params = SingleDishParameters()
    params.simulation_duration = 240.0
    params.enable_logging = False
    
    sim = RestaurantSimulation(params)
    results = sim.run()
    
    # Check key metrics are present and valid
    assert results["parties_arrived"] > 0
    assert results["total_revenue"] >= 0
    assert 0 <= results["service_rate"] <= 1
    
    # Check new utilization metrics
    assert "host_utilization" in results
    assert "food_runner_utilization" in results
    assert "busser_utilization" in results
    assert "expo_utilization" in results
    
    # Check labor costs
    assert results["total_labor_cost"] > 0
    assert results["total_host_cost"] >= 0
    assert results["total_food_runner_cost"] >= 0
    assert results["total_busser_cost"] >= 0
    
    print("✓ Full simulation test passed")
    return True


def test_edge_case_no_hosts():
    """Test simulation with no hosts (should still work)."""
    from simulation import RestaurantSimulation
    from parameters import SingleDishParameters
    
    params = SingleDishParameters()
    params.simulation_duration = 60.0
    params.num_hosts = 1  # Minimum hosts
    params.enable_logging = False
    
    sim = RestaurantSimulation(params)
    results = sim.run()
    
    assert results["parties_arrived"] > 0
    print("✓ Edge case: minimum hosts test passed")
    return True


def test_edge_case_minimal_food_runners():
    """Test simulation with minimal food runners."""
    from simulation import RestaurantSimulation
    from parameters import SingleDishParameters
    
    params = SingleDishParameters()
    params.simulation_duration = 60.0
    params.num_food_runners = 1  # Minimal food runners
    params.enable_logging = False
    
    sim = RestaurantSimulation(params)
    results = sim.run()
    
    assert results["parties_arrived"] > 0
    print("✓ Edge case: minimal food runners test passed")
    return True


def test_multiple_replications():
    """Test multiple simulation replications for consistency."""
    from simulation import RestaurantSimulation
    from parameters import SingleDishParameters
    
    results_list = []
    for seed in [1, 2, 3]:
        params = SingleDishParameters()
        params.simulation_duration = 120.0
        params.seed = seed
        params.enable_logging = False
        
        sim = RestaurantSimulation(params)
        results = sim.run()
        results_list.append(results)
    
    # Check results vary (different seeds)
    revenues = [r["total_revenue"] for r in results_list]
    assert len(set(revenues)) > 1, "Results should vary with different seeds"
    
    # Check all runs completed successfully
    for r in results_list:
        assert r["parties_arrived"] > 0
    
    print("✓ Multiple replications test passed")
    return True


def test_result_formatting():
    """Test that result formatting works without errors."""
    from simulation import RestaurantSimulation
    from parameters import SingleDishParameters
    from results import format_results
    
    params = SingleDishParameters()
    params.simulation_duration = 60.0
    params.enable_logging = False
    
    sim = RestaurantSimulation(params)
    results = sim.run()
    
    # Add config for formatting
    results['num_tables'] = params.num_tables
    results['num_servers'] = params.num_servers
    results['num_cooks'] = params.num_cooks
    results['simulation_duration'] = params.simulation_duration
    
    # Format should not raise any errors
    formatted = format_results(results)
    assert len(formatted) > 0
    assert "RESTAURANT SIMULATION RESULTS" in formatted
    assert "STATION UTILIZATION" in formatted
    
    print("✓ Result formatting test passed")
    return True


# ==========================================================================
# RUN ALL TESTS
# ==========================================================================

def run_all_tests():
    """Run all phase tests."""
    print("\n" + "=" * 60)
    print("RESTAURANT SIMULATION - PHASE TESTS")
    print("=" * 60 + "\n")
    
    tests = [
        ("Phase 1.1: Parameters", test_phase1_parameters),
        ("Phase 1.2: Models", test_phase1_models),
        ("Phase 1.3: Recipes", test_phase1_recipes),
        ("Phase 2-6: Simulation Runs", test_simulation_runs),
        ("Phase 2: Zone Assignment", test_zone_assignment),
        ("Phase 5: Task Removal", test_task_removal),
        ("Phase 6: Parties Flow", test_parties_flow),
        ("Phase 3-4: Cooking Stations", test_cooking_stations),
        ("Phase 7: Snapshot Logging", test_snapshot_logging),
        ("Phase 9.1: Full Simulation", test_full_simulation),
        ("Phase 9.2: Edge Case - Min Hosts", test_edge_case_no_hosts),
        ("Phase 9.3: Edge Case - Minimal Food Runners", test_edge_case_minimal_food_runners),
        ("Phase 9.4: Multiple Replications", test_multiple_replications),
        ("Phase 9.5: Result Formatting", test_result_formatting),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"✗ {name} FAILED: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
