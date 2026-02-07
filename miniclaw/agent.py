"""Main agent: skills, memory, tools, model loop."""
from __future__ import annotations

import copy
import json
import threading
import time
import traceback
from collections import deque
from typing import Any, Callable, Dict, List, Optional

from .config import ConfigStore
from .events import EventLog, UsageTracker
from .memory_store import MemoryStore
from .model_client import ModelProviderClient
from .plugins import PluginRegistry
from .skills import SkillRegistry
from .tools import ToolRunner
from .util import LOGGER, truncate_text, utc_now

class MiniClawAgent:
    def __init__(
        self,
        config_store: ConfigStore,
        event_log: EventLog,
        skill_registry: SkillRegistry,
        plugin_registry: PluginRegistry,
        model_client: ModelProviderClient,
        usage_tracker: UsageTracker,
        memory_store: MemoryStore,
        tool_runner: ToolRunner,
    ) -> None:
        self._config_store = config_store
        self._event_log = event_log
        self._skill_registry = skill_registry
        self._plugin_registry = plugin_registry
        self._model_client = model_client
        self._usage_tracker = usage_tracker
        self._memory_store = memory_store
        self._tool_runner = tool_runner
        self._history: deque[Dict[str, Any]] = deque(maxlen=400)
        self._chat_lock = threading.Lock()
        
        # Set the skill registry reference in the advanced file selection plugin if it exists
        try:
            # Try to set the skill registry in the advanced_file_selection plugin
            for plugin_info in self._plugin_registry.list():
                if plugin_info["id"] == "advanced_file_selection":
                    module = plugin_info.get("_module")
                    if module and hasattr(module, "set_skill_registry"):
                        module.set_skill_registry(self._skill_registry)
                        break
        except Exception:
            # Ignore errors if the plugin doesn't exist or has issues
            pass

    def _resolve_provider(self, config: Dict[str, Any], requested_provider_id: str = "") -> tuple[Dict[str, Any], str]:
        providers_cfg = config.get("providers") or {}
        items_raw = providers_cfg.get("items") or []
        items = [item for item in items_raw if isinstance(item, dict)]
        if not items:
            raise RuntimeError("No model providers are configured")

        by_id = {str(item.get("id") or "").strip().lower(): item for item in items if str(item.get("id") or "").strip()}
        enabled_items = [item for item in items if bool(item.get("enabled", True))]
        if not enabled_items:
            raise RuntimeError("No enabled model providers are available")

        default_provider_id = str(providers_cfg.get("default_provider_id") or "").strip().lower()
        default_provider = by_id.get(default_provider_id)
        if default_provider is None or not bool(default_provider.get("enabled", True)):
            default_provider = enabled_items[0]

        requested = str(requested_provider_id or "").strip().lower()
        if not requested:
            return copy.deepcopy(default_provider), "default"

        requested_provider = by_id.get(requested)
        if requested_provider is None:
            return copy.deepcopy(default_provider), f"requested_missing:{requested}"
        if not bool(requested_provider.get("enabled", True)):
            return copy.deepcopy(default_provider), f"requested_disabled:{requested}"
        return copy.deepcopy(requested_provider), "requested"

    def history(self, limit: int = 100) -> List[Dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 400))
        with self._chat_lock:
            return list(self._history)[-safe_limit:]

    def chat(self, user_message: str, source: str = "web", meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.chat_with_updates(user_message=user_message, source=source, meta=meta, status_callback=None)

    def chat_with_updates(
        self,
        user_message: str,
        source: str = "web",
        meta: Optional[Dict[str, Any]] = None,
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        content = (user_message or "").strip()
        if not content:
            raise ValueError("Message must not be empty")
        LOGGER.info("Agent request source=%s message_chars=%d", source, len(content))
        meta_payload = copy.deepcopy(meta) if isinstance(meta, dict) else {}
        requested_provider_id = str(meta_payload.get("provider_id") or "").strip().lower()

        def report_status(message: str) -> None:
            if not status_callback:
                return
            try:
                status_callback(message)
            except Exception:
                self._event_log.add(
                    "agent.status.error",
                    "Status callback failed",
                    {"message": message},
                )

        with self._chat_lock:
            try:
                config = self._config_store.get()
                agent_cfg = config["agent"]
                provider, provider_reason = self._resolve_provider(config, requested_provider_id=requested_provider_id)
                provider_id = str(provider.get("id") or "")
                provider_type = str(provider.get("type") or "ollama")
                provider_model = str(provider.get("model") or "")

                trace_id = f"trace-{int(time.time() * 1000)}"

                def mark_stage(stage: str, why: str, status_text: Optional[str] = None) -> None:
                    self._event_log.add(
                        "agent.stage",
                        "Agent stage update",
                        {
                            "trace_id": trace_id,
                            "source": source,
                            "stage": stage,
                            "why": why,
                        },
                    )
                    if status_text:
                        report_status(status_text)

                mark_stage("analyze", "Score query against enabled skills and decide context inputs.", status_text="analyze")
                selected_skills = self._skill_registry.applicable_for_query(
                    agent_cfg.get("enabled_skills", []),
                    content,
                    min_score=int(agent_cfg.get("skill_match_min_score") or 2),
                )

                default_prompt = str(
                    agent_cfg.get("system_prompt_default")
                    or agent_cfg.get("system_prompt")
                    or "You are MiniClaw."
                ).strip()
                provider_prompt_override = str(provider.get("system_prompt_override") or "").strip()
                effective_system_prompt = provider_prompt_override or default_prompt

                memory_blocks = self._memory_store.prompt_blocks()
                if memory_blocks:
                    self._event_log.add(
                        "memory.prompt.loaded",
                        "Loaded memory context blocks",
                        {
                            "trace_id": trace_id,
                            "count": len(memory_blocks),
                            "files": [item.get("name") for item in memory_blocks],
                        },
                    )

                messages: List[Dict[str, str]] = [{"role": "system", "content": effective_system_prompt}]
                for block in memory_blocks:
                    block_name = str(block.get("name") or "memory.md")
                    block_content = str(block.get("content") or "").strip()
                    if not block_content:
                        continue
                    messages.append(
                        {
                            "role": "system",
                            "content": f"[Memory: {block_name}]\n{block_content}",
                        }
                    )

                for skill in selected_skills:
                    self._event_log.add(
                        "skill.applied",
                        "Applied skill to prompt",
                        {
                            "trace_id": trace_id,
                            "skill": skill["id"],
                            "path": skill["path"],
                            "match": skill.get("_match"),
                        },
                    )
                    messages.append(
                        {
                            "role": "system",
                            "content": f"[Skill: {skill['id']}]\n{skill['content']}",
                        }
                    )

                max_history = int(agent_cfg.get("max_history_messages") or 12)
                history_items = list(self._history)[-max_history:]
                for item in history_items:
                    role = str(item.get("role") or "")
                    text = str(item.get("content") or "")
                    if role and text:
                        messages.append({"role": role, "content": text})

                plugin_context = {
                    "trace_id": trace_id,
                    "source": source,
                    "meta": meta_payload,
                    "history": history_items,
                    "user_message": content,
                    "config": config,
                    "provider": provider,
                }
                mark_stage("plugins", "Apply enabled pre-prompt plugin hooks.", status_text="plugins")
                plugin_messages = self._plugin_registry.run_pre_prompt(plugin_context)
                messages.extend(plugin_messages)

                messages.append({"role": "user", "content": content})

                self._event_log.add(
                    "agent.plan",
                    "Planned response execution",
                    {
                        "trace_id": trace_id,
                        "source": source,
                        "query": {
                            "chars": len(content),
                            "preview": content[:220],
                        },
                        "why": {
                            "provider": {
                                "id": provider_id,
                                "type": provider_type,
                                "model": provider_model,
                                "selection_reason": provider_reason,
                            },
                            "selected_skills": [
                                {
                                    "id": skill.get("id"),
                                    "match": skill.get("_match"),
                                }
                                for skill in selected_skills
                            ],
                            "memory_blocks_used": [item.get("name") for item in memory_blocks],
                            "history_messages_used": len(history_items),
                            "plugin_messages_added": len(plugin_messages),
                            "enabled_plugins": [item["id"] for item in self._plugin_registry.list() if item.get("enabled")],
                        },
                    },
                )

                self._event_log.add(
                    "prompt.built",
                    "Built prompt for provider",
                    {
                        "trace_id": trace_id,
                        "provider_id": provider_id,
                        "provider_type": provider_type,
                        "model": provider_model,
                        "source": source,
                        "messages": messages,
                    },
                )

                tools_catalog = self._tool_runner.catalog(include_mcp_details=False)
                tools_enabled = bool(tools_catalog.get("enabled", False))
                tool_defs = tools_catalog.get("tools") or []
                max_tool_steps = max(0, int(tools_catalog.get("max_steps") or 0))
                if tools_enabled and tool_defs and max_tool_steps > 0:
                    messages.append({"role": "system", "content": self._tool_runner.agent_prompt_block()})

                tool_runs: List[Dict[str, Any]] = []
                raw_response: Dict[str, Any] = {}
                assistant_message = ""
                usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                model_calls = 0
                output_limit = int(config.get("tools", {}).get("output_char_limit") or 12000)
                empty_retry_done = False
                use_ollama_tools = (
                    tools_enabled
                    and tool_defs
                    and max_tool_steps > 0
                    and str(provider_type or "").strip().lower() == "ollama"
                )
                ollama_tools: Optional[List[Dict[str, Any]]] = (
                    self._tool_runner.tool_defs_ollama() if use_ollama_tools else None
                )

                while True:
                    model_calls += 1
                    mark_stage("model_call", "Send prompt to model for completion.", status_text=f"model {provider_model}")
                    raw_response = self._model_client.chat(
                        provider=provider, messages=messages, tools=ollama_tools
                    )

                    assistant_message = ""
                    message_obj = raw_response.get("message") if isinstance(raw_response, dict) else {}
                    if isinstance(message_obj, dict):
                        assistant_message = str(message_obj.get("content") or "").strip()
                        if not assistant_message and isinstance(message_obj.get("parts"), list):
                            for part in message_obj.get("parts", []):
                                if isinstance(part, dict) and part.get("text"):
                                    assistant_message = str(part.get("text") or "").strip()
                                    break
                    has_native_tool_calls = (
                        isinstance(message_obj, dict)
                        and isinstance(message_obj.get("tool_calls"), list)
                        and len(message_obj.get("tool_calls") or []) > 0
                    )
                    if not assistant_message and not has_native_tool_calls:
                        if (
                            tools_enabled
                            and tool_defs
                            and not empty_retry_done
                            and len(tool_runs) == 0
                        ):
                            messages.append(
                                {
                                    "role": "system",
                                    "content": (
                                        "Your previous response was empty. You must reply with exactly one of: "
                                        "(1) A single JSON object for a tool call: {\"tool\":\"tool_name\",\"arguments\":{...}}, or "
                                        "(2) Plain text for your final answer. No other format."
                                    ),
                                }
                            )
                            empty_retry_done = True
                            continue
                        assistant_message = "MiniClaw received an empty response from the selected model provider."

                    usage_raw = raw_response.get("usage") if isinstance(raw_response, dict) else {}
                    if not isinstance(usage_raw, dict):
                        usage_raw = {}
                    call_usage = {
                        "prompt_tokens": int(usage_raw.get("prompt_tokens") or 0),
                        "completion_tokens": int(usage_raw.get("completion_tokens") or 0),
                    }
                    call_usage["total_tokens"] = int(
                        usage_raw.get("total_tokens") or (call_usage["prompt_tokens"] + call_usage["completion_tokens"])
                    )
                    usage["prompt_tokens"] += call_usage["prompt_tokens"]
                    usage["completion_tokens"] += call_usage["completion_tokens"]
                    usage["total_tokens"] += call_usage["total_tokens"]

                    call_provider_id = str((raw_response or {}).get("provider_id") or provider_id)
                    call_provider_type = str((raw_response or {}).get("provider_type") or provider_type)
                    call_model = str((raw_response or {}).get("model") or provider_model)
                    self._usage_tracker.add(
                        {
                            "trace_id": trace_id,
                            "source": source,
                            "provider_id": call_provider_id,
                            "provider_type": call_provider_type,
                            "model": call_model,
                            "prompt_tokens": call_usage["prompt_tokens"],
                            "completion_tokens": call_usage["completion_tokens"],
                            "total_tokens": call_usage["total_tokens"],
                        }
                    )

                    if not tools_enabled or not tool_defs or max_tool_steps <= 0:
                        break

                    message_obj = raw_response.get("message") if isinstance(raw_response, dict) else {}
                    native_tool_calls = message_obj.get("tool_calls") if isinstance(message_obj, dict) else None
                    if isinstance(native_tool_calls, list) and len(native_tool_calls) > 0:
                        if len(tool_runs) >= max_tool_steps:
                            self._event_log.add(
                                "agent.tools.limit",
                                "Tool step budget exhausted (native tool_calls)",
                                {
                                    "trace_id": trace_id,
                                    "max_tool_steps": max_tool_steps,
                                    "assistant_message": assistant_message,
                                },
                            )
                            assistant_message = (
                                f"MiniClaw stopped after reaching the tool step limit ({max_tool_steps}). "
                                "Refine the request or increase tools.max_steps."
                            )
                            break
                        messages.append({
                            "role": "assistant",
                            "content": assistant_message or "",
                            "tool_calls": native_tool_calls,
                        })
                        for tc in native_tool_calls:
                            if len(tool_runs) >= max_tool_steps:
                                break
                            func = tc.get("function") if isinstance(tc, dict) else {}
                            tool_name = str((func.get("name") if isinstance(func, dict) else "") or "").strip()
                            if not tool_name:
                                continue
                            raw_args = func.get("arguments") if isinstance(func, dict) else None
                            if isinstance(raw_args, str):
                                try:
                                    tool_args = json.loads(raw_args) if raw_args.strip() else {}
                                except (json.JSONDecodeError, TypeError):
                                    tool_args = {}
                            else:
                                tool_args = raw_args if isinstance(raw_args, dict) else {}
                            mark_stage("tool_call", "Execute a requested tool before final response.", status_text=f"tool {tool_name}")
                            tool_result = self._tool_runner.run(
                                tool_name,
                                tool_args,
                                trace={"trace_id": trace_id, "source": source, "step": len(tool_runs) + 1},
                            )
                            tool_runs.append(
                                {"tool": tool_name, "arguments": tool_args, "result": tool_result},
                            )
                            self._event_log.add(
                                "agent.tool_call",
                                "Agent executed a tool call",
                                {
                                    "trace_id": trace_id,
                                    "tool": tool_name,
                                    "arguments": tool_args,
                                    "result": tool_result,
                                    "step": len(tool_runs),
                                },
                            )
                            tool_result_text = truncate_text(
                                json.dumps(tool_result, indent=2, sort_keys=True), output_limit
                            )
                            messages.append({
                                "role": "tool",
                                "tool_name": tool_name,
                                "content": tool_result_text,
                            })
                        continue

                    parsed_tool_call = self._tool_runner.parse_tool_call(assistant_message)
                    if parsed_tool_call is None:
                        break
                    if len(tool_runs) >= max_tool_steps:
                        self._event_log.add(
                            "agent.tools.limit",
                            "Tool step budget exhausted",
                            {
                                "trace_id": trace_id,
                                "max_tool_steps": max_tool_steps,
                                "assistant_message": assistant_message,
                            },
                        )
                        assistant_message = (
                            f"MiniClaw stopped after reaching the tool step limit ({max_tool_steps}). "
                            "Refine the request or increase tools.max_steps."
                        )
                        break

                    tool_name = str(parsed_tool_call.get("tool") or "")
                    tool_args = parsed_tool_call.get("arguments") if isinstance(parsed_tool_call.get("arguments"), dict) else {}
                    mark_stage("tool_call", "Execute a requested tool before final response.", status_text=f"tool {tool_name}")
                    tool_result = self._tool_runner.run(
                        tool_name,
                        tool_args,
                        trace={"trace_id": trace_id, "source": source, "step": len(tool_runs) + 1},
                    )
                    tool_runs.append(
                        {
                            "tool": tool_name,
                            "arguments": tool_args,
                            "result": tool_result,
                        }
                    )
                    self._event_log.add(
                        "agent.tool_call",
                        "Agent executed a tool call",
                        {
                            "trace_id": trace_id,
                            "tool": tool_name,
                            "arguments": tool_args,
                            "result": tool_result,
                            "step": len(tool_runs),
                        },
                    )
                    messages.append({"role": "assistant", "content": assistant_message})
                    tool_result_text = truncate_text(json.dumps(tool_result, indent=2, sort_keys=True), output_limit)
                    messages.append(
                        {
                            "role": "system",
                            "content": (
                                f"[Tool Result #{len(tool_runs)} | {tool_name}]\n"
                                f"{tool_result_text}\n\n"
                                "Continue. Use another tool call JSON if needed; otherwise provide the final answer."
                            ),
                        }
                    )

                used_provider_id = str((raw_response or {}).get("provider_id") or provider_id)
                used_provider_type = str((raw_response or {}).get("provider_type") or provider_type)
                used_model = str((raw_response or {}).get("model") or provider_model)

                self._memory_store.append_journal(
                    source=source,
                    trace_id=trace_id,
                    user_message=content,
                    assistant_response=assistant_message,
                    provider_id=used_provider_id,
                    model=used_model,
                )

                now = utc_now()
                self._history.append(
                    {
                        "role": "user",
                        "content": content,
                        "source": source,
                        "meta": meta_payload,
                        "timestamp": now,
                    }
                )
                self._history.append(
                    {
                        "role": "assistant",
                        "content": assistant_message,
                        "source": "miniclaw",
                        "meta": {
                            "trace_id": trace_id,
                            "provider_id": used_provider_id,
                            "model": used_model,
                            "usage": usage,
                            "tool_runs": tool_runs,
                        },
                        "timestamp": now,
                    }
                )

                self._plugin_registry.run_post_response(
                    {
                        "trace_id": trace_id,
                        "source": source,
                        "meta": meta_payload,
                        "response": assistant_message,
                        "raw_response": raw_response,
                        "provider": {
                            "id": used_provider_id,
                            "type": used_provider_type,
                            "model": used_model,
                        },
                        "usage": usage,
                        "tool_runs": tool_runs,
                    }
                )
                mark_stage("finalize", "Persist history and finalize response payload.", status_text="final")

                self._event_log.add(
                    "agent.response",
                    "Agent produced response",
                    {
                        "trace_id": trace_id,
                        "source": source,
                        "provider": {
                            "id": used_provider_id,
                            "type": used_provider_type,
                            "model": used_model,
                        },
                        "usage": usage,
                        "model_calls": model_calls,
                        "tool_runs": tool_runs,
                        "response": assistant_message,
                        "raw_response": raw_response,
                    },
                )
                LOGGER.info(
                    "Agent response source=%s trace_id=%s provider=%s model=%s response_chars=%d model_calls=%d tool_runs=%d",
                    source,
                    trace_id,
                    used_provider_id,
                    used_model,
                    len(assistant_message),
                    model_calls,
                    len(tool_runs),
                )
                return {
                    "trace_id": trace_id,
                    "response": assistant_message,
                    "provider": {
                        "id": used_provider_id,
                        "type": used_provider_type,
                        "model": used_model,
                    },
                    "usage": usage,
                    "model_calls": model_calls,
                    "tool_runs": tool_runs,
                    "raw_response": raw_response,
                }
            except Exception as exc:
                self._event_log.add(
                    "agent.error",
                    "Agent failed to produce response",
                    {
                        "source": source,
                        "error": f"{exc.__class__.__name__}: {exc}",
                        "traceback": traceback.format_exc(limit=10),
                    },
                )
                LOGGER.exception("Agent error source=%s", source)
                raise