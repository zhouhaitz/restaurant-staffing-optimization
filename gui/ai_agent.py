"""AI Agent for simulation explainability using OpenAI Function Calling.

This module provides an AI agent that can:
- Answer questions about simulation results
- Explore data using function tools
- Provide insights and explanations
"""

import os
import json
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import sys

# Add gui directory to path for imports
gui_path = Path(__file__).parent
sys.path.insert(0, str(gui_path))

from dotenv import load_dotenv
import pandas as pd
import numpy as np

# Load environment variables
load_dotenv()

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # Will raise error when trying to use

from data_loader import get_log_summary, extract_parties, extract_dishes
from metrics_calculator import (
    calculate_revpash,
    calculate_table_utilization,
    calculate_staff_utilization,
    calculate_station_utilization,
    calculate_queue_metrics,
    calculate_throughput_metrics,
    calculate_service_times,
    calculate_summary_statistics,
)


class SimulationAgent:
    """AI agent for exploring and explaining simulation data."""
    
    MAX_FUNCTION_CALLS = 10  # Prevent infinite loops
    
    def __init__(self, data: Dict):
        """Initialize agent with simulation data.
        
        Args:
            data: Simulation log data with snapshots and events
        """
        if OpenAI is None:
            raise ImportError("OpenAI library not installed. Run: pip install openai")
        
        self.data = data
        self.snapshots = data.get("snapshots", [])
        self.events = data.get("events", [])
        self.metadata = data.get("metadata", {})
        
        # Load API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"  # Cost-effective model
        
        # Define function tools
        self.tools = self._define_tools()
        
        # System prompt
        self.system_prompt = self._create_system_prompt()
    
    def _create_system_prompt(self) -> str:
        """Create system prompt describing the simulation."""
        summary = get_log_summary(self.data)
        
        return f"""You are an expert restaurant operations analyst helping users understand simulation results.

**Current Simulation Summary:**
- Duration: {summary.get('duration_minutes', 0):.1f} minutes ({summary.get('duration_hours', 0):.2f} hours)
- Parties: {summary.get('num_parties', 0)}
- Total Revenue: ${summary.get('total_revenue', 0):,.2f}
- Snapshots: {summary.get('num_snapshots', 0)}
- Events: {summary.get('num_events', 0)}

**Your Role:**
- Use function tools to explore and analyze the simulation data
- Don't guess or make up numbers - always call functions to get accurate data
- Explain findings in clear, business-friendly language
- Provide actionable insights when possible
- Cite specific numbers and metrics from the data

**Available Metrics:**
- RevPASH: Revenue Per Available Seat Hour
- Utilization: Table, staff, and station utilization rates
- Queue metrics: Wait times and queue lengths
- Service times: Kitchen, dining, total time
- Throughput: Parties and dishes served over time

When answering questions:
1. Use functions to gather relevant data
2. Analyze the data to understand patterns
3. Provide clear explanations with specific numbers
4. Suggest improvements if appropriate"""
    
    def _define_tools(self) -> List[Dict]:
        """Define function tools for data access."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_simulation_summary",
                    "description": "Get high-level summary of the simulation including duration, parties served, revenue, and event counts",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_metric",
                    "description": "Calculate performance metrics like RevPASH, utilization, queues, throughput, or service times",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "metric_name": {
                                "type": "string",
                                "enum": ["revpash", "table_utilization", "staff_utilization", 
                                        "station_utilization", "queue_metrics", "throughput", 
                                        "service_times", "summary_statistics"],
                                "description": "The metric to calculate"
                            },
                            "time_range": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 2,
                                "maxItems": 2,
                                "description": "Optional time range [start_min, end_min] to filter data"
                            }
                        },
                        "required": ["metric_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_snapshot_at_time",
                    "description": "Get system state snapshot at a specific time point",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "time_minutes": {
                                "type": "number",
                                "description": "Time in minutes to get snapshot for"
                            }
                        },
                        "required": ["time_minutes"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_events",
                    "description": "Filter and retrieve events by type, time range, or entity ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "event_type": {
                                "type": "string",
                                "description": "Filter by event type (e.g., PARTY_ARRIVED, ORDER_PLACED)"
                            },
                            "time_range": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 2,
                                "maxItems": 2,
                                "description": "Time range [start_min, end_min]"
                            },
                            "entity_id": {
                                "type": "integer",
                                "description": "Filter by specific entity ID (party, dish, etc.)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of events to return (default: 50)",
                                "default": 50
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_parties_by_status",
                    "description": "Get parties filtered by their status or at a specific time",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "description": "Filter by status (waiting, seated, dining, completed, etc.)"
                            },
                            "time_minutes": {
                                "type": "number",
                                "description": "Get parties at a specific time point"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_station_performance",
                    "description": "Get performance metrics for a specific kitchen station",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "station_name": {
                                "type": "string",
                                "enum": ["wood_grill", "salad_station", "sautee_station", 
                                        "tortilla_station", "guac_station"],
                                "description": "The kitchen station to analyze"
                            },
                            "time_range": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 2,
                                "maxItems": 2,
                                "description": "Optional time range [start_min, end_min]"
                            }
                        },
                        "required": ["station_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_custom_statistic",
                    "description": "Calculate custom statistics like peak times, averages, or specific patterns",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "statistic": {
                                "type": "string",
                                "enum": ["peak_utilization_time", "average_wait_time", 
                                        "revenue_per_hour", "busiest_hour", "slowest_hour"],
                                "description": "The statistic to calculate"
                            }
                        },
                        "required": ["statistic"]
                    }
                }
            }
        ]
    
    def _execute_function(self, function_name: str, arguments: Dict) -> Any:
        """Execute a function tool and return results.
        
        Args:
            function_name: Name of function to execute
            arguments: Function arguments
        
        Returns:
            Function result
        """
        try:
            if function_name == "get_simulation_summary":
                return self._get_simulation_summary()
            
            elif function_name == "calculate_metric":
                return self._calculate_metric(
                    arguments["metric_name"],
                    arguments.get("time_range")
                )
            
            elif function_name == "get_snapshot_at_time":
                return self._get_snapshot_at_time(arguments["time_minutes"])
            
            elif function_name == "query_events":
                return self._query_events(
                    arguments.get("event_type"),
                    arguments.get("time_range"),
                    arguments.get("entity_id"),
                    arguments.get("limit", 50)
                )
            
            elif function_name == "get_parties_by_status":
                return self._get_parties_by_status(
                    arguments.get("status"),
                    arguments.get("time_minutes")
                )
            
            elif function_name == "get_station_performance":
                return self._get_station_performance(
                    arguments["station_name"],
                    arguments.get("time_range")
                )
            
            elif function_name == "calculate_custom_statistic":
                return self._calculate_custom_statistic(arguments["statistic"])
            
            else:
                return {"error": f"Unknown function: {function_name}"}
        
        except Exception as e:
            return {"error": f"Error executing {function_name}: {str(e)}"}
    
    # ========== Function Tool Implementations ==========
    
    def _get_simulation_summary(self) -> Dict:
        """Get simulation summary."""
        return get_log_summary(self.data)
    
    def _calculate_metric(self, metric_name: str, time_range: Optional[List[float]] = None) -> Dict:
        """Calculate specified metric."""
        # Filter snapshots by time range if provided
        snapshots = self.snapshots
        if time_range:
            start, end = time_range
            snapshots = [s for s in snapshots if start <= s.get("time", 0) <= end]
        
        if not snapshots:
            return {"error": "No snapshots in specified time range"}
        
        try:
            if metric_name == "revpash":
                df = calculate_revpash(snapshots)
                return {
                    "metric": "revpash",
                    "final_revpash": float(df['revpash'].iloc[-1]) if len(df) > 0 else 0,
                    "average_revpash": float(df['revpash'].mean()) if len(df) > 0 else 0,
                    "data_points": len(df)
                }
            
            elif metric_name == "table_utilization":
                df = calculate_table_utilization(snapshots)
                return {
                    "metric": "table_utilization",
                    "average_utilization": float(df['utilization'].mean()) if len(df) > 0 else 0,
                    "peak_utilization": float(df['utilization'].max()) if len(df) > 0 else 0,
                    "data_points": len(df)
                }
            
            elif metric_name == "staff_utilization":
                df = calculate_staff_utilization(snapshots)
                if len(df) > 0:
                    # Get average utilization for each staff type
                    result = {"metric": "staff_utilization"}
                    for col in df.columns:
                        if col != 'time':
                            result[f"{col}_avg"] = float(df[col].mean())
                    return result
                return {"metric": "staff_utilization", "error": "No data"}
            
            elif metric_name == "station_utilization":
                df = calculate_station_utilization(snapshots)
                if len(df) > 0:
                    result = {"metric": "station_utilization"}
                    for col in df.columns:
                        if col != 'time':
                            result[f"{col}_avg"] = float(df[col].mean())
                    return result
                return {"metric": "station_utilization", "error": "No data"}
            
            elif metric_name == "queue_metrics":
                df = calculate_queue_metrics(snapshots)
                return {
                    "metric": "queue_metrics",
                    "average_guest_queue": float(df['guest_queue'].mean()) if 'guest_queue' in df.columns else 0,
                    "max_guest_queue": float(df['guest_queue'].max()) if 'guest_queue' in df.columns else 0,
                    "data_points": len(df)
                }
            
            elif metric_name == "throughput":
                df = calculate_throughput_metrics(snapshots)
                return {
                    "metric": "throughput",
                    "parties_served": int(df['parties_served'].iloc[-1]) if len(df) > 0 else 0,
                    "dishes_delivered": int(df['dishes_delivered'].iloc[-1]) if len(df) > 0 else 0,
                    "data_points": len(df)
                }
            
            elif metric_name == "service_times":
                times = calculate_service_times(snapshots)
                result = {"metric": "service_times"}
                for key, values in times.items():
                    if values:
                        result[f"{key}_mean"] = float(np.mean(values))
                        result[f"{key}_median"] = float(np.median(values))
                        result[f"{key}_max"] = float(np.max(values))
                return result
            
            elif metric_name == "summary_statistics":
                return calculate_summary_statistics(snapshots)
            
            else:
                return {"error": f"Unknown metric: {metric_name}"}
        
        except Exception as e:
            return {"error": f"Error calculating {metric_name}: {str(e)}"}
    
    def _get_snapshot_at_time(self, time_minutes: float) -> Dict:
        """Get snapshot closest to specified time."""
        if not self.snapshots:
            return {"error": "No snapshots available"}
        
        # Find closest snapshot
        closest = min(self.snapshots, key=lambda s: abs(s.get("time", 0) - time_minutes))
        
        # Return simplified snapshot (full snapshot is too large)
        return {
            "time": closest.get("time", 0),
            "parties_in_system": closest.get("parties_in_system", 0),
            "total_revenue": closest.get("total_revenue", 0),
            "guest_queue_length": closest.get("guest_queue_length", 0),
            "expo_queue_length": closest.get("expo_queue_length", 0),
            "parties_served": closest.get("parties_served", 0)
        }
    
    def _query_events(self, event_type: Optional[str], time_range: Optional[List[float]], 
                      entity_id: Optional[int], limit: int) -> Dict:
        """Query and filter events."""
        filtered_events = self.events
        
        # Filter by event type
        if event_type:
            filtered_events = [e for e in filtered_events if e.get("event_type") == event_type]
        
        # Filter by time range
        if time_range:
            start, end = time_range
            filtered_events = [e for e in filtered_events if start <= e.get("timestamp", 0) <= end]
        
        # Filter by entity ID
        if entity_id is not None:
            filtered_events = [e for e in filtered_events if e.get("entity_id") == entity_id]
        
        # Limit results
        filtered_events = filtered_events[:limit]
        
        return {
            "total_matching": len(filtered_events),
            "events": filtered_events[:10],  # Return first 10 for brevity
            "summary": f"Found {len(filtered_events)} matching events"
        }
    
    def _get_parties_by_status(self, status: Optional[str], time_minutes: Optional[float]) -> Dict:
        """Get parties filtered by status."""
        if time_minutes is not None:
            # Get snapshot at time
            snapshot = min(self.snapshots, key=lambda s: abs(s.get("time", 0) - time_minutes))
            parties = snapshot.get("parties", [])
        else:
            # Get all parties from final snapshot
            if self.snapshots:
                parties = self.snapshots[-1].get("parties", [])
            else:
                parties = []
        
        # Filter by status if provided
        if status:
            parties = [p for p in parties if p.get("status") == status]
        
        # Return summary
        return {
            "count": len(parties),
            "parties": parties[:10],  # First 10 for brevity
            "summary": f"Found {len(parties)} parties" + (f" with status '{status}'" if status else "")
        }
    
    def _get_station_performance(self, station_name: str, time_range: Optional[List[float]]) -> Dict:
        """Get station performance metrics."""
        snapshots = self.snapshots
        if time_range:
            start, end = time_range
            snapshots = [s for s in snapshots if start <= s.get("time", 0) <= end]
        
        if not snapshots:
            return {"error": "No data in time range"}
        
        # Calculate utilization for this station
        try:
            queue_key = f"{station_name}_queue"
            busy_key = f"{station_name}_busy"
            
            queue_lengths = [s.get(queue_key, 0) for s in snapshots]
            busy_slots = [s.get(busy_key, 0) for s in snapshots]
            
            return {
                "station": station_name,
                "average_queue_length": float(np.mean(queue_lengths)) if queue_lengths else 0,
                "max_queue_length": int(max(queue_lengths)) if queue_lengths else 0,
                "average_busy_slots": float(np.mean(busy_slots)) if busy_slots else 0,
                "max_busy_slots": int(max(busy_slots)) if busy_slots else 0,
                "time_range": time_range,
                "data_points": len(snapshots)
            }
        except Exception as e:
            return {"error": f"Error analyzing {station_name}: {str(e)}"}
    
    def _calculate_custom_statistic(self, statistic: str) -> Dict:
        """Calculate custom statistic."""
        try:
            if statistic == "peak_utilization_time":
                # Find time with highest table utilization
                df = calculate_table_utilization(self.snapshots)
                if len(df) > 0:
                    peak_idx = df['utilization'].idxmax()
                    peak_row = df.loc[peak_idx]
                    return {
                        "statistic": "peak_utilization_time",
                        "time_minutes": float(peak_row['time']),
                        "utilization": float(peak_row['utilization']),
                        "occupied_tables": int(peak_row['occupied'])
                    }
            
            elif statistic == "revenue_per_hour":
                summary = calculate_summary_statistics(self.snapshots)
                duration_hours = summary.get('duration_hours', 1)
                revenue = summary.get('total_revenue', 0)
                return {
                    "statistic": "revenue_per_hour",
                    "revenue_per_hour": revenue / duration_hours if duration_hours > 0 else 0,
                    "total_revenue": revenue,
                    "duration_hours": duration_hours
                }
            
            elif statistic in ["busiest_hour", "slowest_hour"]:
                # Analyze parties per time window
                df = calculate_throughput_metrics(self.snapshots)
                if len(df) > 0:
                    # Calculate rate of change (parties served per interval)
                    df['parties_rate'] = df['parties_served'].diff().fillna(0)
                    
                    if statistic == "busiest_hour":
                        busiest_idx = df['parties_rate'].idxmax()
                        busiest_row = df.loc[busiest_idx]
                        return {
                            "statistic": "busiest_hour",
                            "time_minutes": float(busiest_row['time']),
                            "parties_in_interval": float(busiest_row['parties_rate'])
                        }
                    else:  # slowest_hour
                        slowest_idx = df['parties_rate'].idxmin()
                        slowest_row = df.loc[slowest_idx]
                        return {
                            "statistic": "slowest_hour",
                            "time_minutes": float(slowest_row['time']),
                            "parties_in_interval": float(slowest_row['parties_rate'])
                        }
            
            return {"error": f"Unknown statistic: {statistic}"}
        
        except Exception as e:
            return {"error": f"Error calculating {statistic}: {str(e)}"}
    
    def answer_question(self, question: str) -> Tuple[str, List[Dict]]:
        """Answer a question about the simulation using function calling.
        
        Args:
            question: User's question
        
        Returns:
            Tuple of (answer_text, function_calls_made)
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": question}
        ]
        
        function_calls_made = []
        iterations = 0
        
        while iterations < self.MAX_FUNCTION_CALLS:
            iterations += 1
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )
            
            assistant_message = response.choices[0].message
            
            # Check if function calls were made
            if not assistant_message.tool_calls:
                # No more function calls, return answer
                return assistant_message.content, function_calls_made
            
            # Add assistant message to conversation
            messages.append(assistant_message)
            
            # Execute each function call
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                # Execute function
                result = self._execute_function(function_name, arguments)
                
                # Record function call
                function_calls_made.append({
                    "function": function_name,
                    "arguments": arguments,
                    "result": result
                })
                
                # Add function result to conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": json.dumps(result)
                })
        
        # Max iterations reached
        return "I apologize, but I've reached the maximum number of function calls. Please try asking a more specific question.", function_calls_made

