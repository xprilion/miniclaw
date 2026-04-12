"""Enhanced decision-making capabilities for MiniClaw."""

from typing import Any, Dict, List, Union
from ..core.events import EventLog
from ..core.util import LOGGER


class DecisionFramework:
    """Structured decision-making framework."""
    
    def __init__(self, event_log: EventLog) -> None:
        self._event_log = event_log
    
    def evaluate_options(self, options: List[Dict[str, Any]], criteria: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Score and rank options based on criteria."""
        self._event_log.add(
            "decision.options_evaluation",
            "Evaluating options against criteria",
            {"option_count": len(options), "criteria_count": len(criteria)}
        )
        
        scored_options = []
        for option in options:
            score_details = self._calculate_score(option, criteria)
            scored_options.append({
                **option,
                "score": score_details["total_score"],
                "breakdown": score_details["breakdown"],
                "normalized_score": score_details["normalized_score"]
            })
        
        # Sort by score (highest first)
        return sorted(scored_options, key=lambda x: x["score"], reverse=True)
    
    def _calculate_score(self, option: Dict[str, Any], criteria: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate weighted score for an option with detailed breakdown."""
        total_score = 0.0
        total_weight = 0.0
        breakdown = {}
        
        for criterion in criteria:
            name = criterion["name"]
            weight = float(criterion.get("weight", 1.0))
            
            # Get the evaluation value for this criterion
            # This could be a direct value or need to be calculated
            value = self._get_criterion_value(option, criterion)
            
            weighted_score = weight * value
            total_score += weighted_score
            total_weight += weight
            
            breakdown[name] = {
                "weight": weight,
                "value": value,
                "weighted_score": weighted_score
            }
        
        normalized_score = total_score / total_weight if total_weight > 0 else 0.0
        
        return {
            "total_score": total_score,
            "normalized_score": normalized_score,
            "breakdown": breakdown
        }
    
    def _get_criterion_value(self, option: Dict[str, Any], criterion: Dict[str, Any]) -> float:
        """Extract or calculate the value for a criterion from an option."""
        name = criterion["name"]
        
        # First check if the value is directly provided in the option's evaluation
        if "evaluation" in option and name in option["evaluation"]:
            return float(option["evaluation"][name])
        
        # If not, look for it in the option's direct properties
        if name in option:
            value = option[name]
            # Convert boolean to float (True=1.0, False=0.0)
            if isinstance(value, bool):
                return 1.0 if value else 0.0
            # Convert string numbers to float
            if isinstance(value, str):
                try:
                    return float(value)
                except ValueError:
                    # If it's a string that can't be converted, return a mid-value
                    return 0.5
            # Convert numeric values to float
            if isinstance(value, (int, float)):
                return float(value)
        
        # Default value if not found
        return 0.5
    
    def make_decision_with_criteria(self, options: List[Dict[str, Any]], 
                                  criteria: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Make a decision based on weighted criteria evaluation."""
        if not options:
            return {
                "selected_option": None,
                "confidence": 0.0,
                "reasoning": "No options provided for evaluation"
            }
        
        if not criteria:
            # If no criteria provided, select the first option
            return {
                "selected_option": options[0],
                "confidence": 0.5,
                "reasoning": "No criteria provided, selecting first option"
            }
        
        # Evaluate all options
        scored_options = self.evaluate_options(options, criteria)
        best_option = scored_options[0]
        
        # Calculate confidence based on score difference
        confidence = self._calculate_confidence(scored_options)
        
        # Generate reasoning based on top criteria
        reasoning = self._generate_decision_reasoning(best_option, scored_options, criteria)
        
        self._event_log.add(
            "decision.made",
            "Decision made based on criteria evaluation",
            {
                "selected_option": best_option.get("id", "unknown"),
                "confidence": confidence,
                "top_score": best_option["score"],
                "total_options": len(options)
            }
        )
        
        return {
            "selected_option": best_option,
            "confidence": confidence,
            "reasoning": reasoning,
            "scored_options": scored_options
        }
    
    def _calculate_confidence(self, scored_options: List[Dict[str, Any]]) -> float:
        """Calculate confidence based on score differences."""
        if len(scored_options) == 0:
            return 0.0
        if len(scored_options) == 1:
            return 0.9  # High confidence when only one option
        
        best_score = scored_options[0]["score"]
        second_score = scored_options[1]["score"] if len(scored_options) > 1 else 0.0
        
        # Confidence is higher when there's a clear winner
        score_difference = best_score - second_score
        # Normalize the difference to a confidence value between 0.5 and 0.95
        confidence = 0.5 + (0.45 * min(1.0, score_difference / (best_score + 1e-10)))
        
        return confidence
    
    def _generate_decision_reasoning(self, best_option: Dict[str, Any], 
                                   scored_options: List[Dict[str, Any]], 
                                   criteria: List[Dict[str, Any]]) -> str:
        """Generate human-readable reasoning for the decision."""
        if not best_option:
            return "No option selected"
        
        reasoning_parts = []
        reasoning_parts.append(f"Selected '{best_option.get('name', 'Unknown')}' based on evaluation against criteria.")
        
        # Mention top criteria that influenced the decision
        if "breakdown" in best_option:
            # Sort criteria by weighted score to find the most influential
            sorted_criteria = sorted(
                best_option["breakdown"].items(),
                key=lambda x: x[1]["weighted_score"],
                reverse=True
            )
            
            top_criteria = sorted_criteria[:2]  # Top 2 criteria
            if top_criteria:
                reasoning_parts.append("Key factors:")
                for criterion_name, details in top_criteria:
                    reasoning_parts.append(f"  - {criterion_name}: scored {details['value']:.2f} (weight: {details['weight']})")
        
        # Compare with the next best option if available
        if len(scored_options) > 1:
            second_option = scored_options[1]
            reasoning_parts.append(f"Next best was '{second_option.get('name', 'Unknown')}' with a score of {second_option['score']:.2f}.")
        
        return " ".join(reasoning_parts)
    
    def format_decision_explanation(self, decision_result: Dict[str, Any]) -> str:
        """Format decision process into clear explanation."""
        if not decision_result:
            return "No decision information available."
        
        explanation = ["# Decision Analysis\n"]
        
        selected = decision_result.get("selected_option", {})
        if selected:
            explanation.append(f"## Selected Option: {selected.get('name', 'Unknown')}")
            explanation.append(f"**Confidence**: {decision_result.get('confidence', 0.0) * 100:.1f}%")
            explanation.append(f"**Reasoning**: {decision_result.get('reasoning', 'No reasoning provided')}")
            explanation.append("")
        
        # Show scored options if available
        scored_options = decision_result.get("scored_options", [])
        if scored_options:
            explanation.append("## All Options Ranked")
            for i, option in enumerate(scored_options, 1):
                explanation.append(f"{i}. {option.get('name', 'Unknown')} (Score: {option.get('score', 0.0):.2f})")
            explanation.append("")
        
        # Show detailed breakdown for the selected option
        if selected and "breakdown" in selected:
            explanation.append("## Scoring Breakdown")
            for criterion, details in selected["breakdown"].items():
                explanation.append(f"- {criterion}: Value={details['value']:.2f}, Weight={details['weight']:.1f}, Score={details['weighted_score']:.2f}")
            explanation.append("")
        
        return "\n".join(explanation)
