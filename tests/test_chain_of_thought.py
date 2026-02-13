"""Tests for enhanced chain-of-thought reasoning capabilities."""

import unittest
from unittest.mock import Mock, patch

from miniclaw.core.reasoning import ReasoningEngine
from miniclaw.core.decisions import DecisionFramework
from miniclaw.core.planning import ActionPlanner
from miniclaw.core.communication import CommunicationManager


class TestReasoningEngine(unittest.TestCase):
    def setUp(self):
        self.event_log = Mock()
        self.reasoning_engine = ReasoningEngine(self.event_log)
    
    def test_should_engage_reasoning_with_indicators(self):
        # Test that reasoning is engaged for queries with reasoning indicators
        query = "Analyze the effectiveness of our marketing strategy"
        selected_skills = []
        
        should_engage = self.reasoning_engine.should_engage_reasoning(query, selected_skills)
        self.assertTrue(should_engage)
    
    def test_should_engage_reasoning_with_skills(self):
        # Test that reasoning is engaged when reasoning skills are selected
        query = "What is 2+2?"
        selected_skills = [{"id": "systematic_analysis"}]
        
        should_engage = self.reasoning_engine.should_engage_reasoning(query, selected_skills)
        self.assertTrue(should_engage)
    
    def test_problem_analysis(self):
        # Test that problem analysis works correctly
        query = "How can we improve our customer satisfaction?"
        context = {}
        
        analysis = self.reasoning_engine.analyze_problem(query, context)
        self.assertIn("goal", analysis)
        self.assertIn("constraints", analysis)
        self.assertIn("success_criteria", analysis)
        self.assertIn("stakeholders", analysis)
    
    def test_approach_exploration(self):
        # Test that approach exploration generates valid options
        problem_analysis = {
            "goal": "Test goal",
            "constraints": [],
            "success_criteria": [],
            "stakeholders": []
        }
        
        approaches = self.reasoning_engine.explore_approaches(problem_analysis)
        self.assertGreater(len(approaches), 0)
        for approach in approaches:
            self.assertIn("id", approach)
            self.assertIn("name", approach)
            self.assertIn("description", approach)
    
    def test_format_reasoning_output(self):
        # Test that reasoning output formatting works
        reasoning_result = {
            "analysis": {
                "goal": "Test goal",
                "constraints": ["Constraint 1"],
                "success_criteria": ["Criterion 1"],
                "stakeholders": ["Stakeholder 1"]
            },
            "approaches": [
                {
                    "name": "Approach 1",
                    "description": "First approach",
                    "pros": ["Pro 1"],
                    "cons": ["Con 1"],
                    "effort": "Low",
                    "risk": "Low"
                }
            ],
            "decision": {
                "selected": {"name": "Approach 1"},
                "reasoning": "Best approach",
                "confidence": 0.8
            },
            "plan": {
                "goal": "Execute approach",
                "steps": [
                    {
                        "description": "Step 1",
                        "expected_outcome": "Outcome 1",
                        "success_criteria": "Criteria 1"
                    }
                ]
            }
        }
        
        output = self.reasoning_engine.format_reasoning_output(reasoning_result)
        self.assertIn("# My Reasoning Process", output)
        self.assertIn("## Problem Analysis", output)
        self.assertIn("## Approaches Considered", output)
        self.assertIn("## Decision", output)
        self.assertIn("## Execution Plan", output)


class TestDecisionFramework(unittest.TestCase):
    def setUp(self):
        self.event_log = Mock()
        self.decision_framework = DecisionFramework(self.event_log)
    
    def test_option_scoring(self):
        options = [
            {"name": "Option A", "evaluation": {"cost": 0.8, "speed": 0.6}},
            {"name": "Option B", "evaluation": {"cost": 0.4, "speed": 0.9}}
        ]
        criteria = [
            {"name": "cost", "weight": 0.6},
            {"name": "speed", "weight": 0.4}
        ]
        
        ranked = self.decision_framework.evaluate_options(options, criteria)
        # Verify ranking is correct based on weighted scoring
        self.assertEqual(len(ranked), 2)
        # Option A: (0.8 * 0.6 + 0.6 * 0.4) / (0.6 + 0.4) = (0.48 + 0.24) / 1.0 = 0.72
        # Option B: (0.4 * 0.6 + 0.9 * 0.4) / (0.6 + 0.4) = (0.24 + 0.36) / 1.0 = 0.60
        self.assertEqual(ranked[0]["name"], "Option A")  # Higher weighted score
        self.assertEqual(ranked[1]["name"], "Option B")
    
    def test_decision_with_criteria(self):
        options = [
            {"id": "opt1", "name": "Option 1", "evaluation": {"effectiveness": 0.9, "cost": 0.7}},
            {"id": "opt2", "name": "Option 2", "evaluation": {"effectiveness": 0.6, "cost": 0.9}}
        ]
        criteria = [
            {"name": "effectiveness", "weight": 0.7},
            {"name": "cost", "weight": 0.3}
        ]
        
        result = self.decision_framework.make_decision_with_criteria(options, criteria)
        self.assertIsNotNone(result["selected_option"])
        self.assertGreater(result["confidence"], 0.5)
        self.assertIn("reasoning", result)
        self.assertIn("scored_options", result)
    
    def test_format_decision_explanation(self):
        decision_result = {
            "selected_option": {"name": "Best Option"},
            "confidence": 0.85,
            "reasoning": "This option scored highest",
            "scored_options": [
                {"name": "Best Option", "score": 8.5},
                {"name": "Second Best", "score": 7.2}
            ]
        }
        
        explanation = self.decision_framework.format_decision_explanation(decision_result)
        self.assertIn("# Decision Analysis", explanation)
        self.assertIn("## Selected Option", explanation)
        self.assertIn("## All Options Ranked", explanation)


class TestActionPlanner(unittest.TestCase):
    def setUp(self):
        self.event_log = Mock()
        self.action_planner = ActionPlanner(self.event_log)
    
    def test_plan_creation(self):
        plan = self.action_planner.create_plan("Create a marketing strategy", {})
        self.assertIn("goal", plan)
        self.assertIn("steps", plan)
        self.assertIn("dependencies", plan)
        self.assertIn("resources", plan)
        self.assertIn("timeline", plan)
        self.assertIn("risk_mitigation", plan)
        
        # Check that steps were created
        self.assertGreater(len(plan["steps"]), 0)
        
        # Check that timeline was estimated
        self.assertIn("estimated_duration", plan["timeline"])
    
    def test_format_plan_explanation(self):
        plan = {
            "goal": "Test plan",
            "steps": [
                {
                    "description": "Step 1",
                    "expected_outcome": "Outcome 1",
                    "success_criteria": "Criteria 1",
                    "effort": "Low",
                    "priority": "High"
                }
            ],
            "dependencies": {},
            "timeline": {
                "estimated_duration": "1 hour"
            },
            "resources": ["Resource 1"],
            "risk_mitigation": [
                {
                    "risk": "Risk 1",
                    "likelihood": "Medium",
                    "impact": "High",
                    "mitigation": "Mitigation 1"
                }
            ]
        }
        
        explanation = self.action_planner.format_plan_explanation(plan)
        self.assertIn("# Action Plan", explanation)
        self.assertIn("## Goal", explanation)
        self.assertIn("## Execution Steps", explanation)
        self.assertIn("## Timeline", explanation)
        self.assertIn("## Required Resources", explanation)
        self.assertIn("## Risk Mitigation", explanation)


class TestCommunicationManager(unittest.TestCase):
    def setUp(self):
        self.event_log = Mock()
        self.communication_manager = CommunicationManager(self.event_log)
    
    def test_reasoning_explanation(self):
        reasoning_trace = {
            "analysis": {
                "goal": "Test goal", 
                "constraints": ["Constraint 1"],
                "success_criteria": ["Criterion 1"],
                "stakeholders": ["Stakeholder 1"]
            },
            "approaches": [
                {
                    "name": "Approach 1", 
                    "description": "First approach", 
                    "pros": ["Pro 1"],
                    "cons": ["Con 1"],
                    "effort": "Low",
                    "risk": "Low"
                }
            ],
            "decision": {
                "selected": {"name": "Approach 1"}, 
                "reasoning": "Best approach",
                "confidence": 0.8
            },
            "plan": {
                "goal": "Execute approach",
                "steps": [
                    {
                        "description": "Step 1",
                        "expected_outcome": "Outcome 1", 
                        "success_criteria": "Criteria 1"
                    }
                ]
            }
        }
        
        explanation = self.communication_manager.format_reasoning_explanation(reasoning_trace)
        self.assertIn("# My Reasoning Process", explanation)
        self.assertIn("## Problem Analysis", explanation)
        self.assertIn("## Approaches Considered", explanation)
        self.assertIn("## Decision", explanation)
        self.assertIn("## Execution Plan", explanation)
    
    def test_comprehensive_explanation(self):
        cot_result = {
            "reasoning": {
                "analysis": {"goal": "Test goal"},
                "approaches": [{"name": "Approach 1"}],
                "decision": {"selected": {"name": "Approach 1"}},
                "plan": {"goal": "Execute approach"}
            },
            "decision": {
                "selected_option": {"name": "Approach 1"}
            },
            "plan": {
                "goal": "Execute approach"
            }
        }
        
        explanation = self.communication_manager.create_comprehensive_explanation(cot_result)
        self.assertIn("# My Reasoning Process", explanation)
        # Check that multiple sections are present
        self.assertIn("# Decision-Making Process", explanation)


if __name__ == '__main__':
    unittest.main()