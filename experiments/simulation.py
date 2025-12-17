"""Main restaurant simulation engine.

This module implements a discrete-event simulation of a restaurant with:
- Guest arrival and seating (hosts, zones)
- Multi-station kitchen with component-based cooking
- Expo staging area
- Priority queue system for servers, food runners, and bussers
"""
from __future__ import annotations

import math
from collections import deque
from typing import List, Dict, Optional, Deque, Tuple, Set

import numpy as np
import simpy

import json

from models import (
    Dish, Party, Cook, Host, FoodRunner, Busser, Station,
    DishComponent, Task, DeliveryTask, CleaningTask, TaskType
)
from parameters import SingleDishParameters
import utils
from results import calculate_results
import dish_recipes
from logging_utils import (
    serialize_party, serialize_dish, serialize_task, serialize_station,
    serialize_table, serialize_order, create_event, EventType,
    get_party_status, get_dish_status
)


class RestaurantSimulation:
    """Full restaurant simulation with zones, stations, and priority queues."""
    
    def __init__(self, params: SingleDishParameters):
        self.p = params
        self.rng = np.random.default_rng(self.p.seed)
        self.env = simpy.Environment()

        # TABLE SETUP
        if self.p.table_config is None:
            self.table_sizes = [2] * 10 + [4] * 10
        else:
            self.table_sizes = self.p.table_config.copy()
        
        self.tables_by_size: Dict[int, simpy.Store] = {}
        self.table_id_to_size: Dict[int, int] = {}
        self.table_id_counter = 0
        
        for size in set(self.table_sizes):
            count = self.table_sizes.count(size)
            self.tables_by_size[size] = simpy.Store(self.env, capacity=count)
            for i in range(count):
                table_id = self.table_id_counter
                self.table_id_counter += 1
                self.table_id_to_size[table_id] = size
                self.tables_by_size[size].put(table_id)
        
        # ZONE ASSIGNMENT
        self.table_to_zone: Dict[int, int] = {}
        self.zone_to_tables: Dict[int, List[int]] = {}
        self._assign_zones()
        
        self.available_tables_by_zone: Dict[int, Set[int]] = {
            zone_id: set(tables) for zone_id, tables in self.zone_to_tables.items()
        }
        self.next_zone_index = 0
        
        # FOH RESOURCES
        # Use max(1, ...) to ensure resources always have capacity >= 1
        # This allows the simulation to run even with 0 staff (labor costs will still be $0)
        self.hosts = simpy.Resource(self.env, capacity=max(1, self.p.num_hosts))
        self.host_objects: List[Host] = [Host(id=i) for i in range(self.p.num_hosts)]
        
        self.servers = simpy.Resource(self.env, capacity=max(1, self.p.num_servers))
        self.server_busy_time: float = 0.0
        
        self.food_runners = simpy.Resource(self.env, capacity=max(1, self.p.num_food_runners))
        self.food_runner_objects: List[FoodRunner] = [FoodRunner(id=i) for i in range(self.p.num_food_runners)]
        self.food_runner_busy_time: float = 0.0
        
        self.bussers = simpy.Resource(self.env, capacity=max(1, self.p.num_bussers))
        self.busser_objects: List[Busser] = [Busser(id=i) for i in range(self.p.num_bussers)]
        self.busser_busy_time: float = 0.0
        
        # GUEST & HOST QUEUES
        self.guest_queue: Deque[Party] = deque()
        self.host_queue: Deque[Party] = deque()
        
        self.guest_queue_trigger = simpy.Event(self.env)
        self.guest_queue_waiting = False
        self.host_queue_trigger = simpy.Event(self.env)
        self.host_queue_waiting = False
        
        # TASK QUEUES
        # Use max(1, num_servers) to ensure at least 1 zone exists even with 0 servers
        num_zones = max(1, self.p.num_servers)
        self.server_zone_queues: Dict[int, Deque[Task]] = {
            zone_id: deque() for zone_id in range(num_zones)
        }
        self.food_runner_queue: Deque[DeliveryTask] = deque()
        self.busser_queue: Deque[CleaningTask] = deque()
        
        self.active_tasks: Dict[int, Task] = {}
        self.task_counter = 0
        
        self.server_queue_triggers: Dict[int, simpy.Event] = {
            zone_id: simpy.Event(self.env) for zone_id in range(num_zones)
        }
        self.server_queue_waiting: Dict[int, bool] = {
            zone_id: False for zone_id in range(num_zones)
        }
        self.food_runner_queue_trigger = simpy.Event(self.env)
        self.food_runner_queue_waiting = False
        self.busser_queue_trigger = simpy.Event(self.env)
        self.busser_queue_waiting = False
        
        # COOKING STATIONS WITH COOKS
        self.stations: Dict[str, Station] = {}
        self.station_queues: Dict[str, Deque[DishComponent]] = {}
        self.station_triggers: Dict[str, simpy.Event] = {}
        self.station_waiting: Dict[str, bool] = {}
        
        # Custom cook tracking per station
        self.station_cook_counts: Dict[str, List[int]] = {}  # List of component counts per cook
        self.station_cook_busy_time: Dict[str, float] = {}  # Total busy time for all cooks at station
        self.station_cook_available_events: Dict[str, simpy.Event] = {}  # Triggered when a cook becomes available
        
        # Distribute cooks to stations
        cook_distribution = self._distribute_cooks_to_stations()
        
        for station_name in self.p.get_station_names():
            # Assign cooks to this station
            num_cooks_at_station = cook_distribution[station_name]
            
            # Station capacity = number of cooks × cook_concurrency
            station_capacity = num_cooks_at_station * self.p.cook_concurrency
            
            self.stations[station_name] = Station(
                id=len(self.stations), 
                name=station_name, 
                capacity=station_capacity
            )
            self.station_queues[station_name] = deque()
            self.station_triggers[station_name] = simpy.Event(self.env)
            self.station_waiting[station_name] = False
            
            # Initialize cook tracking: list of component counts, one per cook
            self.station_cook_counts[station_name] = [0] * num_cooks_at_station
            self.station_cook_busy_time[station_name] = 0.0
            self.station_cook_available_events[station_name] = simpy.Event(self.env)
        
        self.component_tracking: Dict[int, Dict[int, bool]] = {}
        self.component_counter = 0
        
        # EXPO
        self.expo = simpy.Resource(self.env, capacity=self.p.expo_capacity)
        self.expo_queue: Deque[Dish] = deque()
        self.expo_trigger = simpy.Event(self.env)
        self.expo_waiting = False
        self.expo_busy_time: float = 0.0
        
        # ORDER BATCHING
        self.order_batching: Dict[int, List[Dish]] = {}
        self.order_total_dishes: Dict[int, int] = {}
        self.order_events: Dict[int, simpy.Event] = {}
        
        # DELIVERED DISHES TRACKING (for immediate single-dish delivery)
        self.order_delivered_dishes: Dict[int, Set[int]] = {}  # order_id -> set of delivered dish_ids
        
        # DISH RECIPES
        self.recipes = dish_recipes.get_recipes(self.p.dish_recipes)
        self.menu_distribution = dish_recipes.get_menu_distribution(self.p.menu_distribution, self.recipes)
        self.menu_catalog = self.p.menu_catalog  # Store menu catalog for pricing
        
        # COUNTERS & TRACKING
        self.party_counter = 0
        self.order_counter = 0
        self.dish_counter = 0
        self.parties: List[Party] = []
        self.all_dishes: List[Dish] = []
        self.total_revenue: float = 0.0
        self.order_to_party: Dict[int, int] = {}
        self.order_first_delivery_events: Dict[int, simpy.Event] = {}
        self.order_all_delivered_events: Dict[int, simpy.Event] = {}
        
        # LOGGING
        self.snapshot_history: List[Dict] = []
        self.last_snapshot_time: float = -self.p.min_snapshot_interval  # Allow first snapshot immediately
        self.event_log: List[Dict] = []  # Chronological event log
        
        # Legacy compatibility
        self.cooks: List[Cook] = [Cook(i) for i in range(self.p.num_cooks)]
        self.pending_dishes: Deque[Tuple[int, Dish]] = deque()
        self.queue_length_history: List[Tuple[float, int]] = []
        self.dish_assignments: int = 0
        self.first_dish_start_times: Dict[int, float] = {}
        self.order_to_dishes_left: Dict[int, int] = {}

    def _assign_zones(self):
        all_table_ids = list(self.table_id_to_size.keys())
        num_zones = max(1, self.p.num_servers)
        for zone_id in range(num_zones):
            self.zone_to_tables[zone_id] = []
        for i, table_id in enumerate(all_table_ids):
            zone_id = i % num_zones
            self.table_to_zone[table_id] = zone_id
            self.zone_to_tables[zone_id].append(table_id)
    
    def _distribute_cooks_to_stations(self) -> Dict[str, int]:
        """Distribute cooks across stations proportionally to capacity.
        
        Ensures minimum 1 cook per station.
        
        Returns:
            Dictionary mapping station_name -> number of cooks assigned
        """
        station_names = self.p.get_station_names()
        station_capacities = {name: self.p.get_station_capacity(name) for name in station_names}
        total_capacity = sum(station_capacities.values())
        
        if total_capacity == 0:
            # Fallback: equal distribution
            cooks_per_station = self.p.num_cooks // len(station_names)
            remainder = self.p.num_cooks % len(station_names)
            distribution = {name: max(1, cooks_per_station) for name in station_names}
            for i, name in enumerate(station_names):
                if i < remainder:
                    distribution[name] += 1
            return distribution
        
        # Proportional distribution
        distribution = {}
        total_assigned = 0
        
        # First pass: assign based on proportional share (rounded down, min 1)
        for name in station_names:
            capacity = station_capacities[name]
            proportional_share = (self.p.num_cooks * capacity) / total_capacity
            assigned = max(1, int(proportional_share))
            distribution[name] = assigned
            total_assigned += assigned
        
        # Second pass: distribute remainder to stations with highest fractional parts
        remainder = self.p.num_cooks - total_assigned
        if remainder > 0:
            fractional_parts = []
            for name in station_names:
                capacity = station_capacities[name]
                proportional_share = (self.p.num_cooks * capacity) / total_capacity
                fractional = proportional_share - int(proportional_share)
                fractional_parts.append((fractional, name))
            
            fractional_parts.sort(reverse=True)
            for i in range(min(remainder, len(fractional_parts))):
                name = fractional_parts[i][1]
                distribution[name] += 1
        
        return distribution
    
    def _has_available_cook(self, station_name: str) -> bool:
        """Check if any cook at this station can take another component."""
        cook_counts = self.station_cook_counts[station_name]
        return any(count < self.p.cook_concurrency for count in cook_counts)
    
    def _assign_component_to_cook(self, station_name: str) -> int:
        """Assign a component to an available cook.
        
        Returns:
            Index of the cook assigned (for tracking purposes)
        """
        cook_counts = self.station_cook_counts[station_name]
        # Find first cook with available capacity
        for cook_idx, count in enumerate(cook_counts):
            if count < self.p.cook_concurrency:
                cook_counts[cook_idx] += 1
                return cook_idx
        raise RuntimeError(f"No available cook at station {station_name}")
    
    def _release_component_from_cook(self, station_name: str, cook_idx: int):
        """Release a component from a cook."""
        self.station_cook_counts[station_name][cook_idx] -= 1
        # Trigger event if a cook became available
        if self._has_available_cook(station_name):
            if not self.station_cook_available_events[station_name].triggered:
                self.station_cook_available_events[station_name].succeed()
                self.station_cook_available_events[station_name] = simpy.Event(self.env)
    
    def get_zone_for_table(self, table_id: int) -> int:
        return self.table_to_zone.get(table_id, 0)
    
    def start_table_matching_dispatcher(self):
        self.env.process(self._table_matching_dispatcher())
    
    def _table_matching_dispatcher(self):
        while True:
            matched_any = False
            guests_to_remove = []
            for party in self.guest_queue:
                table_id = self._find_matching_table(party.party_size)
                if table_id is not None:
                    party.host_queue_time = self.env.now
                    party.tables_assigned = [table_id]
                    party.zone_id = self.get_zone_for_table(table_id)
                    self.available_tables_by_zone[party.zone_id].discard(table_id)
                    self.host_queue.append(party)
                    guests_to_remove.append(party)
                    matched_any = True
                    self._trigger_host_queue()
            for party in guests_to_remove:
                self.guest_queue.remove(party)
            if matched_any:
                yield self.env.timeout(0)  # Allow host to process
            else:
                self.guest_queue_waiting = True
                yield self.guest_queue_trigger
                self.guest_queue_waiting = False
                self.guest_queue_trigger = simpy.Event(self.env)
    
    def _find_matching_table(self, party_size: int) -> Optional[int]:
        num_zones = max(1, self.p.num_servers)
        for offset in range(num_zones):
            zone_id = (self.next_zone_index + offset) % num_zones
            available_in_zone = self.available_tables_by_zone.get(zone_id, set())
            best_table = None
            best_waste = float('inf')
            for table_id in available_in_zone:
                table_size = self.table_id_to_size[table_id]
                if table_size >= party_size:
                    waste = table_size - party_size
                    if waste < best_waste:
                        best_waste = waste
                        best_table = table_id
            if best_table is not None:
                self.next_zone_index = (zone_id + 1) % num_zones
                return best_table
        return None
    
    def _trigger_guest_queue(self):
        if self.guest_queue_waiting and not self.guest_queue_trigger.triggered:
            self.guest_queue_trigger.succeed()
            self.guest_queue_trigger = simpy.Event(self.env)
            self.guest_queue_waiting = False
    
    def _trigger_host_queue(self):
        if self.host_queue_waiting and not self.host_queue_trigger.triggered:
            self.host_queue_trigger.succeed()
            self.host_queue_trigger = simpy.Event(self.env)
            self.host_queue_waiting = False
    
    def start_host_dispatcher(self):
        self.env.process(self._host_dispatcher())
    
    def _host_dispatcher(self):
        while True:
            if self.host_queue:
                party = self.host_queue.popleft()
                yield self.env.process(self._seat_party(party))
            else:
                self.host_queue_waiting = True
                yield self.host_queue_trigger
                self.host_queue_waiting = False
                self.host_queue_trigger = simpy.Event(self.env)
    
    def _seat_party(self, party: Party):
        host_req = self.hosts.request()
        yield host_req
        party.walk_start_time = self.env.now
        walk_time = utils.draw_normal_positive(self.rng, self.p.walking_to_table_mean, self.p.walking_to_table_std)
        yield self.env.timeout(walk_time)
        party.table_assigned_time = self.env.now
        host_time = walk_time + self.p.host_queue_processing_time
        for host in self.host_objects:
            if host.active_since is None:
                host.busy_time += host_time
                host.parties_seated += 1
                break
        self.hosts.release(host_req)
        
        # Log PARTY_SEATED event
        self._take_event_snapshot(
            EventType.PARTY_SEATED, party.id,
            from_state="being_seated", to_state="deciding",
            details={"table_ids": party.tables_assigned, "zone_id": party.zone_id}
        )
        
        if party.table_request is not None:
            party.table_request.succeed()
    
    def start_station_dispatchers(self):
        for station_name in self.stations.keys():
            self.env.process(self._station_dispatcher(station_name))
    
    def _station_dispatcher(self, station_name: str):
        station = self.stations[station_name]
        queue = self.station_queues[station_name]
        
        while True:
            processed_any = False
            # Process components while:
            # 1. Station has capacity (busy_slots < capacity)
            # 2. Queue has components
            # 3. At least one cook has available capacity
            while (station.busy_slots < station.capacity and 
                   queue and 
                   self._has_available_cook(station_name)):
                component = queue.popleft()
                station.busy_slots += 1
                if station.active_since is None:
                    station.active_since = self.env.now
                self.env.process(self._cook_component(station, component))
                processed_any = True
            if processed_any:
                yield self.env.timeout(0)  # Allow started processes to run
            # Wait if: no queue, station at capacity, or all cooks at capacity
            if (not queue or 
                station.busy_slots >= station.capacity or 
                not self._has_available_cook(station_name)):
                self.station_waiting[station_name] = True
                # Wait for either: new component in queue OR cook becomes available
                yield self.station_triggers[station_name] | self.station_cook_available_events[station_name]
                self.station_waiting[station_name] = False
                self.station_triggers[station_name] = simpy.Event(self.env)
                # Reset cook available event if it was triggered
                if self.station_cook_available_events[station_name].triggered:
                    self.station_cook_available_events[station_name] = simpy.Event(self.env)
    
    def _cook_component(self, station: Station, component: DishComponent):
        # Assign component to an available cook
        cook_idx = self._assign_component_to_cook(station.name)
        
        component.start_time = self.env.now
        cook_start_time = self.env.now  # Track when cook started working
        
        # Set dish start_time when first component starts
        dish = next((d for d in self.all_dishes if d.id == component.dish_id), None)
        is_first_component = False
        if dish and dish.start_time is None:
            dish.start_time = self.env.now
            is_first_component = True
            # Track first dish start for legacy metrics
            if component.order_id not in self.first_dish_start_times:
                self.first_dish_start_times[component.order_id] = self.env.now
            
            # Log DISH_STARTED event (when first component starts)
            self._take_event_snapshot(
                EventType.DISH_STARTED, dish.id,
                from_state="queued", to_state="cooking",
                details={"dish_type": dish.dish_type, "order_id": dish.order_id, "station": station.name}
            )
        
        prep_time = utils.draw_lognormal(self.rng, component.prep_time_mu, component.prep_time_sigma)
        component.actual_prep_time = prep_time
        yield self.env.timeout(prep_time)
        
        # Track cook busy time for this station
        cook_elapsed_time = self.env.now - cook_start_time
        self.station_cook_busy_time[station.name] += cook_elapsed_time
        
        component.complete_time = self.env.now
        station.dishes_prepared += 1
        station.busy_slots -= 1
        
        # Release component from cook
        self._release_component_from_cook(station.name, cook_idx)
        
        if station.busy_slots == 0 and station.active_since is not None:
            station.busy_time += (self.env.now - station.active_since)
            station.active_since = None
        self._trigger_station(station.name)
        dish_id = component.dish_id
        if dish_id in self.component_tracking:
            self.component_tracking[dish_id][component.id] = True
            if all(self.component_tracking[dish_id].values()):
                self._dish_components_complete(dish_id)
    
    def _trigger_station(self, station_name: str):
        if self.station_waiting.get(station_name, False):
            trigger = self.station_triggers.get(station_name)
            if trigger and not trigger.triggered:
                trigger.succeed()
                self.station_triggers[station_name] = simpy.Event(self.env)
                self.station_waiting[station_name] = False
    
    def _dish_components_complete(self, dish_id: int):
        dish = next((d for d in self.all_dishes if d.id == dish_id), None)
        if dish is None:
            return
        
        # Calculate total prep time (max of parallel components)
        if dish.components:
            component_times = [c.actual_prep_time for c in dish.components if c.actual_prep_time is not None]
            if component_times:
                dish.prep_time = max(component_times)  # Parallel cooking = max time
        
        dish.complete_time = self.env.now
        self.expo_queue.append(dish)
        
        # Log DISH_COMPLETED event
        self._take_event_snapshot(
            EventType.DISH_COMPLETED, dish_id,
            from_state="cooking", to_state="expo_queue",
            details={"dish_type": dish.dish_type, "order_id": dish.order_id, "prep_time": dish.prep_time}
        )
        
        self._trigger_expo()
    
    def start_expo_dispatcher(self):
        self.env.process(self._expo_dispatcher())
    
    def _expo_dispatcher(self):
        while True:
            if self.expo_queue:
                dish = self.expo_queue.popleft()
                self.env.process(self._expo_check(dish))
                yield self.env.timeout(0)  # Allow process to start
            else:
                self.expo_waiting = True
                yield self.expo_trigger
                self.expo_waiting = False
                self.expo_trigger = simpy.Event(self.env)
    
    def _expo_check(self, dish: Dish):
        expo_req = self.expo.request()
        yield expo_req
        dish.expo_start_time = self.env.now
        
        # Log DISH_EXPO_START event
        self._take_event_snapshot(
            EventType.DISH_EXPO_START, dish.id,
            from_state="expo_queue", to_state="expo_check",
            details={"dish_type": dish.dish_type, "order_id": dish.order_id}
        )
        
        check_time = utils.draw_normal_positive(self.rng, self.p.expo_check_time_mean, self.p.expo_check_time_std)
        yield self.env.timeout(check_time)
        self.expo_busy_time += check_time
        dish.expo_complete_time = self.env.now
        self.expo.release(expo_req)
        
        # Log DISH_EXPO_COMPLETE event
        self._take_event_snapshot(
            EventType.DISH_EXPO_COMPLETE, dish.id,
            from_state="expo_check", to_state="ready",
            details={"dish_type": dish.dish_type, "order_id": dish.order_id}
        )
        
        order_id = dish.order_id
        if order_id not in self.order_batching:
            self.order_batching[order_id] = []
        self.order_batching[order_id].append(dish)
        
        # IMMEDIATE DELIVERY: Create delivery task for this single dish as soon as it completes expo
        self._create_delivery_task_for_dish(dish)
        
        # Set all_dishes_ready when last dish completes expo (for order-level kitchen time metric)
        total_expected = self.order_total_dishes.get(order_id, 0)
        if len(self.order_batching[order_id]) >= total_expected:
            party_id = self.order_to_party.get(order_id)
            if party_id is not None:
                party = next((p for p in self.parties if p.id == party_id), None)
                if party is not None and party.all_dishes_ready is None:
                    party.all_dishes_ready = self.env.now
    
    def _trigger_expo(self):
        if self.expo_waiting and not self.expo_trigger.triggered:
            self.expo_trigger.succeed()
            self.expo_trigger = simpy.Event(self.env)
            self.expo_waiting = False
    
    def _create_task_id(self) -> int:
        self.task_counter += 1
        return self.task_counter
    
    def _create_delivery_task_for_dish(self, dish: Dish):
        """Create a delivery task for a single dish (immediate delivery).
        
        This enables dishes to be delivered as soon as they complete expo,
        rather than waiting for all dishes in the order to be ready.
        """
        order_id = dish.order_id
        party_id = self.order_to_party.get(order_id)
        if party_id is None:
            return
        party = next((p for p in self.parties if p.id == party_id), None)
        if party is None:
            return
        
        zone_id = party.zone_id or 0
        task = DeliveryTask(
            id=self._create_task_id(),
            task_type=TaskType.DELIVERY,
            party_id=party_id,
            zone_id=zone_id,
            created_time=self.env.now,
            order_id=order_id,
            num_dishes=1,  # Single dish delivery
            dish_id=dish.id  # Track which specific dish
        )
        self.active_tasks[task.id] = task
        self.food_runner_queue.append(task)
        if zone_id in self.server_zone_queues:
            self.server_zone_queues[zone_id].append(task)
        
        # Log TASK_CREATED (DELIVERY) event
        self._take_event_snapshot(
            EventType.TASK_CREATED, task.id,
            to_state="pending",
            details={"task_type": "DELIVERY", "party_id": party_id, "order_id": order_id, 
                    "dish_id": dish.id, "num_dishes": 1}
        )
        
        self._trigger_food_runner_queue()
        self._trigger_server_zone_queue(zone_id)
    
    def _create_delivery_task(self, order_id: int):
        party_id = self.order_to_party.get(order_id)
        if party_id is None:
            return
        party = next((p for p in self.parties if p.id == party_id), None)
        if party is None:
            return
        
        # Set all_dishes_ready when all dishes complete expo (cooking done)
        # This is the correct time - not when delivery completes
        if party.all_dishes_ready is None:
            party.all_dishes_ready = self.env.now
            # Diagnostic logging for kitchen time verification
            if party.kitchen_start is not None:
                kitchen_elapsed = self.env.now - party.kitchen_start
                # Uncomment for debugging: print(f"Order {order_id}: Kitchen complete at t={self.env.now:.2f}, elapsed={kitchen_elapsed:.2f} min")
        
        zone_id = party.zone_id or 0
        num_dishes = len(self.order_batching.get(order_id, []))
        task = DeliveryTask(id=self._create_task_id(), task_type=TaskType.DELIVERY, party_id=party_id,
                           zone_id=zone_id, created_time=self.env.now, order_id=order_id, num_dishes=num_dishes)
        self.active_tasks[task.id] = task
        self.food_runner_queue.append(task)
        if zone_id in self.server_zone_queues:
            self.server_zone_queues[zone_id].append(task)
        
        # Log TASK_CREATED (DELIVERY) event
        self._take_event_snapshot(
            EventType.TASK_CREATED, task.id,
            to_state="pending",
            details={"task_type": "DELIVERY", "party_id": party_id, "order_id": order_id, "num_dishes": num_dishes}
        )
        
        self._trigger_food_runner_queue()
        self._trigger_server_zone_queue(zone_id)
    
    def _create_cleaning_task(self, party: Party):
        zone_id = party.zone_id or 0
        task = CleaningTask(id=self._create_task_id(), task_type=TaskType.CLEANING, party_id=party.id,
                           zone_id=zone_id, created_time=self.env.now, table_ids=party.tables_assigned.copy())
        self.active_tasks[task.id] = task
        self.busser_queue.append(task)
        if zone_id in self.server_zone_queues:
            self.server_zone_queues[zone_id].append(task)
        
        # Log TASK_CREATED (CLEANING) event
        self._take_event_snapshot(
            EventType.TASK_CREATED, task.id,
            to_state="pending",
            details={"task_type": "CLEANING", "party_id": party.id, "table_ids": party.tables_assigned}
        )
        
        self._trigger_busser_queue()
        self._trigger_server_zone_queue(zone_id)
    
    def _create_ordering_task(self, party: Party) -> Task:
        zone_id = party.zone_id or 0
        task = Task(id=self._create_task_id(), task_type=TaskType.ORDERING, party_id=party.id,
                   zone_id=zone_id, created_time=self.env.now)
        self.active_tasks[task.id] = task
        if zone_id in self.server_zone_queues:
            self.server_zone_queues[zone_id].append(task)
        
        # Log TASK_CREATED (ORDERING) event
        self._take_event_snapshot(
            EventType.TASK_CREATED, task.id,
            to_state="pending",
            details={"task_type": "ORDERING", "party_id": party.id}
        )
        
        self._trigger_server_zone_queue(zone_id)
        return task
    
    def _create_checkout_task(self, party: Party) -> Task:
        zone_id = party.zone_id or 0
        task = Task(id=self._create_task_id(), task_type=TaskType.CHECKOUT, party_id=party.id,
                   zone_id=zone_id, created_time=self.env.now)
        self.active_tasks[task.id] = task
        if zone_id in self.server_zone_queues:
            self.server_zone_queues[zone_id].append(task)
        
        # Log TASK_CREATED (CHECKOUT) event
        self._take_event_snapshot(
            EventType.TASK_CREATED, task.id,
            to_state="pending",
            details={"task_type": "CHECKOUT", "party_id": party.id}
        )
        
        self._trigger_server_zone_queue(zone_id)
        return task
    
    def _remove_task_from_queues(self, task: Task, claimed_by: str):
        task_id = task.id
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
        zone_id = task.zone_id
        if zone_id in self.server_zone_queues:
            # Remove in-place to preserve references
            queue = self.server_zone_queues[zone_id]
            for i, t in enumerate(list(queue)):
                if t.id == task_id:
                    del queue[i]
                    break
        if task.task_type == TaskType.DELIVERY:
            # Remove in-place
            for i, t in enumerate(list(self.food_runner_queue)):
                if t.id == task_id:
                    del self.food_runner_queue[i]
                    break
        if task.task_type == TaskType.CLEANING:
            # Remove in-place
            for i, t in enumerate(list(self.busser_queue)):
                if t.id == task_id:
                    del self.busser_queue[i]
                    break
        task.assigned_to = claimed_by
    
    def _trigger_server_zone_queue(self, zone_id: int):
        if self.server_queue_waiting.get(zone_id, False):
            trigger = self.server_queue_triggers.get(zone_id)
            if trigger and not trigger.triggered:
                trigger.succeed()
                self.server_queue_triggers[zone_id] = simpy.Event(self.env)
                self.server_queue_waiting[zone_id] = False
    
    def _trigger_food_runner_queue(self):
        if self.food_runner_queue_waiting and not self.food_runner_queue_trigger.triggered:
            self.food_runner_queue_trigger.succeed()
            self.food_runner_queue_trigger = simpy.Event(self.env)
            self.food_runner_queue_waiting = False
    
    def _trigger_busser_queue(self):
        if self.busser_queue_waiting and not self.busser_queue_trigger.triggered:
            self.busser_queue_trigger.succeed()
            self.busser_queue_trigger = simpy.Event(self.env)
            self.busser_queue_waiting = False
    
    def start_server_zone_dispatchers(self):
        num_zones = max(1, self.p.num_servers)
        for zone_id in range(num_zones):
            self.env.process(self._server_zone_dispatcher(zone_id))
    
    def _server_zone_dispatcher(self, zone_id: int):
        queue = self.server_zone_queues[zone_id]
        while True:
            task = None
            while queue:
                candidate = queue[0]
                if candidate.id in self.active_tasks:
                    task = queue.popleft()
                    break
                else:
                    queue.popleft()
            if task:
                self._remove_task_from_queues(task, f"server_zone_{zone_id}")
                # Process task and WAIT for it to complete before processing next
                yield self.env.process(self._server_process_task(zone_id, task))
            else:
                self.server_queue_waiting[zone_id] = True
                yield self.server_queue_triggers[zone_id]
                self.server_queue_waiting[zone_id] = False
                self.server_queue_triggers[zone_id] = simpy.Event(self.env)
    
    def _server_process_task(self, zone_id: int, task: Task):
        server_req = self.servers.request()
        yield server_req
        task.started_time = self.env.now
        party = next((p for p in self.parties if p.id == task.party_id), None)
        
        # Log TASK_STARTED event
        self._take_event_snapshot(
            EventType.TASK_STARTED, task.id,
            from_state="pending", to_state="in_progress",
            details={"task_type": task.task_type.name, "party_id": task.party_id, "assigned_to": f"server_zone_{zone_id}"}
        )
        
        if task.task_type == TaskType.ORDERING and party:
            party.ordering_start = self.env.now
            order_time = utils.draw_normal_positive(self.rng, self.p.ordering_taking_mean, self.p.ordering_taking_std)
            yield self.env.timeout(order_time)
            self.server_busy_time += order_time
            party.ordering_complete = self.env.now
        
        elif task.task_type == TaskType.CHECKOUT and party:
            party.payment_start = self.env.now
            payment_mean = self.p.payment_base_mean + self.p.payment_per_person_mean * party.party_size
            payment_time = utils.draw_normal_positive(self.rng, payment_mean, self.p.payment_std)
            yield self.env.timeout(payment_time)
            self.server_busy_time += payment_time
            party.payment_complete = self.env.now
        
        elif task.task_type == TaskType.DELIVERY and party:
            delivery_task = task
            order_id = delivery_task.order_id
            
            # Track first delivery time and trigger first_delivery_event
            if party.first_delivery_time is None:
                party.first_delivery_time = self.env.now
                party.delivery_start = self.env.now
                if order_id in self.order_first_delivery_events:
                    ev = self.order_first_delivery_events[order_id]
                    if not ev.triggered:
                        ev.succeed()
            
            # Simulate delivery time
            delivery_time = utils.draw_normal_positive(self.rng, self.p.delivery_base_mean, self.p.delivery_std)
            yield self.env.timeout(delivery_time)
            self.server_busy_time += delivery_time
            
            # Track delivered dishes
            if order_id not in self.order_delivered_dishes:
                self.order_delivered_dishes[order_id] = set()
            if delivery_task.dish_id is not None:
                self.order_delivered_dishes[order_id].add(delivery_task.dish_id)
            party.dishes_delivered_count += delivery_task.num_dishes
            
            # Check if all dishes have been delivered
            if party.dishes_delivered_count >= party.total_dishes:
                party.all_dishes_delivered = self.env.now
                party.delivery_complete = self.env.now
                if order_id in self.order_all_delivered_events:
                    ev = self.order_all_delivered_events[order_id]
                    if not ev.triggered:
                        ev.succeed()
        
        elif task.task_type == TaskType.CLEANING and party:
            cleaning_task = task
            party.cleanup_start = self.env.now
            cleanup_mean = self.p.cleanup_base_mean + self.p.cleanup_per_person_mean * party.party_size
            cleanup_time = utils.draw_normal_positive(self.rng, cleanup_mean, self.p.cleanup_std)
            yield self.env.timeout(cleanup_time)
            self.server_busy_time += cleanup_time
            self._release_tables(cleaning_task.table_ids, party.zone_id)
        
        task.completed_time = self.env.now
        
        # Log TASK_COMPLETED event
        self._take_event_snapshot(
            EventType.TASK_COMPLETED, task.id,
            from_state="in_progress", to_state="completed",
            details={"task_type": task.task_type.name, "party_id": task.party_id}
        )
        
        self.servers.release(server_req)
    
    def start_food_runner_dispatcher(self):
        self.env.process(self._food_runner_dispatcher())
    
    def _food_runner_dispatcher(self):
        while True:
            task = None
            while self.food_runner_queue:
                candidate = self.food_runner_queue[0]
                if candidate.id in self.active_tasks:
                    task = self.food_runner_queue.popleft()
                    break
                else:
                    self.food_runner_queue.popleft()
            if task:
                self._remove_task_from_queues(task, "food_runner")
                yield self.env.process(self._food_runner_process_task(task))
            else:
                self.food_runner_queue_waiting = True
                yield self.food_runner_queue_trigger
                self.food_runner_queue_waiting = False
                self.food_runner_queue_trigger = simpy.Event(self.env)
    
    def _food_runner_process_task(self, task: DeliveryTask):
        runner_req = self.food_runners.request()
        yield runner_req
        task.started_time = self.env.now
        
        # Log TASK_STARTED event
        self._take_event_snapshot(
            EventType.TASK_STARTED, task.id,
            from_state="pending", to_state="in_progress",
            details={"task_type": "DELIVERY", "party_id": task.party_id, "assigned_to": "food_runner"}
        )
        
        party = next((p for p in self.parties if p.id == task.party_id), None)
        order_id = task.order_id
        if party:
            # Track first delivery time and trigger first_delivery_event
            if party.first_delivery_time is None:
                party.first_delivery_time = self.env.now
                party.delivery_start = self.env.now
                if order_id in self.order_first_delivery_events:
                    ev = self.order_first_delivery_events[order_id]
                    if not ev.triggered:
                        ev.succeed()
            
            # Simulate delivery time
            delivery_time = utils.draw_normal_positive(self.rng, self.p.delivery_base_mean, self.p.delivery_std)
            yield self.env.timeout(delivery_time)
            self.food_runner_busy_time += delivery_time
            
            # Track delivered dishes
            if order_id not in self.order_delivered_dishes:
                self.order_delivered_dishes[order_id] = set()
            if task.dish_id is not None:
                self.order_delivered_dishes[order_id].add(task.dish_id)
            party.dishes_delivered_count += task.num_dishes
            
            # Check if all dishes have been delivered
            if party.dishes_delivered_count >= party.total_dishes:
                party.all_dishes_delivered = self.env.now
                party.delivery_complete = self.env.now
                if order_id in self.order_all_delivered_events:
                    ev = self.order_all_delivered_events[order_id]
                    if not ev.triggered:
                        ev.succeed()
        task.completed_time = self.env.now
        
        # Log TASK_COMPLETED event
        self._take_event_snapshot(
            EventType.TASK_COMPLETED, task.id,
            from_state="in_progress", to_state="completed",
            details={"task_type": "DELIVERY", "party_id": task.party_id, "num_dishes": task.num_dishes}
        )
        
        # Log DISH_DELIVERED event for all dishes in this delivery
        if party and task.order_id in self.order_batching:
            for dish in self.order_batching[task.order_id]:
                self._log_event(
                    EventType.DISH_DELIVERED, dish.id,
                    from_state="ready", to_state="delivered",
                    details={"dish_type": dish.dish_type, "order_id": dish.order_id, "party_id": task.party_id}
                )
        
        for runner in self.food_runner_objects:
            runner.deliveries_made += 1
            break
        self.food_runners.release(runner_req)
    
    def start_busser_dispatcher(self):
        self.env.process(self._busser_dispatcher())
    
    def _busser_dispatcher(self):
        while True:
            task = None
            while self.busser_queue:
                candidate = self.busser_queue[0]
                if candidate.id in self.active_tasks:
                    task = self.busser_queue.popleft()
                    break
                else:
                    self.busser_queue.popleft()
            if task:
                self._remove_task_from_queues(task, "busser")
                yield self.env.process(self._busser_process_task(task))
            else:
                self.busser_queue_waiting = True
                yield self.busser_queue_trigger
                self.busser_queue_waiting = False
                self.busser_queue_trigger = simpy.Event(self.env)
    
    def _busser_process_task(self, task: CleaningTask):
        busser_req = self.bussers.request()
        yield busser_req
        task.started_time = self.env.now
        
        # Log TASK_STARTED event
        self._take_event_snapshot(
            EventType.TASK_STARTED, task.id,
            from_state="pending", to_state="in_progress",
            details={"task_type": "CLEANING", "party_id": task.party_id, "assigned_to": "busser"}
        )
        
        party = next((p for p in self.parties if p.id == task.party_id), None)
        if party:
            party.cleanup_start = self.env.now
            cleanup_mean = self.p.cleanup_base_mean + self.p.cleanup_per_person_mean * party.party_size
            cleanup_time = utils.draw_normal_positive(self.rng, cleanup_mean, self.p.cleanup_std)
            yield self.env.timeout(cleanup_time)
            self.busser_busy_time += cleanup_time
            self._release_tables(task.table_ids, party.zone_id)
        task.completed_time = self.env.now
        
        # Log TASK_COMPLETED event
        self._take_event_snapshot(
            EventType.TASK_COMPLETED, task.id,
            from_state="in_progress", to_state="completed",
            details={"task_type": "CLEANING", "party_id": task.party_id, "table_ids": task.table_ids}
        )
        
        for busser in self.busser_objects:
            busser.tables_cleaned += 1
            break
        self.bussers.release(busser_req)
    
    def _release_tables(self, table_ids: List[int], zone_id: Optional[int]):
        for table_id in table_ids:
            size = self.table_id_to_size[table_id]
            self.tables_by_size[size].put(table_id)
            if zone_id is not None and zone_id in self.available_tables_by_zone:
                self.available_tables_by_zone[zone_id].add(table_id)
        self._trigger_guest_queue()
    
    def generate_nhpp_arrivals(self) -> List[float]:
        t = 0.0
        arrivals = []
        lambda_max = self.p.lambda_base + self.p.lambda_peak_multiplier
        while t < self.p.simulation_duration:
            t += self.rng.exponential(1 / lambda_max)
            if t < self.p.simulation_duration:
                if self.rng.random() < self.p.lambda_t(t) / lambda_max:
                    arrivals.append(t)
        return arrivals

    def party_process(self, arrival_time: float):
        self.party_counter += 1
        party = Party(id=self.party_counter, arrival_time=arrival_time, party_size=utils.generate_party_size(self.rng))
        self.parties.append(party)
        party.table_request = self.env.event()
        self.guest_queue.append(party)
        
        # Log PARTY_ARRIVED event
        self._take_event_snapshot(
            EventType.PARTY_ARRIVED, party.id,
            to_state="waiting_for_table",
            details={"party_size": party.party_size, "arrival_time": arrival_time}
        )
        
        self._trigger_guest_queue()
        yield party.table_request
        
        decision_mean = self.p.decision_base_mean + self.p.decision_per_person_mean * party.party_size
        decision_time = utils.draw_normal_positive(self.rng, decision_mean, self.p.decision_std)
        yield self.env.timeout(decision_time)
        
        self._create_ordering_task(party)
        yield self.env.timeout(0)
        while party.ordering_complete is None:
            yield self.env.timeout(0.1)
        
        self.order_counter += 1
        order_id = self.order_counter
        self.order_to_party[order_id] = party.id
        total_dishes = self._generate_order_dishes(party.party_size)
        party.total_dishes = total_dishes
        party.kitchen_start = self.env.now
        self.order_total_dishes[order_id] = total_dishes
        self.order_batching[order_id] = []
        
        # Log ORDER_CREATED event
        self._take_event_snapshot(
            EventType.ORDER_CREATED, order_id,
            to_state="pending",
            details={"party_id": party.id, "total_dishes": total_dishes}
        )
        
        first_delivery_event = self.env.event()
        all_delivered_event = self.env.event()
        self.order_first_delivery_events[order_id] = first_delivery_event
        self.order_all_delivered_events[order_id] = all_delivered_event

        # Create dishes first (they will have prices assigned)
        order_dishes_list = []
        for _ in range(total_dishes):
            dish = self._create_dish_with_components(order_id)
            order_dishes_list.append(dish)
        
        # Calculate check_total from actual dish prices
        dish_total = sum(d.price or self.p.price_per_dish for d in order_dishes_list)
        party.check_total = dish_total * (1 + self.p.drink_supplement)
        
        # Wait for ALL dishes to be delivered before starting dining
        # (first_delivery_event is still tracked for metrics, but dining doesn't start until all arrive)
        yield all_delivered_event
        
        # Start dining timer when all dishes have been delivered
        party.dining_start = party.all_dishes_delivered
        dining_mu_scaled = self.p.dining_base_mu + self.p.dining_per_person_mu * party.party_size
        dining_time = utils.draw_lognormal(self.rng, dining_mu_scaled, self.p.dining_sigma)
        yield self.env.timeout(dining_time)
        party.dining_complete = self.env.now
        
        # Note: party.all_dishes_ready is set in _expo_check() when all dishes complete expo
        # This is different from all_dishes_delivered which is when all dishes reach the table
        
        self._create_checkout_task(party)
        while party.payment_complete is None:
            yield self.env.timeout(0.1)
        
        self._create_cleaning_task(party)
        while party.cleanup_start is None:
            yield self.env.timeout(0.1)
        
        cleanup_mean = self.p.cleanup_base_mean + self.p.cleanup_per_person_mean * party.party_size
        yield self.env.timeout(cleanup_mean + 1.0)
        party.departure_time = self.env.now
        self.total_revenue += party.check_total
        
        # Log PARTY_DEPARTED event
        self._take_event_snapshot(
            EventType.PARTY_DEPARTED, party.id,
            from_state="cleaning", to_state="departed",
            details={"party_size": party.party_size, "check_total": party.check_total, "total_time": party.departure_time - party.arrival_time}
        )

    def _generate_order_dishes(self, party_size: int) -> int:
        per_person = float(self.rng.uniform(self.p.avg_dishes_per_person_low, self.p.avg_dishes_per_person_high))
        total = int(math.ceil(party_size * per_person))
        return max(1, total)
    
    def _create_dish_with_components(self, order_id: int):
        self.dish_counter += 1
        dish_id = self.dish_counter
        dish_type = dish_recipes.select_dish_type(self.rng, self.menu_distribution)
        
        # Get price and description from menu_catalog if available
        price = None
        description = None
        if self.menu_catalog and dish_type in self.menu_catalog:
            catalog_entry = self.menu_catalog[dish_type]
            price = float(catalog_entry.get('price', self.p.price_per_dish))
            description = catalog_entry.get('description')
        else:
            # Fallback to default price if no catalog
            price = self.p.price_per_dish
        
        dish = Dish(
            id=dish_id, 
            order_id=order_id, 
            dish_type=dish_type, 
            queue_time=self.env.now,
            price=price,
            description=description
        )
        self.all_dishes.append(dish)
        recipe_components = dish_recipes.get_dish_components(dish_type, self.recipes)
        self.component_tracking[dish_id] = {}
        for station_name, prep_mu, prep_sigma in recipe_components:
            self.component_counter += 1
            component = DishComponent(id=self.component_counter, dish_id=dish_id, order_id=order_id,
                                      station_name=station_name, prep_time_mu=prep_mu, prep_time_sigma=prep_sigma,
                                      queue_time=self.env.now)
            dish.components.append(component)
            self.component_tracking[dish_id][component.id] = False
            if station_name in self.station_queues:
                self.station_queues[station_name].append(component)
                self._trigger_station(station_name)
        self.order_to_dishes_left[order_id] = self.order_to_dishes_left.get(order_id, 0) + 1
        
        return dish
    
    def start_snapshot_logger(self):
        """Start the snapshot logging system.
        
        In event-driven mode (default), snapshots are taken at key events.
        If periodic backup is enabled, also starts a periodic backup process.
        """
        if self.p.enable_logging and self.p.enable_periodic_backup:
            self.env.process(self._periodic_backup_logger())
    
    def print_snapshot(self):
        print(f"\n=== Simulation Snapshot at t={self.env.now:.1f} ===")
        print(f"Guest Queue: {len(self.guest_queue)}")
        print(f"Host Queue: {len(self.host_queue)}")
        print(f"Parties in system: {len([p for p in self.parties if p.departure_time is None])}")
        print(f"Parties served: {len([p for p in self.parties if p.departure_time is not None])}")
        for station_name in self.stations:
            q_len = len(self.station_queues[station_name])
            busy = self.stations[station_name].busy_slots
            print(f"  {station_name}: queue={q_len}, busy={busy}")
        print(f"Expo Queue: {len(self.expo_queue)}")
        print(f"Revenue: ${self.total_revenue:.2f}")
    
    # ==========================================================================
    # EVENT-DRIVEN LOGGING SYSTEM
    # ==========================================================================
    
    def _should_take_snapshot(self) -> bool:
        """Check if enough time has passed since last snapshot."""
        if not self.p.enable_logging:
            return False
        return self.env.now - self.last_snapshot_time >= self.p.min_snapshot_interval
    
    def _log_event(self, event_type: EventType, entity_id: int,
                   from_state: Optional[str] = None, to_state: Optional[str] = None,
                   details: Optional[Dict] = None):
        """Log a state transition event."""
        if not self.p.enable_logging or not self.p.enable_event_logging:
            return
        event = create_event(event_type, self.env.now, entity_id, from_state, to_state, details)
        self.event_log.append(event)
    
    def _capture_full_snapshot(self) -> Dict:
        """Capture complete system state at current time.
        
        Returns a dictionary with:
        - Backward compatibility fields (time, queue lengths, counts)
        - New detailed fields (parties, dishes, orders, tasks, tables, stations)
        """
        current_time = self.env.now
        
        # Build table occupancy map
        table_to_party: Dict[int, Optional[int]] = {}
        for party in self.parties:
            if party.departure_time is None and party.tables_assigned:
                for table_id in party.tables_assigned:
                    table_to_party[table_id] = party.id
        
        # Build order information
        orders = []
        for order_id, party_id in self.order_to_party.items():
            order_dishes = [serialize_dish(d, current_time) for d in self.all_dishes if d.order_id == order_id]
            # Determine order status
            if order_dishes:
                all_delivered = all(d["status"] == "delivered" for d in order_dishes)
                any_cooking = any(d["status"] == "cooking" for d in order_dishes)
                any_queued = any(d["status"] == "queued" for d in order_dishes)
                if all_delivered:
                    status = "delivered"
                elif any_cooking:
                    status = "cooking"
                elif any_queued:
                    status = "pending"
                else:
                    status = "expo"
            else:
                status = "pending"
            orders.append(serialize_order(order_id, party_id, order_dishes, status))
        
        # Build tables list
        tables = []
        for table_id, table_size in self.table_id_to_size.items():
            zone_id = self.table_to_zone.get(table_id, 0)
            party_id = table_to_party.get(table_id)
            is_available = table_id in self.available_tables_by_zone.get(zone_id, set())
            tables.append(serialize_table(table_id, table_size, zone_id, party_id, is_available))
        
        # Build detailed station info
        stations_detail = []
        for station_name, station in self.stations.items():
            queue_components = []
            for component in self.station_queues.get(station_name, []):
                queue_components.append({
                    "component_id": component.id,
                    "dish_id": component.dish_id,
                    "order_id": component.order_id,
                })
            stations_detail.append(serialize_station(
                station,
                queue_length=len(self.station_queues.get(station_name, [])),
                active_components=queue_components[:5]  # Limit to first 5 for readability
            ))
        
        # Build snapshot with backward compatibility fields first
        snapshot = {
            # === BACKWARD COMPATIBILITY FIELDS (required for existing tests) ===
            "time": current_time,
            "guest_queue_length": len(self.guest_queue),
            "host_queue_length": len(self.host_queue),
            "parties_in_system": len([p for p in self.parties if p.departure_time is None]),
            "parties_served": len([p for p in self.parties if p.departure_time is not None]),
            "total_revenue": self.total_revenue,
            "expo_queue_length": len(self.expo_queue),
            "food_runner_queue": len(self.food_runner_queue),
            "busser_queue": len(self.busser_queue),
        }
        
        # Add station queue/busy fields (backward compat)
        for station_name in self.stations:
            snapshot[f"{station_name}_queue"] = len(self.station_queues[station_name])
            snapshot[f"{station_name}_busy"] = self.stations[station_name].busy_slots
        
        # Add server zone queue fields (backward compat)
        for zone_id in self.server_zone_queues:
            snapshot[f"server_zone_{zone_id}_queue"] = len(self.server_zone_queues[zone_id])
        
        # === NEW DETAILED FIELDS ===
        snapshot["parties"] = [serialize_party(p, current_time) for p in self.parties]
        snapshot["dishes"] = [serialize_dish(d, current_time) for d in self.all_dishes]
        snapshot["orders"] = orders
        snapshot["tasks"] = [serialize_task(t) for t in self.active_tasks.values()]
        snapshot["tables"] = tables
        snapshot["stations"] = stations_detail
        
        return snapshot
    
    def _take_event_snapshot(self, event_type: EventType, entity_id: int,
                             from_state: Optional[str] = None, to_state: Optional[str] = None,
                             details: Optional[Dict] = None, force: bool = False):
        """Take a snapshot if throttle allows, and log the event.
        
        Args:
            event_type: Type of event that triggered this
            entity_id: ID of the entity involved
            from_state: Previous state (optional)
            to_state: New state (optional)
            details: Additional event details (optional)
            force: If True, take snapshot regardless of throttle
        """
        if not self.p.enable_logging:
            return
        
        # Always log the event
        self._log_event(event_type, entity_id, from_state, to_state, details)
        
        # Take snapshot if throttle allows or forced
        if force or self._should_take_snapshot():
            snapshot = self._capture_full_snapshot()
            self.snapshot_history.append(snapshot)
            self.last_snapshot_time = self.env.now
    
    def _periodic_backup_logger(self):
        """Optional periodic backup snapshots (runs alongside event-driven)."""
        while True:
            yield self.env.timeout(self.p.periodic_backup_interval)
            if self.p.enable_logging:
                snapshot = self._capture_full_snapshot()
                self.snapshot_history.append(snapshot)
                self.last_snapshot_time = self.env.now
    
    # ==========================================================================
    # JSON EXPORT METHODS
    # ==========================================================================
    
    def export_snapshots_to_json(self, filepath: str):
        """Export snapshot history to a JSON file."""
        data = {
            "metadata": {
                "simulation_duration": self.p.simulation_duration,
                "num_parties": len(self.parties),
                "num_dishes": len(self.all_dishes),
                "total_revenue": self.total_revenue,
                "num_snapshots": len(self.snapshot_history),
            },
            "snapshots": self.snapshot_history,
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def export_events_to_json(self, filepath: str):
        """Export event log to a JSON file."""
        data = {
            "metadata": {
                "simulation_duration": self.p.simulation_duration,
                "num_events": len(self.event_log),
            },
            "events": self.event_log,
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def export_all_logs_to_json(self, filepath: str):
        """Export both snapshots and events to a single JSON file."""
        data = {
            "metadata": {
                "simulation_duration": self.p.simulation_duration,
                "num_parties": len(self.parties),
                "num_dishes": len(self.all_dishes),
                "total_revenue": self.total_revenue,
                "num_snapshots": len(self.snapshot_history),
                "num_events": len(self.event_log),
            },
            "snapshots": self.snapshot_history,
            "events": self.event_log,
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def run(self) -> Dict[str, float]:
        self.start_table_matching_dispatcher()
        self.start_host_dispatcher()
        self.start_station_dispatchers()
        self.start_expo_dispatcher()
        self.start_server_zone_dispatchers()
        self.start_food_runner_dispatcher()
        self.start_busser_dispatcher()
        self.start_snapshot_logger()
        arrivals = self.generate_nhpp_arrivals()
        for at in arrivals:
            self.env.process(self._schedule_party(at))
        self.env.run(until=self.p.simulation_duration)
        return self._results()

    def _schedule_party(self, arrival_time: float):
        yield self.env.timeout(arrival_time - self.env.now)
        yield self.env.process(self.party_process(arrival_time))

    def _results(self) -> Dict[str, float]:
        return calculate_results(self)


class SingleDishRestaurantSim(RestaurantSimulation):
    """Legacy compatibility wrapper."""
    pass
