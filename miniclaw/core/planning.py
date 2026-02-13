"""Action planning capabilities for MiniClaw."""

from typing import Any, Dict, List, Optional
from ..core.events import EventLog
from ..core.util import LOGGER


class ActionPlanner:
    """Manages creation and execution of action plans."""
    
    def __init__(self, event_log: EventLog) -> None:
        self._event_log = event_log
    
    def create_plan(self, goal: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create a detailed action plan."""
        self._event_log.add(
            "planning.plan_created",
            "Creating action plan",
            {"goal": goal[:100]}
        )
        
        plan = {
            "goal": goal,
            "steps": [],
            "dependencies": {},
            "resources": [],
            "timeline": {},
            "risk_mitigation": []
        }
        
        # Break down goal into steps
        steps = self._decompose_goal(goal, context)
        plan["steps"] = steps
        
        # Identify dependencies
        plan["dependencies"] = self._identify_dependencies(steps)
        
        # Assess required resources
        plan["resources"] = self._assess_resources(steps)
        
        # Identify risks and mitigation strategies
        plan["risk_mitigation"] = self._identify_risks(steps)
        
        # Create timeline
        plan["timeline"] = self._estimate_timeline(steps)
        
        return plan
    
    def _decompose_goal(self, goal: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Break down a goal into executable steps."""
        # This would typically involve prompting the LLM to decompose the goal
        # For now, we'll create a generic decomposition based on the goal content
        
        # Simple keyword-based step generation
        goal_lower = goal.lower()
        steps = []
        
        # Generic preparation step
        steps.append({
            "id": "step_1",
            "description": "Analyze requirements and gather necessary information",
            "expected_outcome": "Clear understanding of what needs to be accomplished",
            "success_criteria": "Requirements are documented and understood",
            "effort": "Low",
            "priority": "High"
        })
        
        # Action step based on goal content
        if "create" in goal_lower or "build" in goal_lower or "develop" in goal_lower:
            steps.append({
                "id": "step_2",
                "description": "Design and implement the solution",
                "expected_outcome": "Functional implementation based on requirements",
                "success_criteria": "Solution meets basic requirements",
                "effort": "High",
                "priority": "High"
            })
        elif "analyze" in goal_lower or "investigate" in goal_lower or "examine" in goal_lower:
            steps.append({
                "id": "step_2",
                "description": "Conduct detailed analysis",
                "expected_outcome": "Comprehensive understanding of the subject",
                "success_criteria": "Key insights are identified and documented",
                "effort": "Medium",
                "priority": "High"
            })
        elif "solve" in goal_lower or "fix" in goal_lower or "resolve" in goal_lower:
            steps.append({
                "id": "step_2",
                "description": "Implement solution approach",
                "expected_outcome": "Problem is addressed effectively",
                "success_criteria": "Problem symptoms are eliminated or reduced",
                "effort": "Medium",
                "priority": "High"
            })
        else:
            # Generic action step
            steps.append({
                "id": "step_2",
                "description": "Execute main approach to address the goal",
                "expected_outcome": "Progress toward goal completion",
                "success_criteria": "Key activities are completed",
                "effort": "Medium",
                "priority": "High"
            })
        
        # Validation step
        steps.append({
            "id": "step_3",
            "description": "Validate results and verify success criteria",
            "expected_outcome": "Confidence that the goal has been achieved",
            "success_criteria": "All success criteria are met or exceeded",
            "effort": "Low",
            "priority": "High"
        })
        
        # Documentation/learning step
        steps.append({
            "id": "step_4",
            "description": "Document process and lessons learned",
            "expected_outcome": "Knowledge capture for future reference",
            "success_criteria": "Key insights and process steps are documented",
            "effort": "Low",
            "priority": "Medium"
        })
        
        return steps
    
    def _identify_dependencies(self, steps: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Identify dependencies between steps."""
        # Simple sequential dependency for now
        dependencies = {}
        for i in range(1, len(steps)):
            step_id = steps[i]["id"]
            previous_step_id = steps[i-1]["id"]
            dependencies[step_id] = [previous_step_id]
        
        # If there are more than 3 steps, add some parallelism possibility
        if len(steps) > 3:
            # Step 4 (documentation) can start after step 2, doesn't need to wait for step 3
            if len(steps) > 3:
                step_4_id = steps[3]["id"]  # Fourth step (index 3)
                step_2_id = steps[1]["id"]  # Second step (index 1)
                dependencies[step_4_id] = [step_2_id]
        
        return dependencies
    
    def _assess_resources(self, steps: List[Dict[str, Any]]) -> List[str]:
        """Assess resources needed for plan execution."""
        # Would analyze steps to determine required resources
        # For now, return generic resources
        return [
            "Computing resources",
            "Internet access",
            "File system access",
            "Text processing capabilities"
        ]
    
    def _identify_risks(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify potential risks in the plan."""
        # Would analyze steps for potential failure points
        return [
            {
                "risk": "Misunderstanding of requirements",
                "likelihood": "Medium",
                "impact": "High",
                "mitigation": "Frequent validation and clarification"
            },
            {
                "risk": "Technical implementation challenges",
                "likelihood": "Medium",
                "impact": "Medium",
                "mitigation": "Break complex steps into smaller subtasks"
            },
            {
                "risk": "Time constraints",
                "likelihood": "Low",
                "impact": "Medium",
                "mitigation": "Regular progress checks and reprioritization"
            }
        ]
    
    def _estimate_timeline(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Estimate timeline for plan execution."""
        # Simple effort-based estimation
        total_effort = 0
        for step in steps:
            effort = step.get("effort", "Medium")
            if effort == "Low":
                total_effort += 1
            elif effort == "Medium":
                total_effort += 2
            elif effort == "High":
                total_effort += 3
        
        # Simple mapping of effort to time estimate
        if total_effort <= 2:
            duration = "30 minutes"
        elif total_effort <= 4:
            duration = "1-2 hours"
        elif total_effort <= 6:
            duration = "Half day"
        else:
            duration = "Full day or more"
        
        return {
            "estimated_duration": duration,
            "total_effort_units": total_effort,
            "milestones": [f"Complete {step.get('description', '')[:30]}..." for step in steps]
        }
    
    def format_plan_explanation(self, plan: Dict[str, Any]) -> str:
        """Format action plan into clear explanation."""
        if not plan:
            return "No plan information available."
        
        explanation = ["# Action Plan\n"]
        
        # Goal
        explanation.append(f"## Goal: {plan.get('goal', 'Unknown')}")
        explanation.append("")
        
        # Steps
        steps = plan.get("steps", [])
        if steps:
            explanation.append("## Execution Steps")
            for i, step in enumerate(steps, 1):
                explanation.append(f"{i}. **{step.get('description', 'Unknown step')}")
                explanation.append(f"   - Expected Outcome: {step.get('expected_outcome', 'N/A')}")
                explanation.append(f"   - Success Criteria: {step.get('success_criteria', 'N/A')}")
                explanation.append(f"   - Effort: {step.get('effort', 'N/A')}")
                explanation.append(f"   - Priority: {step.get('priority', 'N/A')}")
                explanation.append("")
        
        # Dependencies
        dependencies = plan.get("dependencies", {})
        if dependencies:
            explanation.append("## Dependencies")
            for step_id, deps in dependencies.items():
                if deps:
                    explanation.append(f"- {step_id} depends on: {', '.join(deps)}")
            explanation.append("")
        
        # Timeline
        timeline = plan.get("timeline", {})
        if timeline:
            explanation.append("## Timeline")
            explanation.append(f"- Estimated Duration: {timeline.get('estimated_duration', 'N/A')}")
            explanation.append(f"- Total Effort: {timeline.get('total_effort_units', 0)} units")
            explanation.append("")
        
        # Resources
        resources = plan.get("resources", [])
        if resources:
            explanation.append("## Required Resources")
            for resource in resources:
                explanation.append(f"- {resource}")
            explanation.append("")
        
        # Risks
        risks = plan.get("risk_mitigation", [])
        if risks:
            explanation.append("## Risk Mitigation")
            for risk_item in risks:
                explanation.append(f"- Risk: {risk_item.get('risk', 'Unknown')}")
                explanation.append(f"  - Likelihood: {risk_item.get('likelihood', 'N/A')}")
                explanation.append(f"  - Impact: {risk_item.get('impact', 'N/A')}")
                explanation.append(f"  - Mitigation: {risk_item.get('mitigation', 'N/A')}")
                explanation.append("")
        
        return "\n".join(explanation)
