"""
LLM Client Wrapper
Unified OpenAI-format API calls
"""

import json
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI

from ..config import Config


class LLMClient:
    """LLM Client"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME

        if not self.api_key:
            raise ValueError("LLM_API_KEY not configured")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        Send a chat request

        Args:
            messages: Message list
            temperature: Temperature parameter
            max_tokens: Maximum token count
            response_format: Response format (e.g., JSON mode)

        Returns:
            Model response text
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            kwargs["response_format"] = response_format

        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        # Some models (e.g., MiniMax M2.5) may include <think> content in the response, which needs to be removed
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Send a chat request and return JSON.

        Uses response_format for OpenAI models, falls back to prompt-based
        JSON enforcement for Claude/other models via OpenClaw gateway.

        Args:
            messages: Message list
            temperature: Temperature parameter
            max_tokens: Maximum token count

        Returns:
            Parsed JSON object
        """
        # Detect if we're likely talking to Claude (via OpenClaw or Anthropic)
        is_claude = "claude" in self.model.lower() or "anthropic" in self.base_url.lower()

        if is_claude:
            # Claude: enforce JSON via system prompt, no response_format
            patched = list(messages)
            json_instruction = "\n\nYou MUST respond with valid JSON only. No markdown, no explanation, no text before or after the JSON."
            if patched and patched[0]["role"] == "system":
                patched[0] = {**patched[0], "content": patched[0]["content"] + json_instruction}
            else:
                patched.insert(0, {"role": "system", "content": "Respond with valid JSON only." + json_instruction})
            response = self.chat(
                messages=patched,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            # OpenAI-compatible: use native JSON mode
            response = self.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}
            )

        # Clean markdown code block markers and any preamble text before JSON
        cleaned_response = response.strip()
        cleaned_response = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\n?```\s*$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()

        # Strip any text preamble before the first { or [
        first_brace = cleaned_response.find('{')
        first_bracket = cleaned_response.find('[')
        starts = [i for i in [first_brace, first_bracket] if i >= 0]
        if starts and min(starts) > 0:
            cleaned_response = cleaned_response[min(starts):]

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON format returned by LLM: {cleaned_response[:200]}")
