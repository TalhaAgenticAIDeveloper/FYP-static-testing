"""
Groq API Key Rotation Manager
──────────────────────────────
Loads multiple Groq API keys from .env and provides automatic
key rotation with retry logic on rate-limit (HTTP 429) errors.

Usage:
    from groq_key_manager import GroqKeyManager
    manager = GroqKeyManager()
    response = manager.invoke(prompt)
"""

import os
import re
import time
import logging
from typing import List, Optional

from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class AllKeysExhaustedError(Exception):
    """Raised when every available API key has been rate-limited."""
    pass


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class GroqKeyManager:
    """Manages a pool of Groq API keys with automatic rotation."""

    def __init__(
        self,
        model: str = "openai/gpt-oss-20b",
        temperature: float = 0,
        max_retries_per_key: int = 1,
        cooldown_seconds: float = 5.0,
    ):
        self.model = model
        self.temperature = temperature
        self.max_retries_per_key = max_retries_per_key
        self.cooldown_seconds = cooldown_seconds

        self._keys: List[str] = self._load_keys()
        if not self._keys:
            raise ValueError(
                "No Groq API keys found in .env. "
                "Expected GROQ_API_KEY, GROQ_API_KEY_0, GROQ_API_KEY_1, …"
            )

        self._current_index: int = 0
        self._llm: ChatGroq = self._build_llm(self._keys[self._current_index])

        logger.info("GroqKeyManager initialised with %d API key(s).", len(self._keys))

    # ------------------------------------------------------------------
    # Key loading
    # ------------------------------------------------------------------

    @staticmethod
    def _load_keys() -> List[str]:
        """Collect all GROQ_API_KEY* values from the environment."""
        keys: List[str] = []
        seen: set = set()

        # Gather every env var whose name matches GROQ_API_KEY*
        pattern = re.compile(r"^GROQ_API_KEY(_\d+)?$")
        for var_name, value in sorted(os.environ.items()):
            if pattern.match(var_name) and value:
                clean = value.strip().strip('"').strip("'")
                if clean and clean not in seen:
                    keys.append(clean)
                    seen.add(clean)

        return keys

    # ------------------------------------------------------------------
    # LLM construction
    # ------------------------------------------------------------------

    def _build_llm(self, api_key: str) -> ChatGroq:
        return ChatGroq(
            model=self.model,
            temperature=self.temperature,
            api_key=api_key,
        )

    # ------------------------------------------------------------------
    # Rotation
    # ------------------------------------------------------------------

    @property
    def current_key_label(self) -> str:
        return f"Key #{self._current_index + 1}/{len(self._keys)}"

    def _rotate(self) -> bool:
        """Move to the next key. Returns False if we've cycled through all."""
        next_index = self._current_index + 1
        if next_index >= len(self._keys):
            return False
        self._current_index = next_index
        self._llm = self._build_llm(self._keys[self._current_index])
        logger.info("Rotated to %s", self.current_key_label)
        return True

    def reset(self) -> None:
        """Reset back to the first key (call between files if desired)."""
        self._current_index = 0
        self._llm = self._build_llm(self._keys[self._current_index])

    # ------------------------------------------------------------------
    # Rate-limit detection
    # ------------------------------------------------------------------

    @staticmethod
    def _is_rate_limit_error(exc: Exception) -> bool:
        """Return True if the exception looks like an HTTP 429 / rate-limit."""
        exc_str = str(exc).lower()
        if "429" in exc_str:
            return True
        if "rate" in exc_str and "limit" in exc_str:
            return True
        if "rate_limit" in exc_str or "ratelimit" in exc_str:
            return True
        if "too many requests" in exc_str:
            return True
        # Walk the exception chain
        cause = getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)
        if cause and cause is not exc:
            return GroqKeyManager._is_rate_limit_error(cause)
        return False

    # ------------------------------------------------------------------
    # Public API – invoke with automatic retry & rotation
    # ------------------------------------------------------------------

    def invoke(self, prompt: str) -> str:
        """
        Call the LLM. On rate-limit errors, rotate the key and retry.
        Raises AllKeysExhaustedError if every key has been tried.
        """
        attempts = 0
        total_possible = len(self._keys) * (self.max_retries_per_key + 1)

        while attempts < total_possible:
            try:
                response = self._llm.invoke(prompt)
                return response.content
            except Exception as exc:
                if not self._is_rate_limit_error(exc):
                    raise  # not a rate-limit problem → propagate immediately

                attempts += 1
                logger.warning(
                    "Rate-limit hit on %s (attempt %d/%d): %s",
                    self.current_key_label,
                    attempts,
                    total_possible,
                    exc,
                )

                # Try rotating to the next key
                if not self._rotate():
                    # All keys used – raise a clear error
                    raise AllKeysExhaustedError(
                        f"All {len(self._keys)} Groq API keys have been "
                        f"rate-limited. Please wait and try again later."
                    ) from exc

                # Small cooldown before retrying with the new key
                time.sleep(self.cooldown_seconds)

        # Safety net (should not normally be reached)
        raise AllKeysExhaustedError(
            "Maximum retry attempts exceeded across all API keys."
        )
