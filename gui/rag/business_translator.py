"""Business-friendly translation of technical metrics.

This module translates technical simulation metrics into plain language
that non-technical users (chefs, restaurant owners) can understand.
"""

from typing import Dict, Any, Optional


class BusinessTranslator:
    """Translates technical metrics to business-friendly language."""
    
    # Translation dictionary for common terms
    TRANSLATIONS = {
        'revpash': 'revenue per seat per hour',
        'utilization': 'how busy',
        'queue_length': 'customers waiting',
        'throughput': 'customers served',
        'parties_served': 'tables served',
        'service_time': 'time to serve',
        'wait_time': 'waiting time',
        'dining_time': 'time at table',
        'wood_grill': 'Wood Grill',
        'salad_station': 'Salad Station',
        'sautee_station': 'Sauté Station',
        'tortilla_station': 'Tortilla Station',
        'guac_station': 'Guacamole Station'
    }
    
    def __init__(self):
        """Initialize the business translator."""
        pass
    
    def translate_metric(self, metric_name: str, value: float, unit: str = "") -> str:
        """Translate a technical metric to plain language.
        
        Args:
            metric_name: Technical name of the metric
            value: Numeric value
            unit: Optional unit (e.g., 'min', '%', '$')
            
        Returns:
            Plain language description
        """
        metric_lower = metric_name.lower().replace('_', ' ')
        
        # Get friendly name
        friendly_name = self.TRANSLATIONS.get(metric_name.lower(), metric_lower)
        
        # Format value
        if 'utilization' in metric_lower or 'percent' in unit.lower():
            # Percentage values
            percent_value = value * 100 if value <= 1 else value
            return f"Your {friendly_name} was {percent_value:.1f}%"
        elif '$' in unit or 'revenue' in metric_lower or 'price' in metric_lower:
            # Money values
            return f"Your {friendly_name} was ${value:,.2f}"
        elif 'time' in metric_lower:
            # Time values (assume minutes)
            return f"Your {friendly_name} was {value:.1f} minutes"
        elif 'queue' in metric_lower or 'waiting' in metric_lower:
            # Queue/count values
            return f"You had {value:.0f} {friendly_name}"
        else:
            # Generic values
            return f"Your {friendly_name} was {value:.1f}{unit}"
    
    def generate_insight(self, metric_name: str, value: float, threshold: float, 
                        context: Optional[str] = None) -> str:
        """Generate an actionable insight with recommendation.
        
        Args:
            metric_name: Technical name of the metric
            value: Current value
            threshold: Threshold for determining if action is needed
            context: Optional context string
            
        Returns:
            Plain language insight with recommendation
        """
        metric_lower = metric_name.lower()
        friendly_name = self.TRANSLATIONS.get(metric_lower, metric_lower)
        
        # Utilization insights
        if 'utilization' in metric_lower:
            percent_value = value * 100 if value <= 1 else value
            
            if percent_value > 85:
                return (
                    f"Your {friendly_name} is at {percent_value:.1f}% - very busy! "
                    f"Consider adding more capacity or redistributing work to avoid bottlenecks."
                )
            elif percent_value > 70:
                return (
                    f"Your {friendly_name} is at {percent_value:.1f}% - getting busy. "
                    f"Monitor this during peak hours to ensure smooth operations."
                )
            elif percent_value < 30:
                return (
                    f"Your {friendly_name} is at {percent_value:.1f}% - not very busy. "
                    f"You might have excess capacity that could be reduced."
                )
            else:
                return (
                    f"Your {friendly_name} is at {percent_value:.1f}% - looks good! "
                    f"This is a healthy utilization level."
                )
        
        # Queue insights
        elif 'queue' in metric_lower:
            if value > 10:
                return (
                    f"You have {value:.0f} {friendly_name} - that's quite a lot! "
                    f"Consider adding more host staff or speeding up table turnover."
                )
            elif value > 5:
                return (
                    f"You have {value:.0f} {friendly_name} - manageable but watch it. "
                    f"Make sure your host team is working efficiently."
                )
            else:
                return (
                    f"You have {value:.0f} {friendly_name} - looking good! "
                    f"Your operations are running smoothly."
                )
        
        # Wait time insights
        elif 'wait' in metric_lower or 'time' in metric_lower:
            if value > 15:
                return (
                    f"Your {friendly_name} is {value:.1f} minutes - customers are waiting too long! "
                    f"Look for bottlenecks in your kitchen or service flow."
                )
            elif value > 10:
                return (
                    f"Your {friendly_name} is {value:.1f} minutes - getting longer than ideal. "
                    f"Monitor your service speed during busy times."
                )
            else:
                return (
                    f"Your {friendly_name} is {value:.1f} minutes - great! "
                    f"Customers are being served quickly."
                )
        
        # Revenue insights
        elif 'revenue' in metric_lower or 'revpash' in metric_lower:
            if value < threshold:
                return (
                    f"Your {friendly_name} is ${value:,.2f} - below target. "
                    f"Consider optimizing table turnover or menu pricing."
                )
            else:
                return (
                    f"Your {friendly_name} is ${value:,.2f} - meeting or exceeding goals! "
                    f"Keep up the good work."
                )
        
        # Generic insight
        else:
            comparison = "high" if value > threshold else "low"
            return f"Your {friendly_name} is {value:.1f}, which is {comparison} compared to the threshold of {threshold:.1f}."
    
    def translate_station_name(self, station_name: str) -> str:
        """Translate a station name to display format.
        
        Args:
            station_name: Technical station name (e.g., 'wood_grill')
            
        Returns:
            Display name (e.g., 'Wood Grill')
        """
        return self.TRANSLATIONS.get(station_name.lower(), 
                                     station_name.replace('_', ' ').title())
    
    def format_time_range(self, start_minutes: float, end_minutes: float) -> str:
        """Format a time range in a business-friendly way.
        
        Args:
            start_minutes: Start time in minutes
            end_minutes: End time in minutes
            
        Returns:
            Formatted time range (e.g., "7:30 PM to 8:30 PM")
        """
        def minutes_to_time(minutes: float) -> str:
            """Convert minutes to HH:MM format."""
            hours = int(minutes // 60)
            mins = int(minutes % 60)
            
            # Assume simulation starts at 5:00 PM (17:00)
            actual_hour = (17 + hours) % 24
            am_pm = "PM" if actual_hour >= 12 else "AM"
            display_hour = actual_hour if actual_hour <= 12 else actual_hour - 12
            if display_hour == 0:
                display_hour = 12
            
            return f"{display_hour}:{mins:02d} {am_pm}"
        
        start_time = minutes_to_time(start_minutes)
        end_time = minutes_to_time(end_minutes)
        
        return f"{start_time} to {end_time}"

