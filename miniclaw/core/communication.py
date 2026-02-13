"""Enhanced communication capabilities for MiniClaw."""

from typing import Any, Dict, List, Optional
from ..core.events import EventLog
from ..core.util import LOGGER


class CommunicationManager:
    """Manages structured communication of reasoning processes."""
    
    def __init__(self, event_log: EventLog) -> None:
        self._event_log = event_log
    
    def format_reasoning_explanation(self, reasoning_trace: Dict[str, Any]) -> str:
        """Format reasoning process into clear explanation."""
        if not reasoning_trace:
            return "No reasoning information available."
        
        explanation = ["# My Reasoning Process\n"]
        
        # Problem Analysis
        if "analysis" in reasoning_trace:
            analysis = reasoning_trace["analysis"]
            explanation.append("## Problem Analysis")
            explanation.append(f"**Goal**: {analysis.get('goal', 'N/A')}")
            
            constraints = analysis.get('constraints', [])
            if constraints:
                explanation.append(f"**Constraints**: {', '.join(constraints)}")
            
            criteria = analysis.get('success_criteria', [])
            if criteria:
                explanation.append(f"**Success Criteria**: {', '.join(criteria)}")
            
            stakeholders = analysis.get('stakeholders', [])
            if stakeholders:
                explanation.append(f"**Stakeholders**: {', '.join(stakeholders)}")
            
            explanation.append("")
        
        # Approach Exploration
        if "approaches" in reasoning_trace:
            approaches = reasoning_trace["approaches"]
            explanation.append("## Approaches Considered")
            for i, approach in enumerate(approaches, 1):
                explanation.append(f"{i}. **{approach.get('name', 'Approach')}")
                explanation.append(f"   - Description: {approach.get('description', 'N/A')}")
                
                pros = approach.get('pros', [])
                if pros:
                    explanation.append(f"   - Pros: {', '.join(pros)}")
                
                cons = approach.get('cons', [])
                if cons:
                    explanation.append(f"   - Cons: {', '.join(cons)}")
                
                effort = approach.get('effort')
                if effort:
                    explanation.append(f"   - Effort: {effort}")
                
                risk = approach.get('risk')
                if risk:
                    explanation.append(f"   - Risk: {risk}")
                
                explanation.append("")
        
        # Decision Making
        if "decision" in reasoning_trace:
            decision = reasoning_trace["decision"]
            selected = decision.get("selected", {})
            if selected:
                explanation.append("## Decision")
                explanation.append(f"**Selected Approach**: {selected.get('name', 'N/A')}")
                explanation.append(f"**Reasoning**: {decision.get('reasoning', 'N/A')}")
                
                confidence = decision.get('confidence')
                if confidence is not None:
                    explanation.append(f"**Confidence Level**: {confidence * 100:.0f}%")
                
                alternative = decision.get("alternative_considered")
                if alternative:
                    explanation.append(f"**Also Considered**: {alternative.get('name', 'N/A')}")
                
                explanation.append("")
        
        # Execution Plan
        if "plan" in reasoning_trace:
            plan = reasoning_trace["plan"]
            explanation.append("## Execution Plan")
            explanation.append(f"**Goal**: {plan.get('goal', 'N/A')}")
            explanation.append("")
            
            steps = plan.get("steps", [])
            for step in steps:
                explanation.append(f"- **{step.get('description', 'N/A')}")
                explanation.append(f"  - Expected Outcome: {step.get('expected_outcome', 'N/A')}")
                explanation.append(f"  - Success Criteria: {step.get('success_criteria', 'N/A')}")
                explanation.append("")
        
        return "\n".join(explanation)
    
    def generate_progress_update(self, execution_state: Dict[str, Any]) -> str:
        """Generate progress update messages."""
        if not execution_state:
            return "No execution state information available."
        
        progress = execution_state.get("progress", {})
        completed = progress.get("completed_steps", 0)
        total = progress.get("total_steps", 1)
        percentage = int((completed / total) * 100) if total > 0 else 0
        
        message = [f"## Execution Progress: {percentage}% ({completed}/{total} steps completed)"]
        
        current_step = execution_state.get("current_step")
        if current_step:
            message.append(f"**Current Step**: {current_step.get('description', 'N/A')}")
        
        completed_details = progress.get("completed_steps_details", [])
        if completed_details:
            message.append("\n**Completed Steps**:")
            for step_detail in completed_details:
                message.append(f"- {step_detail}")
        
        return "\n".join(message)
    
    def adapt_communication_style(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt communication based on user context."""
        # In a more advanced implementation, this would analyze user interaction history
        # to determine preferred communication style
        
        # For now, return default style
        return {
            "detail_level": "moderate",
            "technical_depth": "intermediate",
            "formality": "friendly_professional",
            "explanation_style": "structured"
        }
    
    def format_decision_explanation(self, decision_info: Dict[str, Any]) -> str:
        """Format decision-making process into clear explanation."""
        if not decision_info:
            return "No decision information available."
        
        explanation = ["# Decision-Making Process\n"]
        
        selected_option = decision_info.get("selected_option")
        if selected_option:
            explanation.append(f"## Selected Option: {selected_option.get('name', 'Unknown')}")
            
            confidence = decision_info.get("confidence")
            if confidence is not None:
                explanation.append(f"**Confidence Level**: {confidence * 100:.1f}%")
            
            reasoning = decision_info.get("reasoning")
            if reasoning:
                explanation.append(f"**Reasoning**: {reasoning}")
            
            explanation.append("")
        
        scored_options = decision_info.get("scored_options", [])
        if scored_options:
            explanation.append("## All Options Ranked")
            for i, option in enumerate(scored_options, 1):
                score = option.get("score", 0.0)
                explanation.append(f"{i}. {option.get('name', 'Unknown')} (Score: {score:.2f})")
            explanation.append("")
        
        return "\n".join(explanation)
    
    def format_planning_explanation(self, planning_info: Dict[str, Any]) -> str:
        """Format planning process into clear explanation."""
        if not planning_info:
            return "No planning information available."
        
        explanation = ["# Planning Process\n"]
        
        goal = planning_info.get("goal")
        if goal:
            explanation.append(f"## Goal: {goal}")
            explanation.append("")
        
        steps = planning_info.get("steps", [])
        if steps:
            explanation.append("## Planned Steps")
            for i, step in enumerate(steps, 1):
                explanation.append(f"{i}. {step.get('description', 'Unknown step')}")
            explanation.append("")
        
        return "\n".join(explanation)
    
    def create_comprehensive_explanation(self, cot_result: Dict[str, Any]) -> str:
        """Create a comprehensive explanation of the entire chain-of-thought process."""
        if not cot_result:
            return "No chain-of-thought information available."
        
        sections = []
        
        # Add reasoning explanation if available
        if "reasoning" in cot_result:
            reasoning_explanation = self.format_reasoning_explanation(cot_result["reasoning"])
            sections.append(reasoning_explanation)
        
        # Add decision explanation if available
        if "decision" in cot_result:
            decision_explanation = self.format_decision_explanation(cot_result["decision"])
            sections.append(decision_explanation)
        
        # Add planning explanation if available
        if "plan" in cot_result:
            planning_explanation = self.format_planning_explanation(cot_result["plan"])
            sections.append(planning_explanation)
        
        if sections:
            return "\n\n---\n\n".join(sections)
        else:
            return "Chain-of-thought process completed with no detailed information to report."
