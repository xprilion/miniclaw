"""Unit tests for MiniClaw model client."""

import json
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import urllib.error

from miniclaw.tools.model_client import ModelProviderClient
from miniclaw.core.events import EventLog


class TestModelProviderClient(unittest.TestCase):
    """Test cases for ModelProviderClient."""

    def setUp(self):
        """Set up test fixtures."""
        self.event_log = EventLog()
        self.client = ModelProviderClient(self.event_log)

    def test_messages_to_generate_prompt(self):
        """Test converting messages to generate prompt."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm doing well, thank you!"},
            {"role": "user", "content": "What's the weather like today?"},
        ]

        prompt = self.client._messages_to_generate_prompt(messages)

        # Check that prompt contains all messages
        self.assertIn("SYSTEM:", prompt)
        self.assertIn("USER:", prompt)
        self.assertIn("ASSISTANT:", prompt)
        self.assertIn("You are a helpful assistant.", prompt)
        self.assertIn("Hello, how are you?", prompt)
        self.assertIn("I'm doing well, thank you!", prompt)
        self.assertIn("What's the weather like today?", prompt)
        # Should end with ASSISTANT:
        self.assertTrue(prompt.endswith("ASSISTANT:"))

    def test_messages_to_generate_prompt_empty_messages(self):
        """Test converting empty messages to generate prompt."""
        messages = []
        prompt = self.client._messages_to_generate_prompt(messages)
        self.assertEqual(prompt, "ASSISTANT:")

    def test_messages_to_generate_prompt_empty_content(self):
        """Test converting messages with empty content to generate prompt."""
        messages = [
            {"role": "user", "content": ""},
            {"role": "user", "content": "Hello"},
        ]
        prompt = self.client._messages_to_generate_prompt(messages)
        # Check that the prompt contains the non-empty message
        self.assertIn("Hello", prompt)
        # Check that empty content messages are skipped (only one USER section)
        self.assertEqual(prompt.count("USER:"), 1)
        # The empty message should not be included
        self.assertNotIn("EMPTY", prompt)

    def test_request_json_get_success(self):
        """Test successful GET request."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock response
            mock_response = MagicMock()
            mock_response.read.return_value.decode.return_value = (
                '{"result": "success"}'
            )
            mock_response.status = 200
            mock_response.headers.get.return_value = "application/json"
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = self.client._request_json(
                url="http://example.com/api/test",
                method="GET",
                payload=None,
                timeout_seconds=30,
                verify_tls=True,
            )

            self.assertEqual(result, {"result": "success"})

    def test_request_json_post_with_payload(self):
        """Test POST request with JSON payload."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock response
            mock_response = MagicMock()
            mock_response.read.return_value.decode.return_value = (
                '{"status": "created"}'
            )
            mock_response.status = 201
            mock_response.headers.get.return_value = "application/json"
            mock_urlopen.return_value.__enter__.return_value = mock_response

            payload = {"name": "test", "value": 123}
            result = self.client._request_json(
                url="http://example.com/api/test",
                method="POST",
                payload=payload,
                timeout_seconds=30,
                verify_tls=True,
            )

            self.assertEqual(result, {"status": "created"})

    def test_request_json_with_http_error(self):
        """Test handling of HTTP errors."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock HTTP error
            mock_error = urllib.error.HTTPError(
                "http://example.com/api/test", 404, "Not Found", {}, None
            )
            mock_error.read = MagicMock(return_value=b'{"error": "Resource not found"}')
            mock_urlopen.side_effect = mock_error

            with self.assertRaises(RuntimeError) as context:
                self.client._request_json(
                    url="http://example.com/api/test",
                    method="GET",
                    payload=None,
                    timeout_seconds=30,
                    verify_tls=True,
                )

            self.assertIn("HTTP 404", str(context.exception))

    def test_request_json_with_network_error(self):
        """Test handling of network errors."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock network error
            mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

            with self.assertRaises(RuntimeError) as context:
                self.client._request_json(
                    url="http://example.com/api/test",
                    method="GET",
                    payload=None,
                    timeout_seconds=30,
                    verify_tls=True,
                )

            self.assertIn("Network error", str(context.exception))

    def test_request_json_empty_response(self):
        """Test handling of empty response."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock empty response
            mock_response = MagicMock()
            mock_response.read.return_value.decode.return_value = ""
            mock_response.status = 200
            mock_response.headers.get.return_value = "application/json"
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = self.client._request_json(
                url="http://example.com/api/test",
                method="GET",
                payload=None,
                timeout_seconds=30,
                verify_tls=True,
            )

            self.assertEqual(result, {})

    def test_request_json_invalid_json_response(self):
        """Test handling of invalid JSON response."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock invalid JSON response
            mock_response = MagicMock()
            mock_response.read.return_value.decode.return_value = '{"invalid": json'
            mock_response.status = 200
            mock_response.headers.get.return_value = "application/json"
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = self.client._request_json(
                url="http://example.com/api/test",
                method="GET",
                payload=None,
                timeout_seconds=30,
                verify_tls=True,
            )

            self.assertIn("error", result)
            self.assertIn("Invalid JSON response", result["error"])

    def test_request_json_non_json_response(self):
        """Test handling of non-JSON response."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock non-JSON response
            mock_response = MagicMock()
            mock_response.read.return_value.decode.return_value = (
                "<html><body>Error</body></html>"
            )
            mock_response.status = 200
            mock_response.headers.get.return_value = "text/html"
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = self.client._request_json(
                url="http://example.com/api/test",
                method="GET",
                payload=None,
                timeout_seconds=30,
                verify_tls=True,
            )

            self.assertIn("error", result)
            self.assertIn("Non-JSON response", result["error"])

    def test_list_models_ollama_success(self):
        """Test listing models from Ollama provider."""
        provider = {
            "type": "ollama",
            "base_url": "http://localhost:11434",
            "id": "test_ollama",
        }

        with patch.object(self.client, "_request_json") as mock_request:
            mock_request.return_value = {
                "models": [{"name": "llama2:7b"}, {"name": "mistral:7b"}]
            }

            models = self.client.list_models(provider)

            self.assertEqual(len(models), 2)
            self.assertIn("llama2:7b", models)
            self.assertIn("mistral:7b", models)

    def test_list_models_ollama_empty_base_url(self):
        """Test listing models with empty base URL."""
        provider = {"type": "ollama", "base_url": "", "model": "llama2:7b"}

        models = self.client.list_models(provider)
        self.assertEqual(models, ["llama2:7b"])

    def test_list_models_openai_compatible_no_listing(self):
        """Test listing models from OpenAI compatible provider with no listing."""
        provider = {
            "type": "openai_compatible",
            "base_url": "http://localhost:8000",
            "id": "test_openai",
            "model": "gpt-4o-mini",
        }

        # Mock the _request_json method to avoid actual network calls
        with patch.object(self.client, '_request_json') as mock_request:
            mock_request.return_value = {"data": []}  # Empty response means no models found
            models = self.client.list_models(provider)
            self.assertEqual(models, ["gpt-4o-mini"])  # Should return the default model

    def test_list_models_openrouter_no_listing(self):
        """Test listing models from OpenRouter provider with no listing."""
        provider = {
            "type": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
            "id": "test_openrouter",
            "model": "openai/gpt-4o-mini",
        }

        models = self.client.list_models(provider)
        self.assertEqual(models, ["openai/gpt-4o-mini"])

    def test_chat_ollama_success(self):
        """Test successful Ollama chat request."""
        provider = {
            "type": "ollama",
            "base_url": "http://localhost:11434",
            "model": "llama2:7b",
            "id": "test_ollama",
            "temperature": 0.7,
        }
        messages = [{"role": "user", "content": "Hello, how are you?"}]

        with patch.object(self.client, "_request_json") as mock_request:
            mock_request.return_value = {
                "message": {"content": "I'm doing well, thank you!"},
                "prompt_eval_count": 10,
                "eval_count": 20,
            }

            result = self.client._chat_ollama(provider, messages)

            self.assertEqual(result["provider_id"], "test_ollama")
            self.assertEqual(result["provider_type"], "ollama")
            self.assertEqual(result["model"], "llama2:7b")
            self.assertEqual(result["message"]["content"], "I'm doing well, thank you!")
            self.assertEqual(result["usage"]["prompt_tokens"], 10)
            self.assertEqual(result["usage"]["completion_tokens"], 20)

    def test_chat_ollama_with_tool_calls(self):
        """Test Ollama chat request with tool calls."""
        provider = {
            "type": "ollama",
            "base_url": "http://localhost:11434",
            "model": "llama2:7b",
            "id": "test_ollama",
        }
        messages = [{"role": "user", "content": "What's the weather?"}]

        with patch.object(self.client, "_request_json") as mock_request:
            mock_request.return_value = {
                "message": {
                    "content": "I'll check the weather for you.",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "get_weather",
                                "arguments": {"location": "New York"},
                            }
                        }
                    ],
                },
                "prompt_eval_count": 15,
                "eval_count": 25,
            }

            result = self.client._chat_ollama(provider, messages)

            self.assertIn("tool_calls", result["message"])
            self.assertEqual(len(result["message"]["tool_calls"]), 1)
            self.assertEqual(
                result["message"]["tool_calls"][0]["function"]["name"], "get_weather"
            )

    def test_chat_ollama_fallback_to_generate(self):
        """Test Ollama chat falling back to generate endpoint."""
        provider = {
            "type": "ollama",
            "base_url": "http://localhost:11434",
            "model": "llama2:7b",
            "id": "test_ollama",
        }
        messages = [{"role": "user", "content": "Hello"}]

        with patch.object(self.client, "_request_json") as mock_request:
            # First call raises error about tool call parsing
            mock_request.side_effect = [
                RuntimeError("error parsing tool call"),
                {
                    "response": "Hello! How can I help you?",
                    "prompt_eval_count": 5,
                    "eval_count": 15,
                },
            ]

            result = self.client._chat_ollama(provider, messages)

            # Should have fallen back to generate endpoint
            self.assertEqual(result["message"]["content"], "Hello! How can I help you?")
            self.assertIn("fallback", result["raw_response"])

    def test_chat_openai_compatible_success(self):
        """Test successful OpenAI compatible chat request."""
        provider = {
            "type": "openai_compatible",
            "base_url": "http://localhost:8000",
            "model": "gpt-4o-mini",
            "id": "test_openai",
            "temperature": 0.7,
            "api_key": "test-key",
        }
        messages = [{"role": "user", "content": "Hello, how are you?"}]

        # Mock the OpenAI client
        with patch("miniclaw.tools.model_client.OpenAI") as mock_openai_class:
            mock_client = Mock()
            mock_openai_class.return_value = mock_client

            # Mock the response
            mock_choice = Mock()
            mock_choice.message.content = "I'm doing well, thank you!"
            mock_response = Mock()
            mock_response.choices = [mock_choice]
            mock_response.usage = Mock()
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 20
            mock_response.usage.total_tokens = 30
            mock_response.model_dump.return_value = {"mock": "response"}

            mock_client.chat.completions.create.return_value = mock_response

            result = self.client._chat_openai_compatible(provider, messages)

            self.assertEqual(result["provider_id"], "test_openai")
            self.assertEqual(result["provider_type"], "openai_compatible")
            self.assertEqual(result["model"], "gpt-4o-mini")
            self.assertEqual(result["message"]["content"], "I'm doing well, thank you!")
            self.assertEqual(result["usage"]["prompt_tokens"], 10)
            self.assertEqual(result["usage"]["completion_tokens"], 20)

    def test_chat_openai_compatible_api_error(self):
        """Test OpenAI compatible chat request with API error."""
        provider = {
            "type": "openai_compatible",
            "base_url": "http://localhost:8000",
            "model": "gpt-4o-mini",
            "id": "test_openai",
            "api_key": "test-key",
        }
        messages = [{"role": "user", "content": "Hello"}]

        # Mock the OpenAI client to raise an API error
        with patch("miniclaw.tools.model_client.OpenAI") as mock_openai_class:
            mock_client = Mock()
            mock_openai_class.return_value = mock_client

            import openai
            import httpx
            from unittest.mock import Mock as UMock

            # Create a mock request object
            mock_request = UMock(spec=httpx.Request)
            mock_request.method = "POST"
            mock_request.url = "http://localhost:8000/chat/completions"
            
            mock_client.chat.completions.create.side_effect = openai.APIError(
                "Test API error",
                request=mock_request,
                body=None
            )

            with self.assertRaises(RuntimeError) as context:
                self.client._chat_openai_compatible(provider, messages)

            self.assertIn("OpenAI API error", str(context.exception))

    def test_chat_litellm_success(self):
        """Test successful LiteLLM chat request."""
        provider = {
            "type": "litellm",
            "base_url": "http://localhost:4000",
            "model": "gpt-4o-mini",
            "id": "test_litellm",
            "temperature": 0.7,
            "api_key": "test-key",
        }
        messages = [{"role": "user", "content": "Hello, how are you?"}]

        with patch.object(self.client, "_request_json") as mock_request:
            mock_request.return_value = {
                "choices": [{"message": {"content": "I'm doing well, thank you!"}}],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                },
            }

            result = self.client._chat_litellm(provider, messages)

            self.assertEqual(result["provider_id"], "test_litellm")
            self.assertEqual(result["provider_type"], "litellm")
            self.assertEqual(result["model"], "gpt-4o-mini")
            self.assertEqual(result["message"]["content"], "I'm doing well, thank you!")
            self.assertEqual(result["usage"]["prompt_tokens"], 10)
            self.assertEqual(result["usage"]["completion_tokens"], 20)

    def test_chat_openrouter_success(self):
        """Test successful OpenRouter chat request."""
        provider = {
            "type": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
            "model": "openai/gpt-4o-mini",
            "id": "test_openrouter",
            "temperature": 0.7,
            "api_key": "test-key",
        }
        messages = [{"role": "user", "content": "Hello, how are you?"}]

        with patch.object(self.client, "_request_json") as mock_request:
            mock_request.return_value = {
                "choices": [{"message": {"content": "I'm doing well, thank you!"}}],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                },
            }

            result = self.client._chat_openrouter(provider, messages)

            self.assertEqual(result["provider_id"], "test_openrouter")
            self.assertEqual(result["provider_type"], "openrouter")
            self.assertEqual(result["model"], "openai/gpt-4o-mini")
            self.assertEqual(result["message"]["content"], "I'm doing well, thank you!")
            self.assertEqual(result["usage"]["prompt_tokens"], 10)
            self.assertEqual(result["usage"]["completion_tokens"], 20)

    def test_chat_openrouter_raises_on_provider_error_payload(self):
        """OpenRouter in-body errors should be surfaced clearly."""
        provider = {
            "type": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
            "model": "openai/gpt-4o-mini",
            "id": "test_openrouter",
            "api_key": "test-key",
        }
        messages = [{"role": "user", "content": "Hello"}]

        with patch.object(self.client, "_request_json") as mock_request:
            mock_request.return_value = {"error": {"message": "Upstream provider timed out"}}

            with self.assertRaises(RuntimeError) as context:
                self.client._chat_openrouter(provider, messages)

        self.assertIn("Upstream provider timed out", str(context.exception))

    def test_chat_openrouter_raises_on_empty_response(self):
        """OpenRouter empty replies should raise a useful error instead of returning blank content."""
        provider = {
            "type": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
            "model": "openai/gpt-4o-mini",
            "id": "test_openrouter",
            "api_key": "test-key",
        }
        messages = [{"role": "user", "content": "Hello"}]

        with patch.object(self.client, "_request_json") as mock_request:
            mock_request.return_value = {"id": "resp_123", "choices": [{"message": {}}]}

            with self.assertRaises(RuntimeError) as context:
                self.client._chat_openrouter(provider, messages)

        self.assertIn("empty response", str(context.exception).lower())

    def test_chat_dispatch_by_provider_type(self):
        """Test chat method dispatches to correct provider type."""
        provider = {
            "type": "ollama",
            "base_url": "http://localhost:11434",
            "model": "llama2:7b",
            "id": "test_ollama",
        }
        messages = [{"role": "user", "content": "Hello"}]

        with patch.object(self.client, "_chat_ollama") as mock_ollama:
            mock_ollama.return_value = {
                "provider_id": "test_ollama",
                "provider_type": "ollama",
                "model": "llama2:7b",
                "message": {"role": "assistant", "content": "Hi!"},
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 10,
                    "total_tokens": 15,
                },
            }

            result = self.client.chat(provider, messages)

            mock_ollama.assert_called_once_with(provider, messages, tools=None)
            self.assertEqual(result["provider_type"], "ollama")

    def test_chat_dispatch_openai_compatible(self):
        """Test chat method dispatches to OpenAI compatible provider."""
        provider = {
            "type": "openai_compatible",
            "base_url": "http://localhost:8000",
            "model": "gpt-4o-mini",
            "id": "test_openai",
        }
        messages = [{"role": "user", "content": "Hello"}]

        with patch.object(self.client, "_chat_openai_compatible") as mock_openai:
            mock_openai.return_value = {
                "provider_id": "test_openai",
                "provider_type": "openai_compatible",
                "model": "gpt-4o-mini",
                "message": {"role": "assistant", "content": "Hi!"},
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 10,
                    "total_tokens": 15,
                },
            }

            result = self.client.chat(provider, messages)

            mock_openai.assert_called_once_with(provider, messages)
            self.assertEqual(result["provider_type"], "openai_compatible")

    def test_chat_dispatch_litellm(self):
        """Test chat method dispatches to LiteLLM provider."""
        provider = {
            "type": "litellm",
            "base_url": "http://localhost:4000",
            "model": "gpt-4o-mini",
            "id": "test_litellm",
        }
        messages = [{"role": "user", "content": "Hello"}]

        with patch.object(self.client, "_chat_litellm") as mock_litellm:
            mock_litellm.return_value = {
                "provider_id": "test_litellm",
                "provider_type": "litellm",
                "model": "gpt-4o-mini",
                "message": {"role": "assistant", "content": "Hi!"},
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 10,
                    "total_tokens": 15,
                },
            }

            result = self.client.chat(provider, messages)

            mock_litellm.assert_called_once_with(provider, messages)
            self.assertEqual(result["provider_type"], "litellm")

    def test_chat_dispatch_openrouter(self):
        """Test chat method dispatches to OpenRouter provider."""
        provider = {
            "type": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
            "model": "openai/gpt-4o-mini",
            "id": "test_openrouter",
        }
        messages = [{"role": "user", "content": "Hello"}]

        with patch.object(self.client, "_chat_openrouter") as mock_openrouter:
            mock_openrouter.return_value = {
                "provider_id": "test_openrouter",
                "provider_type": "openrouter",
                "model": "openai/gpt-4o-mini",
                "message": {"role": "assistant", "content": "Hi!"},
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 10,
                    "total_tokens": 15,
                },
            }

            result = self.client.chat(provider, messages)

            mock_openrouter.assert_called_once_with(provider, messages)
            self.assertEqual(result["provider_type"], "openrouter")


if __name__ == "__main__":
    unittest.main()
