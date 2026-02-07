"""Simple plugin that injects trace metadata into each prompt."""

metadata = {
    "name": "Trace Tag",
    "description": "Adds a trace id and source marker to the system context for easier auditing.",
}


def pre_prompt(context):
    trace_id = context.get("trace_id", "unknown")
    source = context.get("source", "unknown")
    return {
        "extra_system": f"Transparency trace_id={trace_id}; source={source}. Keep reasoning auditable.",
    }


def post_response(context):
    response = context.get("response", "")
    return {
        "response_char_count": len(response),
        "trace_id": context.get("trace_id", "unknown"),
    }
