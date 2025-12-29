"""Process simulation logs into chunks for RAG system.

This module processes simulation log data (metadata, snapshots, events) into
structured chunks with natural language descriptions for vector embedding.
"""

import numpy as np
from typing import Dict, List, Any
from datetime import datetime


class LogProcessor:
    """Process simulation logs into natural language chunks for RAG."""
    
    def __init__(self):
        """Initialize the log processor."""
        pass
    
    def process_log(self, log_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process a single simulation log into chunks.
        
        Args:
            log_data: Simulation log data with metadata, snapshots, and events
            
        Returns:
            List of chunk dictionaries with content and metadata
        """
        chunks = []
        
        # Extract components
        metadata = log_data.get('metadata', {})
        snapshots = log_data.get('snapshots', [])
        events = log_data.get('events', [])
        
        # Generate different types of chunks
        chunks.extend(self._extract_summary_chunks(metadata, snapshots))
        chunks.extend(self._extract_time_series_chunks(snapshots))
        chunks.extend(self._extract_insight_chunks(snapshots))
        chunks.extend(self._extract_configuration_chunks(metadata, snapshots))
        
        return chunks
    
    def _extract_summary_chunks(self, metadata: Dict, snapshots: List[Dict]) -> List[Dict]:
        """Extract high-level summary chunks."""
        chunks = []
        
        if not snapshots:
            return chunks
        
        # Overall summary
        final_snapshot = snapshots[-1]
        duration_minutes = final_snapshot.get('time', 0)
        duration_hours = duration_minutes / 60.0
        
        revenue = final_snapshot.get('total_revenue', 0)
        parties_served = final_snapshot.get('parties_served', 0)
        
        summary_content = (
            f"This simulation ran for {duration_hours:.2f} hours ({duration_minutes:.1f} minutes). "
            f"The restaurant served {parties_served} parties and generated ${revenue:,.2f} in total revenue. "
            f"The average revenue per party was ${revenue/parties_served:.2f} if we served any parties."
        )
        
        chunks.append({
            'content': summary_content,
            'metadata': {
                'chunk_type': 'summary',
                'time_range': [0, duration_minutes],
                'metrics': {
                    'duration_hours': duration_hours,
                    'parties_served': parties_served,
                    'total_revenue': revenue
                }
            }
        })
        
        return chunks
    
    def _extract_time_series_chunks(self, snapshots: List[Dict]) -> List[Dict]:
        """Extract time-based patterns and trends."""
        chunks = []
        
        if len(snapshots) < 2:
            return chunks
        
        # Aggregate by hour
        hours = {}
        for snapshot in snapshots:
            time = snapshot.get('time', 0)
            hour = int(time // 60)
            
            if hour not in hours:
                hours[hour] = {
                    'parties_in_system': [],
                    'guest_queue': [],
                    'revenue': [],
                    'times': []
                }
            
            hours[hour]['parties_in_system'].append(snapshot.get('parties_in_system', 0))
            hours[hour]['guest_queue'].append(snapshot.get('guest_queue_length', 0))
            hours[hour]['revenue'].append(snapshot.get('total_revenue', 0))
            hours[hour]['times'].append(time)
        
        # Find peak hour
        if hours:
            peak_hour = max(hours.keys(), key=lambda h: np.mean(hours[h]['parties_in_system']) if hours[h]['parties_in_system'] else 0)
            peak_data = hours[peak_hour]
            
            avg_parties = np.mean(peak_data['parties_in_system']) if peak_data['parties_in_system'] else 0
            avg_queue = np.mean(peak_data['guest_queue']) if peak_data['guest_queue'] else 0
            
            peak_content = (
                f"The busiest period was hour {peak_hour} (minutes {peak_hour*60} to {(peak_hour+1)*60}). "
                f"During this time, there were an average of {avg_parties:.1f} parties in the restaurant "
                f"with an average of {avg_queue:.1f} parties waiting in the guest queue."
            )
            
            chunks.append({
                'content': peak_content,
                'metadata': {
                    'chunk_type': 'time_series',
                    'time_range': [peak_hour * 60, (peak_hour + 1) * 60],
                    'metrics': {
                        'avg_parties': avg_parties,
                        'avg_queue': avg_queue,
                        'hour': peak_hour
                    }
                }
            })
        
        return chunks
    
    def _extract_insight_chunks(self, snapshots: List[Dict]) -> List[Dict]:
        """Extract insights about bottlenecks and performance issues."""
        chunks = []
        
        if not snapshots:
            return chunks
        
        # Analyze station utilization
        station_names = ['wood_grill', 'salad_station', 'sautee_station', 'tortilla_station', 'guac_station']
        station_utils = {name: [] for name in station_names}
        station_queues = {name: [] for name in station_names}
        
        for snapshot in snapshots:
            for station in station_names:
                busy_key = f'{station}_busy'
                capacity_key = f'{station}_capacity'
                queue_key = f'{station}_queue'
                
                if busy_key in snapshot and capacity_key in snapshot:
                    capacity = snapshot[capacity_key]
                    if capacity > 0:
                        util = snapshot[busy_key] / capacity
                        station_utils[station].append(util)
                
                if queue_key in snapshot:
                    station_queues[station].append(snapshot[queue_key])
        
        # Find bottleneck station
        avg_utils = {name: np.mean(utils) if utils else 0 for name, utils in station_utils.items()}
        if avg_utils:
            bottleneck_station = max(avg_utils.keys(), key=lambda s: avg_utils[s])
            bottleneck_util = avg_utils[bottleneck_station]
            
            if bottleneck_util > 0.7:  # Over 70% utilization
                station_display = bottleneck_station.replace('_', ' ').title()
                bottleneck_content = (
                    f"The {station_display} was the busiest station with {bottleneck_util*100:.1f}% average utilization. "
                    f"This station may be a bottleneck in your operation. "
                    f"Consider adding more capacity or redistributing work."
                )
                
                chunks.append({
                    'content': bottleneck_content,
                    'metadata': {
                        'chunk_type': 'insight',
                        'time_range': [0, snapshots[-1].get('time', 0)],
                        'metrics': {
                            'station': bottleneck_station,
                            'utilization': bottleneck_util
                        }
                    }
                })
        
        # Analyze queue performance
        guest_queues = [s.get('guest_queue_length', 0) for s in snapshots]
        if guest_queues:
            max_queue = max(guest_queues)
            avg_queue = np.mean(guest_queues)
            
            if max_queue > 5:  # Significant queue
                queue_content = (
                    f"The guest queue reached a maximum of {max_queue} parties waiting. "
                    f"The average queue length was {avg_queue:.1f} parties. "
                    f"Long queues may indicate you need more host capacity or faster table turnover."
                )
                
                chunks.append({
                    'content': queue_content,
                    'metadata': {
                        'chunk_type': 'insight',
                        'time_range': [0, snapshots[-1].get('time', 0)],
                        'metrics': {
                            'max_queue': max_queue,
                            'avg_queue': avg_queue
                        }
                    }
                })
        
        return chunks
    
    def _extract_configuration_chunks(self, metadata: Dict, snapshots: List[Dict]) -> List[Dict]:
        """Extract configuration details."""
        chunks = []
        
        if not snapshots:
            return chunks
        
        # Extract staffing from first snapshot
        first_snapshot = snapshots[0]
        
        # Count resources
        num_servers = first_snapshot.get('num_servers', metadata.get('num_servers', 0))
        num_cooks = first_snapshot.get('num_cooks', metadata.get('num_cooks', 0))
        num_hosts = first_snapshot.get('num_hosts', metadata.get('num_hosts', 0))
        num_food_runners = first_snapshot.get('num_food_runners', metadata.get('num_food_runners', 0))
        num_bussers = first_snapshot.get('num_bussers', metadata.get('num_bussers', 0))
        
        config_content = (
            f"This simulation was configured with {num_servers} servers, {num_cooks} cooks, "
            f"{num_hosts} hosts, {num_food_runners} food runners, and {num_bussers} bussers. "
        )
        
        # Add station capacities
        station_info = []
        for station in ['wood_grill', 'salad_station', 'sautee_station', 'tortilla_station', 'guac_station']:
            capacity_key = f'{station}_capacity'
            if capacity_key in first_snapshot:
                capacity = first_snapshot[capacity_key]
                display_name = station.replace('_', ' ').title()
                station_info.append(f"{display_name} has capacity {capacity}")
        
        if station_info:
            config_content += "Station capacities: " + ", ".join(station_info) + "."
        
        chunks.append({
            'content': config_content,
            'metadata': {
                'chunk_type': 'configuration',
                'time_range': [0, 0],
                'metrics': {
                    'num_servers': num_servers,
                    'num_cooks': num_cooks,
                    'num_hosts': num_hosts,
                    'num_food_runners': num_food_runners,
                    'num_bussers': num_bussers
                }
            }
        })
        
        return chunks

