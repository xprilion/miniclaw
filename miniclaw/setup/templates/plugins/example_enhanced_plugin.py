# name: Enhanced Example Plugin
# description: Demonstrates the enhanced plugin system with hooks and lifecycle management
# version: 1.0.0

"""
Enhanced example plugin for MiniClaw that demonstrates the new plugin system features.
"""

from typing import Any, Dict, List, Optional


def on_load(context) -> None:
    """Called when the plugin is loaded."""
    context.log_event("plugin.example.loaded", "Example plugin loaded")
    context.set_plugin_data("load_time", __import__("time").time())


def on_enable(context) -> None:
    """Called when the plugin is enabled."""
    context.log_event("plugin.example.enabled", "Example plugin enabled")
    context.set_plugin_data("enable_count", context.get_plugin_data("enable_count", 0) + 1)


def on_disable(context) -> None:
    """Called when the plugin is disabled."""
    context.log_event("plugin.example.disabled", "Example plugin disabled")


def on_unload(context) -> None:
    """Called when the plugin is unloaded."""
    context.log_event("plugin.example.unloaded", "Example plugin unloaded")


def on_pre_prompt(context, plugin_context) -> Optional[List[Dict[str, str]]]:
    """
    Called before the prompt is sent to the model.
    Can add additional messages to the prompt.
    """
    # Add a timestamp message
    import time
    timestamp_msg = {
        "role": "system",
        "content": f"[Plugin Notice] Current time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    }

    plugin_context.log_event(
        "plugin.example.pre_prompt",
        "Added timestamp to prompt",
        {"timestamp": time.strftime('%Y-%m-%d %H:%M:%S')}
    )

    return [timestamp_msg]


def on_post_response(context, plugin_context) -> Optional[Dict[str, Any]]:
    """
    Called after the model responds.
    Can modify the response or trigger additional actions.
    """
    response = context.get("response", "")

    # Count words in response
    word_count = len(response.split())

    plugin_context.log_event(
        "plugin.example.post_response",
        "Processed response",
        {"word_count": word_count}
    )

    # Add word count to context for other plugins
    plugin_context.set_plugin_data("last_response_word_count", word_count)

    return None


def on_message(context, plugin_context) -> Optional[Dict[str, Any]]:
    """
    Called when a new message is received.
    Can preprocess the message or trigger actions.
    """
    message = context.get("user_message", "")

    # Detect if message contains greeting
    greetings = ["hello", "hi", "hey", "greetings"]
    is_greeting = any(greeting in message.lower() for greeting in greetings)

    if is_greeting:
        plugin_context.log_event(
            "plugin.example.greeting_detected",
            "Greeting detected in message",
            {"message_preview": message[:50]}
        )

    return None


def on_tool_call(context, plugin_context) -> Optional[Dict[str, Any]]:
    """
    Called when a tool is about to be executed.
    Can modify tool arguments or prevent execution.
    """
    tool_name = context.get("tool", "")
    arguments = context.get("arguments", {})

    plugin_context.log_event(
        "plugin.example.tool_call",
        f"Tool {tool_name} called",
        {"argument_count": len(arguments)}
    )

    # Example: Add a custom header to fetch_url calls
    if tool_name == "fetch_url":
        if "headers" not in arguments:
            arguments["headers"] = {}
        arguments["headers"]["X-Plugin"] = "example-enhanced"

        return {"arguments": arguments}

    return None


def on_model_response(context, plugin_context) -> Optional[Dict[str, Any]]:
    """
    Called when a model response is received.
    Can analyze or modify the response.
    """
    response = context.get("response", "")

    # Simple sentiment detection
    positive_words = ["good", "great", "excellent", "amazing", "wonderful"]
    negative_words = ["bad", "terrible", "awful", "horrible", "disappointing"]

    positive_count = sum(1 for word in positive_words if word in response.lower())
    negative_count = sum(1 for word in negative_words if word in response.lower())

    sentiment = "neutral"
    if positive_count > negative_count:
        sentiment = "positive"
    elif negative_count > positive_count:
        sentiment = "negative"

    plugin_context.log_event(
        "plugin.example.sentiment_analyzed",
        f"Sentiment analyzed: {sentiment}",
        {"positive_words": positive_count, "negative_words": negative_count}
    )

    # Store sentiment for this response
    plugin_context.set_plugin_data("last_sentiment", sentiment)

    return None
