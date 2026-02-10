"""Plugin that formats responses appropriately for different channels."""

import re
from typing import Any, Dict

metadata = {
    "name": "Response Formatter",
    "description": (
        "Formats responses appropriately for different channels (Telegram, WhatsApp, Web, etc.). "
        "Removes markdown for chat channels and preserves it for web channels."
    ),
}


def _format_for_telegram(response: str) -> str:
    """Format response for Telegram - remove markdown and make more conversational."""
    # Remove markdown code blocks
    formatted = re.sub(r'```.*?```', '', response, flags=re.DOTALL)
    formatted = re.sub(r'`([^`]+)`', r'"\1"', formatted)  # Inline code
    formatted = re.sub(r'\*\*(.*?)\*\*', r'\1', formatted)  # Bold
    formatted = re.sub(r'\*(.*?)\*', r'\1', formatted)  # Italic
    formatted = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', formatted)  # Links

    # Remove tool call mentions that look like internal details
    formatted = re.sub(r'\[Tool Result.*?\]', '', formatted, flags=re.DOTALL)
    formatted = re.sub(r'\{"tool":.*?\}', '', formatted)

    # Remove other technical artifacts
    formatted = re.sub(r'\[Skill:.*?\]', '', formatted, flags=re.DOTALL)
    formatted = re.sub(r'\[Memory:.*?\]', '', formatted, flags=re.DOTALL)
    formatted = re.sub(r'Trace ID:.*?\n', '', formatted)
    formatted = re.sub(r'trace_id=.*?;', '', formatted)
    formatted = re.sub(r'trace-[0-9]+', '', formatted)

    # Clean up extra whitespace
    formatted = re.sub(r'\n\s*\n\s*\n', '\n\n', formatted)
    formatted = formatted.strip()

    # Make responses more conversational
    if formatted.startswith("MiniClaw") or formatted.startswith("I'm MiniClaw"):
        # Remove self-referential prefixes
        formatted = re.sub(r'^MiniClaw.*?:\s*', '', formatted)
        formatted = re.sub(r'^I\'?m MiniClaw.*?:\s*', '', formatted)

    # Add a more natural conversational tone
    if formatted and not formatted.endswith(('.', '!', '?')):
        # Add a period if it doesn't end with punctuation
        formatted = formatted.rstrip() + '.'

    return formatted


def _format_for_whatsapp(response: str) -> str:
    """Format response for WhatsApp - similar to Telegram but with simpler formatting."""
    return _format_for_telegram(response)


def _format_for_web(response: str) -> str:
    """Format response for web - preserve markdown for better presentation."""
    # Keep markdown for web, but clean up any tool call artifacts
    formatted = re.sub(r'\[Tool Result.*?\]', '', response, flags=re.DOTALL)
    formatted = re.sub(r'\{"tool":.*?\}', '', formatted)
    formatted = re.sub(r'\n\s*\n\s*\n', '\n\n', formatted)
    return formatted.strip()


def _make_conversational(response: str) -> str:
    """Make the response sound more conversational and less like a computer."""
    # Remove overly technical language
    formatted = response

    # Replace technical phrases with more natural ones
    replacements = {
        r'I have completed the following actions?:': 'I looked into this for you:',
        r'I will perform the following actions?:': 'Here\'s what I\'ll do:',
        r'The result (is|was):': 'Here\'s what I found:',
        r'I have (executed|run) the following.*?:': 'I checked the following:',
        r'According to.*?:': '',
        r'Based on.*?:': '',
        r'I\'?ve analyzed.*?:': 'Looking at this:',
        r'I\'?ve checked.*?:': 'I found that:',
        r'After reviewing.*?:': 'Here\'s what I discovered:',
    }

    for pattern, replacement in replacements.items():
        formatted = re.sub(pattern, replacement, formatted, flags=re.IGNORECASE)

    # Remove redundant phrases
    redundant_phrases = [
        r'I am MiniClaw.*?:',
        r'As MiniClaw.*?:',
        r'The requested action.*?:',
        r'Here is the result.*?:',
        r'Let me.*?:',
        r'Allow me to.*?:',
    ]

    for phrase in redundant_phrases:
        formatted = re.sub(phrase, '', formatted, flags=re.IGNORECASE)

    # Make responses sound more human
    human_phrases = {
        r'Furthermore,': 'Also,',
        r'Additionally,': 'Also,',
        r'Moreover,': 'Also,',
        r'However,': 'But,',
        r'Nevertheless,': 'But,',
        r'Consequently,': 'So,',
        r'Therefore,': 'So,',
    }

    for phrase, replacement in human_phrases.items():
        formatted = re.sub(phrase, replacement, formatted, flags=re.IGNORECASE)

    # Clean up extra spaces
    formatted = re.sub(r'\s+', ' ', formatted)
    formatted = re.sub(r'\n\s*\n', '\n\n', formatted)

    # Make sure sentences start with capital letters
    formatted = re.sub(r'(\.|\!|\?)\s+([a-z])', lambda m: m.group(1) + ' ' + m.group(2).upper(), formatted)

    return formatted.strip()


def pre_prompt(context: Dict[str, Any]) -> Dict[str, Any]:
    """Add information about the source channel to context."""
    source = context.get("source", "web")
    return {
        "extra_system": f"Output format: {source} channel. Adjust response format accordingly.",
    }


def post_response(context: Dict[str, Any]) -> Dict[str, Any]:
    """Format the response based on the source channel."""
    response = context.get("response", "")
    source = context.get("source", "web")

    if not response:
        return {}

    # Format based on channel
    if source in ["telegram", "whatsapp"]:
        formatted_response = _format_for_telegram(response) if source == "telegram" else _format_for_whatsapp(response)
        formatted_response = _make_conversational(formatted_response)
    elif source in ["web", "cli"]:
        formatted_response = _format_for_web(response)
    else:
        # Default to web formatting for unknown channels
        formatted_response = _format_for_web(response)

    # Update the context with the formatted response
    context["response"] = formatted_response

    return {
        "original_length": len(response),
        "formatted_length": len(formatted_response),
        "channel": source,
    }
