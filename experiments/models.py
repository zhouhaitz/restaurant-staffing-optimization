"""Data models for restaurant simulation entities."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum, auto

import simpy


# ==========================================================================
# TASK TYPES
# ==========================================================================

class TaskType(Enum):
    """Types of tasks that can be assigned to staff."""
    ORDERING = auto()      # Server-only: take order from party
    CHECKOUT = auto()      # Server-only: process payment
    DELIVERY = auto()      # Server or Food Runner: deliver food
    CLEANING = auto()      # Server or Busser: clean table


@dataclass
class Task:
    """Base class for tasks in queue system."""
    id: int
    task_type: TaskType
    party_id: int
    zone_id: int
    created_time: float
    started_time: Optional[float] = None
    completed_time: Optional[float] = None
    assigned_to: Optional[str] = None  # e.g., "server_1", "food_runner_2"


@dataclass
class DeliveryTask(Task):
    """Task for delivering food to a table."""
    order_id: int = 0
    num_dishes: int = 0
    dish_id: Optional[int] = None  # For single-dish delivery tracking


@dataclass
class CleaningTask(Task):
    """Task for cleaning a table after party leaves."""
    table_ids: List[int] = field(default_factory=list)


# ==========================================================================
# DISH COMPONENTS
# ==========================================================================

@dataclass
class DishComponent:
    """A single component of a dish that needs to be prepared at a station."""
    id: int
    dish_id: int
    order_id: int
    station_name: str  # e.g., "wood_grill", "salad_station"
    prep_time_mu: float  # lognormal mu parameter
    prep_time_sigma: float  # lognormal sigma parameter
    queue_time: Optional[float] = None  # when component enters station queue
    start_time: Optional[float] = None  # when station starts cooking
    complete_time: Optional[float] = None  # when component is done
    actual_prep_time: Optional[float] = None


@dataclass
class Dish:
    """A dish in an order, potentially composed of multiple components."""
    id: int
    order_id: int
    dish_type: str = "default"  # e.g., "taco", "burrito", "salad"
    queue_time: Optional[float] = None  # when dish enters queue
    start_time: Optional[float] = None  # when first component starts (legacy: when cook starts)
    complete_time: Optional[float] = None  # when all components complete
    prep_time: Optional[float] = None  # actual prep time (with slowdown) - legacy
    expo_start_time: Optional[float] = None  # when dish enters expo
    expo_complete_time: Optional[float] = None  # when dish passes expo check
    components: List[DishComponent] = field(default_factory=list)
    components_complete: int = 0  # count of completed components
    price: Optional[float] = None  # dish-specific price from menu_catalog
    description: Optional[str] = None  # dish description from menu_catalog


# ==========================================================================
# PARTY
# ==========================================================================

@dataclass
class Party:
    """A party (group of guests) visiting the restaurant."""
    id: int
    arrival_time: float
    party_size: int
    zone_id: Optional[int] = None  # which zone the party's table is in
    table_request: Optional[simpy.events.Event] = None
    table_assigned_time: Optional[float] = None
    tables_assigned: List[int] = field(default_factory=list)  # list of table IDs assigned to this party
    host_queue_time: Optional[float] = None  # when party was added to host queue
    walk_start_time: Optional[float] = None  # when host started walking party to table
    ordering_start: Optional[float] = None
    ordering_complete: Optional[float] = None
    kitchen_start: Optional[float] = None
    all_dishes_ready: Optional[float] = None
    delivery_start: Optional[float] = None
    delivery_complete: Optional[float] = None
    dining_start: Optional[float] = None
    dining_complete: Optional[float] = None
    payment_start: Optional[float] = None
    payment_complete: Optional[float] = None
    cleanup_start: Optional[float] = None
    departure_time: Optional[float] = None
    first_delivery_time: Optional[float] = None  # when first dish is delivered
    all_dishes_delivered: Optional[float] = None  # when all dishes are delivered
    dishes_delivered_count: int = 0  # track number of dishes delivered
    total_dishes: int = 0
    check_total: float = 0.0


# ==========================================================================
# STAFF RESOURCES
# ==========================================================================

@dataclass
class Host:
    """Host staff member who seats guests."""
    id: int
    busy_time: float = 0.0  # total time spent seating guests
    active_since: Optional[float] = None
    parties_seated: int = 0


@dataclass
class FoodRunner:
    """Food runner staff member who delivers food."""
    id: int
    busy_time: float = 0.0  # total time spent delivering
    active_since: Optional[float] = None
    deliveries_made: int = 0


@dataclass
class Busser:
    """Busser staff member who cleans tables."""
    id: int
    busy_time: float = 0.0  # total time spent cleaning
    active_since: Optional[float] = None
    tables_cleaned: int = 0


@dataclass
class Cook:
    """Cook staff member (legacy, for backward compatibility)."""
    id: int
    busy_slots: int = 0  # 0..cook_concurrency
    busy_time: float = 0.0  # wall-clock active time
    active_since: Optional[float] = None


# ==========================================================================
# COOKING STATIONS
# ==========================================================================

@dataclass
class Station:
    """A cooking station in the kitchen."""
    id: int
    name: str  # e.g., "wood_grill", "salad_station"
    capacity: int  # max concurrent dishes
    busy_slots: int = 0  # current number of dishes being prepared
    busy_time: float = 0.0  # total time station was active
    active_since: Optional[float] = None
    dishes_prepared: int = 0

