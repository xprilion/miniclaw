"""Ollama, OpenAI-compatible, LiteLLM, and OpenRouter chat API client."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
import ssl
from typing import Any, Dict, List, Optional

import openai
from openai import OpenAI

from .events import EventLog
from .util import LOGGER

class ModelProviderClient:
    def __init__(self, event_log: EventLog) -> None:
        self._event_log = event_log

    def _request_json(
        self,
        url: str,
        method: str,
        payload: Optional[Dict[str, Any]],
        timeout_seconds: int,
        verify_tls: bool,
        redact_url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        request_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        if headers:
            request_headers.update(headers)
        request = urllib.request.Request(url=url, data=data, method=method, headers=request_headers)

        ssl_context = None
        if url.startswith("https://") and not verify_tls:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        target = redact_url or url
        self._event_log.add(
            "network.request",
            "Outgoing HTTP request",
            {
                "method": method,
                "url": target,
                "payload": payload,
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds, context=ssl_context) as response:
                body = response.read().decode("utf-8", errors="replace")
                self._event_log.add(
                    "network.response",
                    "Incoming HTTP response",
                    {
                        "url": target,
                        "status": response.status,
                        "body_preview": body[:500] if body else "",  # Log only first 500 chars
                        "content_type": response.headers.get("Content-Type", ""),
                    },
                )
                # Try to parse JSON, but handle cases where it's not JSON
                if body.strip():
                    content_type = response.headers.get("Content-Type", "").lower()
                    if "application/json" in content_type or content_type.startswith("application/"):
                        try:
                            parsed = json.loads(body)
                            if isinstance(parsed, dict):
                                return parsed
                            return {"data": parsed}
                        except json.JSONDecodeError:
                            # If JSON parsing fails, return the raw body
                            return {"ok": False, "error": "Invalid JSON response", "raw_body": body}
                    else:
                        # Non-JSON response
                        return {"ok": False, "error": "Non-JSON response", "content_type": content_type, "raw_body": body}
                else:
                    return {}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            self._event_log.add(
                "network.error",
                "HTTP request failed",
                {
                    "url": target,
                    "status": exc.code,
                    "body_preview": body[:500] if body else "",  # Log only first 500 chars
                    "content_type": exc.headers.get("Content-Type", "") if exc.headers else "",
                },
            )
            # Try to parse error response as JSON
            if body.strip():
                try:
                    error_parsed = json.loads(body)
                    raise RuntimeError(f"HTTP {exc.code} from {target}: {error_parsed}") from exc
                except json.JSONDecodeError:
                    raise RuntimeError(f"HTTP {exc.code} from {target}: {body}") from exc
            else:
                raise RuntimeError(f"HTTP {exc.code} from {target}: (empty body)") from exc
        except urllib.error.URLError as exc:
            self._event_log.add(
                "network.error",
                "Network request failed",
                {
                    "url": target,
                    "error": str(exc),
                },
            )
            raise RuntimeError(f"Network error to {target}: {exc}") from exc

    def list_models(self, provider: Dict[str, Any]) -> List[str]:
        provider_type = str(provider.get("type") or "ollama").strip().lower()
        base_url = str(provider.get("base_url") or "").rstrip("/")
        timeout_seconds = int(provider.get("timeout_seconds") or 300)
        verify_tls = bool(provider.get("verify_tls", True))
        provider_id = str(provider.get("id") or "")
        model = str(provider.get("model") or "").strip()

        if not base_url:
            return [model] if model else []

        if provider_type == "openai_compatible" or provider_type == "litellm" or provider_type == "openrouter":
            LOGGER.info("Listing models from %s provider id=%s url=%s", provider_type, provider_id, base_url)
            headers = {"Accept": "application/json"}
            api_key = str(provider.get("api_key") or "").strip()
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            # For OpenRouter, we don't actually list models as there are too many
            if provider_type == "openrouter":
                if model:
                    return [model]
                return []
            response = self._request_json(
                url=f"{base_url}/models",
                method="GET",
                payload=None,
                timeout_seconds=timeout_seconds,
                verify_tls=verify_tls,
                headers=headers,
            )
            models = []
            for item in response.get("data", []):
                if not isinstance(item, dict):
                    continue
                model_id = str(item.get("id") or "").strip()
                if model_id:
                    models.append(model_id)
            if not models and model:
                models = [model]
            self._event_log.add(
                "provider.models",
                "Fetched model list from provider",
                {
                    "provider_id": provider_id,
                    "provider_type": provider_type,
                    "count": len(models),
                    "models": models,
                },
            )
            return models

        LOGGER.info("Listing Ollama models from %s", base_url)
        response = self._request_json(
            url=f"{base_url}/api/tags",
            method="GET",
            payload=None,
            timeout_seconds=timeout_seconds,
            verify_tls=verify_tls,
        )
        models = [
            str(item.get("name"))
            for item in response.get("models", [])
            if isinstance(item, dict) and item.get("name")
        ]
        if not models and model:
            models = [model]
        self._event_log.add(
            "provider.models",
            "Fetched model list from provider",
            {
                "provider_id": provider_id,
                "provider_type": "ollama",
                "count": len(models),
                "models": models,
            },
        )
        return models

    def _messages_to_generate_prompt(self, messages: List[Dict[str, str]]) -> str:
        sections: List[str] = []
        for message in messages:
            role = str(message.get("role") or "user").strip().upper()
            content = str(message.get("content") or "").strip()
            if not content:
                continue
            sections.append(f"{role}:\n{content}")
        sections.append("ASSISTANT:")
        return "\n\n".join(sections)

    def _chat_ollama(
        self,
        provider: Dict[str, Any],
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        base_url = str(provider.get("base_url") or "").rstrip("/")
        model = str(provider.get("model") or "gpt-oss:20b")
        timeout_seconds = int(provider.get("timeout_seconds") or 300)
        verify_tls = bool(provider.get("verify_tls", True))
        temperature = float(provider.get("temperature") or 0.2)

        LOGGER.info("Sending Ollama chat request provider=%s model=%s url=%s", provider.get("id"), model, base_url)
        chat_payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if tools:
            chat_payload["tools"] = tools
        try:
            raw_response = self._request_json(
                url=f"{base_url}/api/chat",
                method="POST",
                payload=chat_payload,
                timeout_seconds=timeout_seconds,
                verify_tls=verify_tls,
            )
            message = raw_response.get("message") or {}
            content = str((message.get("content")) or "").strip()
            if not content and isinstance(message.get("parts"), list):
                for part in message.get("parts", []):
                    if isinstance(part, dict) and part.get("text"):
                        content = str(part.get("text") or "").strip()
                        break
            if not content:
                content = str(raw_response.get("content") or "").strip()
            usage = {
                "prompt_tokens": int(raw_response.get("prompt_eval_count") or 0),
                "completion_tokens": int(raw_response.get("eval_count") or 0),
            }
            usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
            out_message: Dict[str, Any] = {"role": "assistant", "content": content}
            tool_calls = message.get("tool_calls")
            if isinstance(tool_calls, list) and tool_calls:
                out_message["tool_calls"] = tool_calls
            return {
                "provider_id": str(provider.get("id") or ""),
                "provider_type": "ollama",
                "model": model,
                "message": out_message,
                "usage": usage,
                "raw_response": raw_response,
            }
        except RuntimeError as exc:
            error_text = str(exc)
            # gpt-oss models can emit plain-text tool traces that fail /api/chat parsing.
            if "error parsing tool call" not in error_text.lower():
                raise
            self._event_log.add(
                "provider.fallback",
                "Falling back from Ollama /api/chat to /api/generate",
                {
                    "provider_id": str(provider.get("id") or ""),
                    "model": model,
                    "reason": error_text,
                },
            )
            LOGGER.warning("Ollama /api/chat failed; fallback to /api/generate provider=%s model=%s", provider.get("id"), model)
            generate_payload = {
                "model": model,
                "prompt": self._messages_to_generate_prompt(messages),
                "stream": False,
                "options": {"temperature": temperature},
            }
            generate_response = self._request_json(
                url=f"{base_url}/api/generate",
                method="POST",
                payload=generate_payload,
                timeout_seconds=timeout_seconds,
                verify_tls=verify_tls,
            )
            usage = {
                "prompt_tokens": int(generate_response.get("prompt_eval_count") or 0),
                "completion_tokens": int(generate_response.get("eval_count") or 0),
            }
            usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
            return {
                "provider_id": str(provider.get("id") or ""),
                "provider_type": "ollama",
                "model": model,
                "message": {
                    "role": "assistant",
                    "content": str(generate_response.get("response") or "").strip(),
                },
                "usage": usage,
                "raw_response": {
                    "fallback": "generate",
                    "generate": generate_response,
                },
            }

    def _chat_openai_compatible(self, provider: Dict[str, Any], messages: List[Dict[str, str]]) -> Dict[str, Any]:
        base_url = str(provider.get("base_url") or "").rstrip("/")
        model = str(provider.get("model") or "gpt-4o-mini")
        timeout_seconds = int(provider.get("timeout_seconds") or 300)
        temperature = float(provider.get("temperature") or 0.2)
        api_key = str(provider.get("api_key") or "").strip()
        
        LOGGER.info(
            "Sending OpenAI-compatible chat request provider=%s model=%s url=%s",
            provider.get("id"),
            model,
            base_url,
        )
        
        # Use the official OpenAI client which handles all the complexities
        client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout_seconds,
        )
        
        try:
            # Log the request
            self._event_log.add(
                "network.request",
                "Outgoing OpenAI-compatible request",
                {
                    "url": base_url,
                    "model": model,
                    "messages_count": len(messages),
                },
            )
            
            # Make the request using the official client
            response = client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore
                temperature=temperature,
                stream=False,
            )
            
            # Log the response
            self._event_log.add(
                "network.response",
                "Incoming OpenAI-compatible response",
                {
                    "model": model,
                    "choices_count": len(response.choices) if response.choices else 0,
                },
            )
            
            # Extract content from the response
            content = ""
            if response.choices and len(response.choices) > 0:
                choice = response.choices[0]
                if choice.message and choice.message.content:
                    content = str(choice.message.content).strip()
            
            # Extract usage information
            usage = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }
            if response.usage:
                usage["prompt_tokens"] = getattr(response.usage, "prompt_tokens", 0) or 0
                usage["completion_tokens"] = getattr(response.usage, "completion_tokens", 0) or 0
                usage["total_tokens"] = getattr(response.usage, "total_tokens", 0) or 0
            
            return {
                "provider_id": str(provider.get("id") or ""),
                "provider_type": "openai_compatible",
                "model": model,
                "message": {"role": "assistant", "content": content},
                "usage": usage,
                "raw_response": response.model_dump() if hasattr(response, 'model_dump') else response.dict(),
            }
            
        except openai.APIError as e:
            error_msg = f"OpenAI API error: {str(e)}"
            self._event_log.add(
                "network.error",
                "OpenAI-compatible request failed",
                {
                    "url": base_url,
                    "model": model,
                    "error": error_msg,
                },
            )
            raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self._event_log.add(
                "network.error",
                "OpenAI-compatible request failed",
                {
                    "url": base_url,
                    "model": model,
                    "error": error_msg,
                },
            )
            raise RuntimeError(error_msg) from e

    def _chat_litellm(self, provider: Dict[str, Any], messages: List[Dict[str, str]]) -> Dict[str, Any]:
        base_url = str(provider.get("base_url") or "http://localhost:4000").rstrip("/")
        model = str(provider.get("model") or "gpt-4o-mini")
        timeout_seconds = int(provider.get("timeout_seconds") or 300)
        verify_tls = bool(provider.get("verify_tls", True))
        temperature = float(provider.get("temperature") or 0.2)
        api_key = str(provider.get("api_key") or "").strip()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        LOGGER.info(
            "Sending LiteLLM chat request provider=%s model=%s url=%s",
            provider.get("id"),
            model,
            base_url,
        )
        raw_response = self._request_json(
            url=f"{base_url}/chat/completions",
            method="POST",
            payload=payload,
            timeout_seconds=timeout_seconds,
            verify_tls=verify_tls,
            headers=headers,
        )

        content = ""
        choices = raw_response.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0] if isinstance(choices[0], dict) else {}
            message = first.get("message") if isinstance(first, dict) else {}
            if isinstance(message, dict):
                content = str(message.get("content") or "").strip()

        usage_raw = raw_response.get("usage") if isinstance(raw_response, dict) else {}
        if not isinstance(usage_raw, dict):
            usage_raw = {}
        usage = {
            "prompt_tokens": int(usage_raw.get("prompt_tokens") or 0),
            "completion_tokens": int(usage_raw.get("completion_tokens") or 0),
        }
        usage["total_tokens"] = int(usage_raw.get("total_tokens") or (usage["prompt_tokens"] + usage["completion_tokens"]))
        return {
            "provider_id": str(provider.get("id") or ""),
            "provider_type": "litellm",
            "model": model,
            "message": {"role": "assistant", "content": content},
            "usage": usage,
            "raw_response": raw_response,
        }

    def _chat_openrouter(self, provider: Dict[str, Any], messages: List[Dict[str, str]]) -> Dict[str, Any]:
        base_url = str(provider.get("base_url") or "https://openrouter.ai/api/v1").rstrip("/")
        model = str(provider.get("model") or "openai/gpt-4o-mini")
        timeout_seconds = int(provider.get("timeout_seconds") or 300)
        verify_tls = bool(provider.get("verify_tls", True))
        temperature = float(provider.get("temperature") or 0.2)
        api_key = str(provider.get("api_key") or "").strip()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        # Add OpenRouter specific headers
        headers["HTTP-Referer"] = "https://miniclaw.ai"
        headers["X-Title"] = "MiniClaw"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        LOGGER.info(
            "Sending OpenRouter chat request provider=%s model=%s url=%s",
            provider.get("id"),
            model,
            base_url,
        )
        raw_response = self._request_json(
            url=f"{base_url}/chat/completions",
            method="POST",
            payload=payload,
            timeout_seconds=timeout_seconds,
            verify_tls=verify_tls,
            headers=headers,
        )

        content = ""
        choices = raw_response.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0] if isinstance(choices[0], dict) else {}
            message = first.get("message") if isinstance(first, dict) else {}
            if isinstance(message, dict):
                content = str(message.get("content") or "").strip()

        usage_raw = raw_response.get("usage") if isinstance(raw_response, dict) else {}
        if not isinstance(usage_raw, dict):
            usage_raw = {}
        usage = {
            "prompt_tokens": int(usage_raw.get("prompt_tokens") or 0),
            "completion_tokens": int(usage_raw.get("completion_tokens") or 0),
        }
        usage["total_tokens"] = int(usage_raw.get("total_tokens") or (usage["prompt_tokens"] + usage["completion_tokens"]))
        return {
            "provider_id": str(provider.get("id") or ""),
            "provider_type": "openrouter",
            "model": model,
            "message": {"role": "assistant", "content": content},
            "usage": usage,
            "raw_response": raw_response,
        }

    def chat(
        self,
        provider: Dict[str, Any],
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        provider_type = str(provider.get("type") or "ollama").strip().lower()
        if provider_type == "openai_compatible":
            return self._chat_openai_compatible(provider, messages)
        elif provider_type == "litellm":
            return self._chat_litellm(provider, messages)
        elif provider_type == "openrouter":
            return self._chat_openrouter(provider, messages)
        return self._chat_ollama(provider, messages, tools=tools)