#!/usr/bin/env python3
"""
Demo script for MiniClaw chain-of-thought enhancement framework.
This script demonstrates the new reasoning capabilities.
"""

import json
import sys
from pathlib import Path

# Add the miniclaw package to the path
sys.path.insert(0, str(Path(__file__).parent))

from miniclaw.core.events import EventLog
from miniclaw.core.reasoning import ReasoningEngine
from miniclaw.core.decisions import DecisionFramework
from miniclaw.core.planning import ActionPlanner
from miniclaw.core.communication import CommunicationManager


def demo_chain_of_thought():
    """Demonstrate the chain-of-thought enhancement framework."""
    print("=== MiniClaw Chain-of-Thought Enhancement Demo ===\n")
    
    # Initialize components
    event_log = EventLog(100)
    reasoning_engine = ReasoningEngine(event_log)
    decision_framework = DecisionFramework(event_log)
    action_planner = ActionPlanner(event_log)
    communication_manager = CommunicationManager(event_log)
    
    # Example query that should trigger reasoning
    query = "How can we improve our customer onboarding process to reduce churn in the first 30 days?"
    
    print(f"Query: {query}\n")
    
    # 1. Problem Analysis
    print("1. Problem Analysis")
    context = {"source": "demo"}
    analysis = reasoning_engine.analyze_problem(query, context)
    print(f"   Goal: {analysis['goal']}")
    print(f"   Constraints: {', '.join(analysis['constraints'])}")
    print(f"   Success Criteria: {', '.join(analysis['success_criteria'])}")
    print(f"   Stakeholders: {', '.join(analysis['stakeholders'])}")
    print()
    
    # 2. Approach Exploration
    print("2. Approach Exploration")
    approaches = reasoning_engine.explore_approaches(analysis)
    for i, approach in enumerate(approaches, 1):
        print(f"   {i}. {approach['name']}")
        print(f"      Description: {approach['description']}")
        print(f"      Effort: {approach['effort']}, Risk: {approach['risk']}")
    print()
    
    # 3. Decision Making
    print("3. Decision Making")
    # Add evaluation scores to approaches
    for approach in approaches:
        approach["evaluation"] = {
            "effectiveness": 0.8 if "Direct" in approach["name"] else 0.7,
            "effort": 0.6 if approach["effort"] == "Low" else 0.8,
            "risk": 0.3 if approach["risk"] == "Low" else 0.6
        }
    
    criteria = [
        {"name": "effectiveness", "weight": 0.5},
        {"name": "effort", "weight": 0.3},
        {"name": "risk", "weight": 0.2}
    ]
    
    decision_result = decision_framework.make_decision_with_criteria(approaches, criteria)
    selected = decision_result["selected_option"]
    print(f"   Selected: {selected['name']}")
    print(f"   Confidence: {decision_result['confidence']:.1%}")
    print(f"   Reasoning: {decision_result['reasoning']}")
    print()
    
    # 4. Action Planning
    print("4. Action Planning")
    plan_context = {"approach": selected, "context": context}
    plan = action_planner.create_plan(selected["name"], plan_context)
    print(f"   Goal: {plan['goal']}")
    print(f"   Estimated Duration: {plan['timeline']['estimated_duration']}")
    print("   Steps:")
    for i, step in enumerate(plan["steps"], 1):
        print(f"     {i}. {step['description']}")
    print()
    
    # 5. Communication
    print("5. Communication")
    cot_result = {
        "analysis": analysis,
        "approaches": approaches,
        "decision": decision_result,
        "plan": plan
    }
    
    explanation = communication_manager.create_comprehensive_explanation(cot_result)
    print("   Formatted Explanation:")
    print("   " + "="*50)
    # Print first few lines of the explanation
    lines = explanation.split("\n")
    for line in lines[:15]:
        print(f"   {line}")
    if len(lines) > 15:
        print("   ... (truncated for demo)")
    print("   " + "="*50)
    print()
    
    # Show events logged during the process
    print("6. Event Log Summary")
    events = event_log.list_since(limit=10)
    for event in events:
        print(f"   - {event['type']}: {event['message']}")
    print()
    
    print("=== Demo Complete ===")


if __name__ == "__main__":
    demo_chain_of_thought()