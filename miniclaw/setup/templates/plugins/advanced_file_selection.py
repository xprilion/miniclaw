"""Advanced plugin that implements chain of thought reasoning for file selection using the skill registry."""

metadata = {
    "name": "Advanced File Selection Chain of Thought",
    "description": "Analyzes user requests and determines which files (skills, memory, jobs) should be used based on a chain of thought approach, leveraging the skill registry's matching capabilities.",
}

# Global reference to the skill registry (to be set by the agent)
skill_registry = None

def set_skill_registry(registry):
    """Set the skill registry reference."""
    global skill_registry
    skill_registry = registry

def pre_prompt(context):
    """
    Analyze the user message and determine which files should be used.
    This function adds contextual information about file selection to the prompt.
    """
    user_message = context.get("user_message", "")
    trace_id = context.get("trace_id", "unknown")
    
    # Use the skill registry to score skills against the user message
    file_analysis = _analyze_files_with_skills(user_message)
    
    # Create a contextual message about file selection
    cot_message = (
        f"[Chain of Thought - File Selection Analysis]\n"
        f"Trace ID: {trace_id}\n"
        f"Primary recommended skill: {file_analysis['primary_skill']}\n"
        f"Secondary skills: {', '.join(file_analysis['secondary_skills'])}\n"
        f"Memory files to consider: {', '.join(file_analysis['memory_files'])}\n"
        f"Reasoning: {file_analysis['reasoning']}\n"
        f"Skill scores: {file_analysis['skill_scores']}\n"
    )
    
    return {
        "extra_system": cot_message,
    }

def post_response(context):
    """
    Post-process the response to validate file usage.
    """
    response = context.get("response", "")
    trace_id = context.get("trace_id", "unknown")
    
    return {
        "response_char_count": len(response),
        "trace_id": trace_id,
        "file_selection_validation": "processed"
    }

def _analyze_files_with_skills(user_message):
    """
    Analyze the user message using the skill registry to determine which files are needed.
    Returns a dictionary with file selection recommendations.
    """
    global skill_registry
    
    # Default values if skill registry is not available
    if skill_registry is None:
        return {
            "primary_skill": "none",
            "secondary_skills": [],
            "memory_files": ["soul.md", "user.md", "project.md", "journal.md"],
            "reasoning": "Skill registry not available, using default memory files",
            "skill_scores": {}
        }
    
    # Get all available skills
    all_skills = skill_registry.list()
    skill_scores = {}
    
    # Score each skill against the user message
    for skill in all_skills:
        skill_id = skill.get("id", "")
        content = skill.get("content", "")
        
        # Simple scoring based on keyword matching
        score = _score_skill_relevance(content, user_message)
        skill_scores[skill_id] = score
    
    # Sort skills by score
    sorted_skills = sorted(skill_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Select primary and secondary skills
    primary_skill = sorted_skills[0][0] if sorted_skills else "general_reasoning"
    secondary_skills = [skill[0] for skill in sorted_skills[1:3]] if len(sorted_skills) > 1 else []
    
    # Always include core memory files
    memory_files = ["soul.md", "user.md", "project.md"]
    
    # Include journal for context awareness
    memory_files.append("journal.md")
    
    # Create reasoning text
    reasoning = f"Selected '{primary_skill}' as primary skill based on relevance scoring"
    if secondary_skills:
        reasoning += f" with secondary skills: {', '.join(secondary_skills)}"
    
    return {
        "primary_skill": primary_skill,
        "secondary_skills": secondary_skills,
        "memory_files": memory_files,
        "reasoning": reasoning,
        "skill_scores": skill_scores
    }

def _score_skill_relevance(skill_content, user_message):
    """
    Simple relevance scoring based on keyword matching.
    """
    skill_lower = skill_content.lower()
    message_lower = user_message.lower()
    
    # Count matching words
    skill_words = set(skill_lower.split())
    message_words = set(message_lower.split())
    
    # Also check for keyword lines in the skill
    keyword_lines = [line for line in skill_content.split('\n') if line.lower().startswith('keywords:')]
    keyword_score = 0
    
    if keyword_lines:
        keywords = keyword_lines[0].split(':')[1].strip().split(',')
        keywords = [kw.strip().lower() for kw in keywords]
        
        # Check if any keywords are in the user message
        for keyword in keywords:
            if keyword in message_lower:
                keyword_score += 3  # Higher weight for keyword matches
    
    # Word overlap score
    overlap = len(skill_words.intersection(message_words))
    
    # Return combined score
    return overlap + keyword_score