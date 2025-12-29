"""Fact-checking system for RAG chatbot responses.

This module validates numerical claims in chatbot answers against
ground truth simulation data to ensure accuracy and transparency.
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np


@dataclass
class Claim:
    """Represents a numerical claim extracted from text."""
    value: float
    context: str  # Surrounding text
    position: int  # Character position in original text
    unit_type: str  # 'currency', 'percentage', 'time', 'count'
    unit: str  # 'dollar', 'percent', 'hours', 'minutes', 'generic'
    
    def __str__(self):
        if self.unit_type == 'currency':
            return f"${self.value:,.2f}"
        elif self.unit_type == 'percentage':
            return f"{self.value}%"
        elif self.unit_type == 'time':
            return f"{self.value} {self.unit}"
        else:
            return f"{self.value}"


@dataclass
class ValidationResult:
    """Result of validating a claim against ground truth."""
    claim: Claim
    ground_truth: Optional[float]
    error: Optional[float]  # Relative error (0.0 = perfect, 1.0 = 100% off)
    accuracy_level: str  # 'accurate', 'approximate', 'inaccurate', 'unverified'
    metric_name: Optional[str]  # Which ground truth metric was used
    
    @property
    def badge(self) -> str:
        """Return badge emoji for this validation result."""
        if self.accuracy_level == 'accurate':
            return '✓'
        elif self.accuracy_level == 'approximate':
            return '⚠'
        elif self.accuracy_level == 'inaccurate':
            return '✗'
        else:
            return '?'
    
    @property
    def color(self) -> str:
        """Return color for UI display."""
        if self.accuracy_level == 'accurate':
            return 'green'
        elif self.accuracy_level == 'approximate':
            return 'orange'
        elif self.accuracy_level == 'inaccurate':
            return 'red'
        else:
            return 'gray'


class FactChecker:
    """Validates chatbot responses against ground truth simulation data."""
    
    def __init__(self, simulation_data: Dict[str, Any]):
        """Initialize with simulation data for ground truth.
        
        Args:
            simulation_data: Dictionary containing simulation snapshots,
                            metadata, and calculated summary statistics.
        """
        self.simulation_data = simulation_data
        self.ground_truth = self._extract_ground_truth()
    
    def _extract_ground_truth(self) -> Dict[str, float]:
        """Extract ground truth metrics from simulation data."""
        # Prefer standardized metrics if available
        if isinstance(self.simulation_data, dict) and 'total_revenue' in self.simulation_data:
            # This is summary_stats dictionary
            return {
                'total_revenue': self.simulation_data.get('total_revenue', 0),
                'parties_served': self.simulation_data.get('parties_served', 0),
                'duration_hours': self.simulation_data.get('duration_hours', 0),
                'revpash': self.simulation_data.get('revpash', 0),
                'revenue_per_party': self.simulation_data.get('revenue_per_party', 0),
                'parties_per_hour': self.simulation_data.get('parties_per_hour', 0),
                'avg_table_utilization': self.simulation_data.get('avg_table_utilization', 0),
                'avg_station_utilization': self.simulation_data.get('avg_station_utilization', 0),
                'avg_wait_time': self.simulation_data.get('avg_wait_time', 0),
                'avg_kitchen_time': self.simulation_data.get('avg_kitchen_time', 0),
                'avg_dining_time': self.simulation_data.get('avg_dining_time', 0),
                'total_dishes': self.simulation_data.get('total_dishes', 0),
                'dishes_per_hour': self.simulation_data.get('dishes_per_hour', 0),
            }
        
        # Fallback: extract from snapshots if given full simulation data
        snapshots = self.simulation_data.get('snapshots', [])
        if not snapshots:
            return {}
        
        # Extract from final snapshot
        final_snapshot = snapshots[-1]
        return {
            'total_revenue': final_snapshot.get('total_revenue', 0),
            'parties_served': final_snapshot.get('parties_served', 0),
        }
    
    def extract_numerical_claims(self, answer: str) -> List[Claim]:
        """Extract all numerical claims from answer text.
        
        Args:
            answer: The chatbot's answer text
            
        Returns:
            List of Claim objects with extracted values and context
        """
        claims = []
        
        # Pattern definitions: (regex, unit_type, unit)
        patterns = [
            # Currency: $1,234.56 or $1234
            (r'\$\s*([\d,]+\.?\d*)', 'currency', 'dollar'),
            # Percentage: 45.5% or 45%
            (r'([\d,]+\.?\d*)\s*%', 'percentage', 'percent'),
            # Time with hours: 3.5 hours, 2 hrs
            (r'([\d,]+\.?\d*)\s*(?:hours?|hrs?)\b', 'time', 'hours'),
            # Time with minutes: 15 minutes, 20 mins
            (r'([\d,]+\.?\d*)\s*(?:minutes?|mins?)\b', 'time', 'minutes'),
            # Generic numbers (last to avoid capturing parts of above)
            (r'\b([\d,]+\.?\d*)\b', 'count', 'generic'),
        ]
        
        seen_positions = set()  # Avoid duplicate extraction
        
        for pattern, unit_type, unit in patterns:
            for match in re.finditer(pattern, answer, re.IGNORECASE):
                pos = match.start()
                
                # Skip if we already extracted a claim at this position
                if pos in seen_positions:
                    continue
                
                # Extract value
                value_str = match.group(1).replace(',', '')
                try:
                    value = float(value_str)
                except ValueError:
                    continue
                
                # Skip unreasonable values (likely not metrics)
                if value > 1e10 or (unit_type == 'percentage' and value > 200):
                    continue
                
                # Get context (30 chars before and after)
                start_ctx = max(0, pos - 30)
                end_ctx = min(len(answer), match.end() + 30)
                context = answer[start_ctx:end_ctx].strip()
                
                claims.append(Claim(
                    value=value,
                    context=context,
                    position=pos,
                    unit_type=unit_type,
                    unit=unit
                ))
                
                seen_positions.add(pos)
        
        # Sort by position
        claims.sort(key=lambda c: c.position)
        
        return claims
    
    def _infer_metric_from_context(self, claim: Claim, question: str) -> Optional[str]:
        """Infer which ground truth metric to use based on context.
        
        Args:
            claim: The extracted claim
            question: The original question
            
        Returns:
            Name of ground truth metric, or None if cannot infer
        """
        context = (claim.context + " " + question).lower()
        
        # Revenue-related
        if claim.unit_type == 'currency':
            if 'party' in context or 'per party' in context or 'average party' in context:
                return 'revenue_per_party'
            else:
                return 'total_revenue'
        
        # Parties/customers
        if 'part' in context and claim.unit_type == 'count':
            if 'hour' in context or 'per hour' in context:
                return 'parties_per_hour'
            else:
                return 'parties_served'
        
        # RevPASH
        if 'revpash' in context or 'revenue per' in context and 'seat' in context:
            return 'revpash'
        
        # Utilization
        if 'utilization' in context or 'busy' in context:
            if claim.unit_type == 'percentage':
                if 'table' in context:
                    return 'avg_table_utilization'
                elif 'station' in context or 'kitchen' in context:
                    return 'avg_station_utilization'
        
        # Wait times
        if claim.unit_type == 'time':
            if 'wait' in context or 'queue' in context:
                return 'avg_wait_time'
            elif 'kitchen' in context or 'cook' in context or 'prep' in context:
                return 'avg_kitchen_time'
            elif 'dining' in context or 'eat' in context or 'table' in context:
                return 'avg_dining_time'
        
        # Duration
        if 'duration' in context or 'long' in context and claim.unit_type == 'time':
            return 'duration_hours'
        
        # Dishes
        if 'dish' in context and claim.unit_type == 'count':
            if 'hour' in context:
                return 'dishes_per_hour'
            else:
                return 'total_dishes'
        
        return None
    
    def validate_claim(self, claim: Claim, question: str) -> ValidationResult:
        """Validate a single claim against ground truth.
        
        Args:
            claim: The claim to validate
            question: The original question for context
            
        Returns:
            ValidationResult with accuracy assessment
        """
        # Infer which metric to compare against
        metric_name = self._infer_metric_from_context(claim, question)
        
        if not metric_name or metric_name not in self.ground_truth:
            return ValidationResult(
                claim=claim,
                ground_truth=None,
                error=None,
                accuracy_level='unverified',
                metric_name=metric_name
            )
        
        ground_truth = self.ground_truth[metric_name]
        
        # Convert units if needed
        claimed_value = claim.value
        actual_value = ground_truth
        
        # Handle percentage conversion
        if claim.unit_type == 'percentage' and 0 <= actual_value <= 1:
            # Ground truth is 0-1, claim is 0-100
            actual_value = actual_value * 100
        elif claim.unit_type != 'percentage' and 0 <= claimed_value <= 1 and actual_value > 1:
            # Claim might be 0-1, ground truth is natural number
            claimed_value = claimed_value * 100
        
        # Calculate relative error
        if actual_value == 0 and claimed_value == 0:
            error = 0.0
        elif actual_value == 0:
            error = 1.0  # Any non-zero claim is wrong
        else:
            error = abs(claimed_value - actual_value) / abs(actual_value)
        
        # Classify accuracy
        if error < 0.05:  # < 5% error
            accuracy_level = 'accurate'
        elif error < 0.20:  # 5-20% error
            accuracy_level = 'approximate'
        else:  # > 20% error
            accuracy_level = 'inaccurate'
        
        return ValidationResult(
            claim=claim,
            ground_truth=ground_truth,
            error=error,
            accuracy_level=accuracy_level,
            metric_name=metric_name
        )
    
    def validate_answer(self, question: str, answer: str) -> Dict[str, Any]:
        """Validate entire answer against ground truth.
        
        Args:
            question: The user's question
            answer: The chatbot's answer
            
        Returns:
            Dictionary with validation report:
            - extracted_claims: List of all claims found
            - validated_claims: List of ValidationResult objects
            - overall_accuracy: Float 0-1 (proportion of accurate claims)
            - warning_flags: List of warning messages
        """
        # Extract all numerical claims
        claims = self.extract_numerical_claims(answer)
        
        # Validate each claim
        validated = []
        for claim in claims:
            result = self.validate_claim(claim, question)
            validated.append(result)
        
        # Calculate overall accuracy
        verifiable_results = [v for v in validated if v.accuracy_level != 'unverified']
        
        if verifiable_results:
            accurate_count = sum(1 for v in verifiable_results if v.accuracy_level == 'accurate')
            overall_accuracy = accurate_count / len(verifiable_results)
            avg_error = np.mean([v.error for v in verifiable_results if v.error is not None])
        else:
            overall_accuracy = None
            avg_error = None
        
        # Generate warnings
        warnings = []
        inaccurate_claims = [v for v in validated if v.accuracy_level == 'inaccurate']
        if inaccurate_claims:
            warnings.append(f"{len(inaccurate_claims)} claim(s) have >20% error")
        
        unverified_claims = [v for v in validated if v.accuracy_level == 'unverified']
        if len(unverified_claims) > 0 and len(validated) > 0:
            warnings.append(f"{len(unverified_claims)}/{len(validated)} claim(s) could not be verified")
        
        return {
            'extracted_claims': claims,
            'validated_claims': validated,
            'overall_accuracy': overall_accuracy,
            'average_error': avg_error,
            'warning_flags': warnings,
            'claim_count': len(claims),
            'verified_count': len(verifiable_results),
            'accurate_count': sum(1 for v in validated if v.accuracy_level == 'accurate'),
            'approximate_count': sum(1 for v in validated if v.accuracy_level == 'approximate'),
            'inaccurate_count': sum(1 for v in validated if v.accuracy_level == 'inaccurate'),
            'unverified_count': len(unverified_claims)
        }

