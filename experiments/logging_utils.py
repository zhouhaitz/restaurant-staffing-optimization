"""Serialization utilities for simulation logging.

This module provides helper functions to serialize simulation dataclasses
to dictionaries for JSON export, designed for GUI visualization.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Any
from enum import Enum

from models import (
    Party, Dish, DishComponent, Task, DeliveryTask, CleaningTask,
    TaskType, Station, Host, FoodRunner, Busser
)


# ==========================================================================
# EVENT TYPES
# ==========================================================================

class EventType(Enum):
    """Types of events that can be logged."""
    PARTY_ARRIVED = "party_arrived"
    PARTY_SEATED = "party_seated"
    ORDER_CREATED = "order_created"
    DISH_STARTED = "dish_started"
    DISH_COMPLETED = "dish_completed"
    DISH_EXPO_START = "dish_expo_start"
    DISH_EXPO_COMPLETE = "dish_expo_complete"
    DISH_DELIVERED = "dish_delivered"
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    PARTY_DEPARTED = "party_departed"


# ==========================================================================
# STATUS HELPERS
# ==========================================================================

def get_party_status(party: Party, current_time: float) -> str:
    """Determine the current status of a party based on timestamps.
    
    Returns one of:
    - 'waiting_for_table': In guest queue, no table assigned
    - 'being_seated': Host walking to table
    - 'deciding': At table, deciding on order
    - 'ordering': Server taking order
    - 'waiting_for_food': Order placed, waiting for kitchen
    - 'dining': Food delivered, eating
    - 'paying': Payment in progress
    - 'cleaning': Table being cleaned
    - 'departed': Left the restaurant
    """
    if party.departure_time is not None:
        return "departed"
    if party.cleanup_start is not None:
        return "cleaning"
    if party.payment_start is not None:
        return "paying"
    if party.dining_start is not None:
        return "dining"
    if party.first_delivery_time is not None:
        return "dining"
    if party.kitchen_start is not None:
        return "waiting_for_food"
    if party.ordering_start is not None:
        if party.ordering_complete is not None:
            return "waiting_for_food"
        return "ordering"
    if party.table_assigned_time is not None:
        return "deciding"
    if party.walk_start_time is not None:
        return "being_seated"
    if party.host_queue_time is not None:
        return "waiting_for_table"
    return "waiting_for_table"


def get_dish_status(dish: Dish, current_time: float) -> str:
    """Determine the current status/location of a dish.
    
    Returns one of:
    - 'queued': Waiting in station queue
    - 'cooking': Being prepared at station
    - 'expo_queue': Waiting in expo queue
    - 'expo_check': Being checked at expo
    - 'ready': Passed expo, waiting for delivery
    - 'delivered': Delivered to table
    """
    if dish.expo_complete_time is not None:
        return "delivered"
    if dish.expo_start_time is not None:
        return "expo_check"
    if dish.complete_time is not None:
        return "expo_queue"
    if dish.start_time is not None:
        return "cooking"
    return "queued"


def get_component_status(component: DishComponent, current_time: float) -> str:
    """Determine the current status of a dish component.
    
    Returns one of:
    - 'queued': Waiting in station queue
    - 'cooking': Being prepared at station
    - 'complete': Finished cooking
    """
    if component.complete_time is not None:
        return "complete"
    if component.start_time is not None:
        return "cooking"
    return "queued"


# ==========================================================================
# SERIALIZATION FUNCTIONS
# ==========================================================================

def serialize_component(component: DishComponent, current_time: float) -> Dict[str, Any]:
    """Serialize a DishComponent to a dictionary."""
    return {
        "id": component.id,
        "dish_id": component.dish_id,
        "order_id": component.order_id,
        "station_name": component.station_name,
        "prep_time_mu": component.prep_time_mu,
        "prep_time_sigma": component.prep_time_sigma,
        "queue_time": component.queue_time,
        "start_time": component.start_time,
        "complete_time": component.complete_time,
        "actual_prep_time": component.actual_prep_time,
        "status": get_component_status(component, current_time),
    }


def serialize_dish(dish: Dish, current_time: float) -> Dict[str, Any]:
    """Serialize a Dish to a dictionary with all details."""
    return {
        "id": dish.id,
        "order_id": dish.order_id,
        "dish_type": dish.dish_type,
        "queue_time": dish.queue_time,
        "start_time": dish.start_time,
        "complete_time": dish.complete_time,
        "prep_time": dish.prep_time,
        "expo_start_time": dish.expo_start_time,
        "expo_complete_time": dish.expo_complete_time,
        "price": dish.price,
        "description": dish.description,
        "status": get_dish_status(dish, current_time),
        "components": [serialize_component(c, current_time) for c in dish.components],
        "components_complete": dish.components_complete,
    }


def serialize_party(party: Party, current_time: float) -> Dict[str, Any]:
    """Serialize a Party to a dictionary with all timestamps."""
    return {
        "id": party.id,
        "arrival_time": party.arrival_time,
        "party_size": party.party_size,
        "zone_id": party.zone_id,
        "tables_assigned": party.tables_assigned.copy() if party.tables_assigned else [],
        "host_queue_time": party.host_queue_time,
        "walk_start_time": party.walk_start_time,
        "table_assigned_time": party.table_assigned_time,
        "ordering_start": party.ordering_start,
        "ordering_complete": party.ordering_complete,
        "kitchen_start": party.kitchen_start,
        "all_dishes_ready": party.all_dishes_ready,
        "delivery_start": party.delivery_start,
        "delivery_complete": party.delivery_complete,
        "dining_start": party.dining_start,
        "dining_complete": party.dining_complete,
        "payment_start": party.payment_start,
        "payment_complete": party.payment_complete,
        "cleanup_start": party.cleanup_start,
        "departure_time": party.departure_time,
        "first_delivery_time": party.first_delivery_time,
        "all_dishes_delivered": party.all_dishes_delivered,
        "dishes_delivered_count": party.dishes_delivered_count,
        "total_dishes": party.total_dishes,
        "check_total": party.check_total,
        "status": get_party_status(party, current_time),
    }


def serialize_task(task: Task) -> Dict[str, Any]:
    """Serialize a Task to a dictionary."""
    base = {
        "id": task.id,
        "task_type": task.task_type.name if isinstance(task.task_type, Enum) else str(task.task_type),
        "party_id": task.party_id,
        "zone_id": task.zone_id,
        "created_time": task.created_time,
        "started_time": task.started_time,
        "completed_time": task.completed_time,
        "assigned_to": task.assigned_to,
    }
    
    # Add subclass-specific fields
    if isinstance(task, DeliveryTask):
        base["order_id"] = task.order_id
        base["num_dishes"] = task.num_dishes
    elif isinstance(task, CleaningTask):
        base["table_ids"] = task.table_ids.copy() if task.table_ids else []
    
    return base


def serialize_station(station: Station, queue_length: int = 0, 
                      active_components: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """Serialize a Station to a dictionary."""
    return {
        "id": station.id,
        "name": station.name,
        "capacity": station.capacity,
        "busy_slots": station.busy_slots,
        "busy_time": station.busy_time,
        "dishes_prepared": station.dishes_prepared,
        "queue_length": queue_length,
        "active_components": active_components or [],
    }


def serialize_table(table_id: int, table_size: int, zone_id: int,
                    party_id: Optional[int] = None, is_available: bool = True) -> Dict[str, Any]:
    """Serialize a table's state to a dictionary."""
    return {
        "id": table_id,
        "size": table_size,
        "zone_id": zone_id,
        "party_id": party_id,
        "is_available": is_available,
    }


def serialize_order(order_id: int, party_id: int, dishes: List[Dict],
                    status: str = "pending") -> Dict[str, Any]:
    """Serialize an order to a dictionary."""
    return {
        "order_id": order_id,
        "party_id": party_id,
        "dishes": dishes,
        "total_dishes": len(dishes),
        "status": status,
    }


# ==========================================================================
# EVENT CREATION
# ==========================================================================

def create_event(event_type: EventType, timestamp: float, entity_id: int,
                 from_state: Optional[str] = None, to_state: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create an event log entry.
    
    Args:
        event_type: Type of event
        timestamp: Simulation time when event occurred
        entity_id: ID of the entity (party, dish, task) involved
        from_state: Previous state (optional)
        to_state: New state (optional)
        details: Additional event-specific details (optional)
    
    Returns:
        Dictionary ready for JSON serialization
    """
    event = {
        "event_type": event_type.value,
        "timestamp": timestamp,
        "entity_id": entity_id,
    }
    
    if from_state is not None:
        event["from_state"] = from_state
    if to_state is not None:
        event["to_state"] = to_state
    if details is not None:
        event["details"] = details
    
    return event


