"""Pluggable back ends for describing video frames.

The visual narration step needs *some* model that can look at images. This
module keeps that choice out of the rest of the code: everything else asks a
:class:`VisionBackend` to turn (prompt, images) into text, and does not care
which service answers.

Available back ends, in the order ``auto`` tries them:

===============  ==============================  ==================================
Name             Needs                           Cost
===============  ==============================  ==================================
``claude-cli``   the ``claude`` command, signed   included in a Claude subscription
                 in once
``anthropic``    ``ANTHROPIC_API_KEY``            pay per use
``openai``       ``OPENAI_API_KEY``               pay per use
``gemini``       ``GEMINI_API_KEY``               free tier available
``none``         nothing                          narration is skipped
===============  ==============================  ==================================

Adding another provider means writing one class with a ``generate`` method and
listing it in :data:`BACKENDS`.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path

# How long to wait for one description before giving up, in seconds.
REQUEST_TIMEOUT = 600


class VisionUnavailable(RuntimeError):
    """Raised when no back end can be used."""


def _read_image_as_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _post_json(url: str, payload: dict, headers: dict[str, str]) -> dict:
    """Minimal JSON POST so the toolkit needs no HTTP dependency."""
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    request.add_header("Content-Type", "application/json")
    for key, value in headers.items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"{url} returned HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach {url}: {exc.reason}") from exc


class VisionBackend(ABC):
    """Turns a text prompt plus images into a text answer."""

    name = "abstract"
    needs_network = True

    @abstractmethod
    def generate(self, prompt: str, images: list[Path], model: str) -> str:
        """Return the model's answer as plain text."""

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """True when this back end could run right now."""

    @classmethod
    def why_unavailable(cls) -> str:
        return f"{cls.name} is not configured."


class ClaudeCliBackend(VisionBackend):
    """Uses the Claude Code command line tool, which needs no API key.

    The prompt is piped through standard input because a two-minute window can
    exceed the command-line length limit on Windows.
    """

    name = "claude-cli"

    @classmethod
    def is_available(cls) -> bool:
        return shutil.which("claude") is not None

    @classmethod
    def why_unavailable(cls) -> str:
        return (
            "The 'claude' command is not installed. Get it from "
            "https://claude.com/claude-code and sign in once."
        )

    def generate(self, prompt: str, images: list[Path], model: str) -> str:
        # The CLI reads images itself, so the paths go in the prompt and the
        # Read tool is allowed. Nothing else is permitted.
        listing = "\n".join(f"  {path}" for path in images)
        full_prompt = f"{prompt}\n\nRead these image files:\n{listing}\n"

        command = ["claude", "-p", "--allowedTools", "Read", "--output-format", "text"]
        if model:
            command += ["--model", model]

        result = subprocess.run(
            command,
            input=full_prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=REQUEST_TIMEOUT,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"claude exited with code {result.returncode}: {result.stderr.strip()[:300]}"
            )
        return result.stdout.strip()


class AnthropicApiBackend(VisionBackend):
    """Calls the Anthropic Messages API directly with an API key."""

    name = "anthropic"
    DEFAULT_MODEL = "claude-sonnet-5"
    API_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"

    @classmethod
    def is_available(cls) -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY"))

    @classmethod
    def why_unavailable(cls) -> str:
        return "ANTHROPIC_API_KEY is not set. Put it in your .env file."

    def generate(self, prompt: str, images: list[Path], model: str) -> str:
        content: list[dict] = []
        for path in images:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": _read_image_as_base64(path),
                    },
                }
            )
        content.append({"type": "text", "text": prompt})

        payload = {
            "model": model or self.DEFAULT_MODEL,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": content}],
        }
        response = _post_json(
            self.API_URL,
            payload,
            {
                "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                "anthropic-version": self.API_VERSION,
            },
        )
        blocks = response.get("content", [])
        return "".join(block.get("text", "") for block in blocks).strip()


class OpenAiApiBackend(VisionBackend):
    """Calls the OpenAI Chat Completions API."""

    name = "openai"
    DEFAULT_MODEL = "gpt-4o"
    API_URL = "https://api.openai.com/v1/chat/completions"

    @classmethod
    def is_available(cls) -> bool:
        return bool(os.environ.get("OPENAI_API_KEY"))

    @classmethod
    def why_unavailable(cls) -> str:
        return "OPENAI_API_KEY is not set. Put it in your .env file."

    def generate(self, prompt: str, images: list[Path], model: str) -> str:
        content: list[dict] = [{"type": "text", "text": prompt}]
        for path in images:
            encoded = _read_image_as_base64(path)
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
            )

        payload = {
            "model": model or self.DEFAULT_MODEL,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": content}],
        }
        response = _post_json(
            self.API_URL, payload, {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"}
        )
        choices = response.get("choices", [])
        if not choices:
            raise RuntimeError("OpenAI returned no choices.")
        return (choices[0].get("message", {}).get("content") or "").strip()


class GeminiApiBackend(VisionBackend):
    """Calls the Google Gemini API, which has a usable free tier."""

    name = "gemini"
    DEFAULT_MODEL = "gemini-2.0-flash"

    @classmethod
    def is_available(cls) -> bool:
        return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))

    @classmethod
    def why_unavailable(cls) -> str:
        return "GEMINI_API_KEY is not set. Put it in your .env file."

    def generate(self, prompt: str, images: list[Path], model: str) -> str:
        key = os.environ.get("GEMINI_API_KEY") or os.environ["GOOGLE_API_KEY"]
        chosen = model or self.DEFAULT_MODEL
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{chosen}:generateContent?key={key}"
        )

        parts: list[dict] = [{"text": prompt}]
        for path in images:
            parts.append(
                {"inline_data": {"mime_type": "image/jpeg", "data": _read_image_as_base64(path)}}
            )

        response = _post_json(url, {"contents": [{"parts": parts}]}, {})
        candidates = response.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini returned no candidates.")
        chunks = candidates[0].get("content", {}).get("parts", [])
        return "".join(chunk.get("text", "") for chunk in chunks).strip()


class DisabledBackend(VisionBackend):
    """Placeholder used when narration is switched off."""

    name = "none"
    needs_network = False

    @classmethod
    def is_available(cls) -> bool:
        return True

    def generate(self, prompt: str, images: list[Path], model: str) -> str:
        raise VisionUnavailable("Visual narration is disabled.")


# Order matters: `auto` picks the first one that is ready.
BACKENDS: dict[str, type[VisionBackend]] = {
    "claude-cli": ClaudeCliBackend,
    "anthropic": AnthropicApiBackend,
    "openai": OpenAiApiBackend,
    "gemini": GeminiApiBackend,
    "none": DisabledBackend,
}

# Models each back end should use when the config leaves the choice open.
DEFAULT_MODELS: dict[str, tuple[str, str]] = {
    # backend: (per-window vision model, final synthesis model)
    "claude-cli": ("sonnet", "opus"),
    "anthropic": ("claude-sonnet-5", "claude-opus-5"),
    "openai": ("gpt-4o", "gpt-4o"),
    "gemini": ("gemini-2.0-flash", "gemini-2.0-flash"),
    "none": ("", ""),
}


def select_backend(preference: str = "auto") -> VisionBackend:
    """Return a ready-to-use back end.

    ``auto`` walks :data:`BACKENDS` in order and returns the first available
    one. Any other value selects that back end explicitly and fails loudly if
    it is not configured, so a typo in config.json does not silently fall back
    to something the user did not ask for.
    """
    choice = (preference or "auto").strip().lower()

    if choice == "auto":
        for name, backend_class in BACKENDS.items():
            if name == "none":
                continue
            if backend_class.is_available():
                return backend_class()
        raise VisionUnavailable(
            "No image-capable model is configured, so the video cannot be described.\n"
            "Pick one of these:\n"
            "  - install the 'claude' command from https://claude.com/claude-code\n"
            "  - or put ANTHROPIC_API_KEY, OPENAI_API_KEY or GEMINI_API_KEY in your .env file\n"
            "The transcript does not need any of this; only the visual description does."
        )

    if choice not in BACKENDS:
        known = ", ".join(BACKENDS)
        raise VisionUnavailable(f"Unknown vision back end '{preference}'. Choose one of: {known}")

    backend_class = BACKENDS[choice]
    if not backend_class.is_available():
        raise VisionUnavailable(backend_class.why_unavailable())
    return backend_class()


def available_backends() -> list[tuple[str, bool, str]]:
    """List every back end as ``(name, available, explanation)`` for the doctor."""
    rows = []
    for name, backend_class in BACKENDS.items():
        if name == "none":
            continue
        ready = backend_class.is_available()
        rows.append((name, ready, "ready" if ready else backend_class.why_unavailable()))
    return rows
