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
``ollama``       Ollama running locally           free; private; slow on a CPU
``none``         nothing                          narration is skipped
===============  ==============================  ==================================

``auto`` tries them in that order, so a configured cloud model wins over the
local one. Pick ``ollama`` explicitly when the footage must not leave the
machine -- it is the only back end that sends nothing over the internet.

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
from dataclasses import dataclass
from pathlib import Path

from .i18n import t

# How long to wait for one description before giving up, in seconds.
REQUEST_TIMEOUT = 600


class VisionUnavailable(RuntimeError):
    """Raised when no back end can be used."""


def _read_image_as_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _check_http_url(url: str) -> str:
    """Reject anything that is not an HTTP(S) address.

    ``OLLAMA_HOST`` comes from the environment, and urllib is happy to open
    ``file://`` or ``ftp://``. Without this a stray environment variable turns
    a request meant for localhost into a read of local disk, and the API key
    headers would be sent wherever it pointed.
    """
    if not url.lower().startswith(("http://", "https://")):
        raise RuntimeError(
            f"Refusing to use '{url}': an image model address must start with "
            "http:// or https://. Check OLLAMA_HOST."
        )
    return url


def _post_json(url: str, payload: dict, headers: dict[str, str]) -> dict:
    """Minimal JSON POST so the toolkit needs no HTTP dependency."""
    _check_http_url(url)
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")  # noqa: S310 - scheme checked
    request.add_header("Content-Type", "application/json")
    for key, value in headers.items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:  # noqa: S310  # nosec B310 - scheme checked above
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"{url} returned HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach {url}: {exc.reason}") from exc


@dataclass
class WindowPlan:
    """How a back end wants the recording cut up, and why.

    ``note`` is empty when the caller's own settings were kept. When it is not,
    it says what changed and what forced the change, because a run that quietly
    describes the video in different chunks than the user asked for is a run
    whose output they cannot reason about.
    """

    frame_interval: int
    window_seconds: int
    note: str = ""

    @property
    def changed(self) -> bool:
        return bool(self.note)


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

    @classmethod
    def plan_windows(cls, frame_interval: int, window_seconds: int,
                     machine=None) -> WindowPlan:
        """Accept the requested windowing, or shrink it to what this can finish.

        Hosted models cope with whatever they are sent, so the default is to
        change nothing. A back end that has a fixed context window or runs on
        the user's own processor overrides this.
        """
        return WindowPlan(frame_interval, window_seconds)


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
        #
        # The final synthesis step sends no images -- it works from the text of
        # the sections. Asking it to "read these image files" and then listing
        # none made the model open its answer by complaining that no images
        # arrived, and that complaint ended up in the finished document.
        full_prompt = prompt
        if images:
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


class OllamaBackend(VisionBackend):
    """A vision model running on this computer, served by Ollama.

    The only option that needs no account and sends nothing over the internet,
    which matters when the footage must not leave the machine. It is also the
    slowest and the least accurate: a 2-4 billion parameter model reads a large
    sign reliably, but struggles with the small embroidered text on a uniform
    that a frontier model picks out. Offer it for privacy, not for quality.

    Ollama listens on localhost:11434 and pulls models on demand.
    """

    name = "ollama"
    DEFAULT_MODEL = "qwen2.5vl:3b"
    BASE_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")

    # Ollama gives a model a 4096-token context unless asked otherwise, and one
    # frame of a 1280x720 video costs about 900 tokens once encoded. A default
    # 120-second window holds twelve frames, so the request arrives at roughly
    # 10800 tokens and Ollama rejects the whole thing with HTTP 400 instead of
    # answering about the frames that did fit. The context is therefore sized
    # from the images actually being sent. 1100 leaves room for frames from a
    # larger source than the one this was measured on.
    TOKENS_PER_FRAME = 1100
    # Below this, sizing the context down buys nothing and risks clipping the
    # prompt; above it, a CPU spends longer on the prefill than on the answer.
    MIN_CONTEXT = 4096
    MAX_CONTEXT = 32768

    # Frames per request. Cost does not grow linearly: on a 16-core CPU three
    # frames answered in under two minutes, while twelve frames had not
    # answered when REQUEST_TIMEOUT expired at ten. Four is the largest batch
    # measured to finish comfortably. A graphics card is roughly an order of
    # magnitude faster, so it keeps the ordinary default.
    MAX_FRAMES_PER_REQUEST_CPU = 4
    MAX_FRAMES_PER_REQUEST_GPU = 12

    # Vision models small enough to be usable on a normal laptop, with the
    # memory each one needs and how long each spends per frame on a CPU.
    #
    # Only the qwen2.5vl:3b figure is measured: 9 frames of a 1280x720 video
    # took about 12 minutes on 16 cores with no graphics card, inside the real
    # pipeline. That is 80 seconds a frame, against the 25 this table used to
    # claim -- the earlier number came from a bare prompt rather than the full
    # one, which carries the window's dialogue as well. The others are scaled
    # from it by size and remain estimates. Better to quote a discouraging
    # number that holds up than a cheerful one that does not.
    MODELS = {
        "moondream": {"gb": 2.0, "ram_gb": 4, "seconds_per_frame": 48},
        "qwen2.5vl:3b": {"gb": 3.2, "ram_gb": 8, "seconds_per_frame": 80},
        "llava:7b": {"gb": 4.7, "ram_gb": 12, "seconds_per_frame": 145},
        "qwen2.5vl:7b": {"gb": 6.0, "ram_gb": 16, "seconds_per_frame": 175},
    }

    # A graphics card is roughly an order of magnitude faster than a CPU here.
    GPU_SPEEDUP = 10.0

    @classmethod
    def is_available(cls) -> bool:
        """True when an Ollama server answers on this machine."""
        try:
            url = _check_http_url(cls.BASE_URL + "/api/tags")
            with urllib.request.urlopen(url, timeout=3):  # noqa: S310  # nosec B310 - scheme checked
                return True
        except (urllib.error.URLError, OSError, RuntimeError):
            return False

    @classmethod
    def why_unavailable(cls) -> str:
        if shutil.which("ollama"):
            return "Ollama is installed but not running. Start it and try again."
        return ("Ollama is not installed. It runs a vision model on this computer, "
                "with no account and nothing sent over the internet. "
                "Get it from https://ollama.com")

    @classmethod
    def installed_models(cls) -> list[str]:
        """Vision models already pulled on this machine."""
        try:
            url = _check_http_url(cls.BASE_URL + "/api/tags")
            with urllib.request.urlopen(url, timeout=5) as response:  # noqa: S310  # nosec B310 - scheme checked
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError, RuntimeError):
            return []
        names = [entry.get("name", "") for entry in data.get("models", [])]
        # Match on the family so "qwen2.5vl:3b" also matches a "-q4_K_M" variant.
        return [name for name in names
                if any(name.startswith(known.split(":")[0]) for known in cls.MODELS)]

    @classmethod
    def recommend_model(cls, ram_gb: float) -> str:
        """The largest vision model this machine can hold comfortably."""
        affordable = [name for name, spec in cls.MODELS.items()
                      if ram_gb <= 0 or ram_gb - 2 >= spec["ram_gb"]]
        return affordable[-1] if affordable else "moondream"

    @classmethod
    def seconds_per_frame(cls, model: str, machine=None) -> float:
        """How long one frame takes on this computer, in seconds."""
        cost = cls.MODELS.get(model, cls.MODELS[cls.DEFAULT_MODEL])["seconds_per_frame"]
        if machine is not None and getattr(machine, "has_gpu", False):
            return cost / cls.GPU_SPEEDUP
        return float(cost)

    @classmethod
    def verdict(cls, machine, model: str = "") -> tuple[str, str]:
        """Whether running the local model here is a good idea.

        Returns ``(level, explanation)`` where level is ``recommended`` on a
        machine with a graphics card, ``slow`` when it will work but take
        several times the length of the recording, and ``unusable`` when the
        model will not fit in memory.

        The local model is never hidden outright, however poor the verdict: it
        is the only option that sends nothing over the internet, and that is
        sometimes the whole reason for choosing it. It is only kept out of the
        recommended slot, with the cost stated plainly.

        ``model`` defaults to the one the pipeline actually runs when nothing
        is configured, not to the largest that would fit. Quoting a cost for a
        model the user has not got, and would not use, is worse than useless:
        it is a number they will plan around.
        """
        model = model or cls.DEFAULT_MODEL
        spec = cls.MODELS.get(model, cls.MODELS[cls.DEFAULT_MODEL])
        ram = getattr(machine, "ram_gb", 0.0)

        # Leave about 2 GB for the operating system, as system.can_run does.
        if ram > 0 and ram - 2.0 < spec["ram_gb"]:
            return "unusable", t("vision.local_no_ram", model=model,
                                 needed=spec["ram_gb"], have=f"{ram:.0f}")

        if getattr(machine, "has_gpu", False):
            return "recommended", t("vision.local_gpu",
                                    gpu=getattr(machine, "gpu_name", ""))

        # Frames are sampled every frame_interval seconds, so the cost per
        # second of video is seconds_per_frame / frame_interval. At the default
        # of one frame per 10 s and 80 s a frame, that is 8x the recording.
        ratio = cls.seconds_per_frame(model, machine) / 10.0
        return "slow", t("vision.local_slow", model=model, ratio=f"{ratio:.0f}")

    @classmethod
    def max_frames_per_request(cls, machine=None) -> int:
        """How many frames this computer can describe in one request."""
        if machine is not None and getattr(machine, "has_gpu", False):
            return cls.MAX_FRAMES_PER_REQUEST_GPU
        return cls.MAX_FRAMES_PER_REQUEST_CPU

    @classmethod
    def plan_windows(cls, frame_interval: int, window_seconds: int,
                     machine=None) -> WindowPlan:
        """Shorten the window until a request holds a manageable number of frames.

        The frame interval is left alone: it decides how much of the video is
        looked at, and dropping frames to fit would silently reduce coverage.
        Shortening the window keeps every frame and sends more, smaller
        requests instead.
        """
        limit = cls.max_frames_per_request(machine)
        frames = max(1, window_seconds // max(frame_interval, 1))
        if frames <= limit:
            return WindowPlan(frame_interval, window_seconds)

        adjusted = max(frame_interval, frame_interval * limit)
        return WindowPlan(
            frame_interval, adjusted,
            t("vision.window_shrunk", backend=cls.name, before=window_seconds,
              after=adjusted, frames=limit),
        )

    @classmethod
    def context_size(cls, image_count: int, prompt: str, num_predict: int) -> int:
        """Tokens of context needed to hold this request and its answer.

        Undersizing loses the whole request, so every term is rounded up: four
        characters per token is generous for Spanish, and the answer has to fit
        in the same window as the question.
        """
        needed = image_count * cls.TOKENS_PER_FRAME + len(prompt) // 3 + num_predict
        return max(cls.MIN_CONTEXT, min(cls.MAX_CONTEXT, needed))

    def generate(self, prompt: str, images: list[Path], model: str) -> str:
        # Long enough for a full paragraph about a two-minute stretch.
        num_predict = 1600
        payload = {
            "model": model or self.DEFAULT_MODEL,
            "prompt": prompt,
            "images": [_read_image_as_base64(path) for path in images],
            "stream": False,
            "options": {
                "num_predict": num_predict,
                "num_ctx": self.context_size(len(images), prompt, num_predict),
            },
        }
        response = _post_json(self.BASE_URL + "/api/generate", payload, {})
        return (response.get("response") or "").strip()


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
    "ollama": OllamaBackend,
    "none": DisabledBackend,
}

# Models each back end should use when the config leaves the choice open.
DEFAULT_MODELS: dict[str, tuple[str, str]] = {
    # backend: (per-window vision model, final synthesis model)
    "claude-cli": ("sonnet", "opus"),
    "anthropic": ("claude-sonnet-5", "claude-opus-5"),
    "openai": ("gpt-4o", "gpt-4o"),
    "gemini": ("gemini-2.0-flash", "gemini-2.0-flash"),
    "ollama": ("qwen2.5vl:3b", "qwen2.5vl:3b"),
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


def is_configured(machine=None) -> bool:
    """True when some model could describe the picture right now.

    The transcript never needs one, so this decides whether the visual
    description is offered at all. Offering it and failing later wastes the
    user's time on a video that may take half an hour to transcribe.
    """
    return any(ready for _, ready, _ in available_backends(machine))


def available_backends(machine=None) -> list[tuple[str, bool, str]]:
    """List every back end as ``(name, available, explanation)`` for the doctor.

    Pass a :class:`~videoscribe.system.MachineProfile` to have the local back
    end report what it will actually cost here. "Ready" on its own is
    misleading for a model that runs on the user's own processor: it is ready
    in the sense that it will start, not in the sense that it will finish today.
    """
    rows = []
    for name, backend_class in BACKENDS.items():
        if name == "none":
            continue
        ready = backend_class.is_available()
        if not ready:
            rows.append((name, False, backend_class.why_unavailable()))
            continue

        explanation = "ready"
        if machine is not None and hasattr(backend_class, "verdict"):
            level, note = backend_class.verdict(machine)
            # A model too big for this machine is not "ready" in any useful
            # sense, so it is reported as unavailable rather than as a caveat.
            if level == "unusable":
                rows.append((name, False, note))
                continue
            explanation = note if level == "slow" else f"ready -- {note}"
        rows.append((name, ready, explanation))
    return rows
