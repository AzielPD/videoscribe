"""Configuration loading for VideoScribe.

Settings are resolved with the following precedence (highest first):

1. Command-line arguments        ``--model medium``
2. Environment variables / .env  ``VIDEOSCRIBE_MODEL=medium``
3. ``config.json``               ``{"transcription": {"model": "medium"}}``
4. Built-in defaults             (see ``DEFAULTS`` below)

This means a user can ship a shared ``config.json`` in the repository and still
override any single value on their own machine through ``.env``, without
editing tracked files.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

# Root of the repository (the folder that contains config.json, inbox/, ...)
REPO_ROOT = Path(__file__).resolve().parent.parent

# Every setting, its default value, and the environment variable that overrides
# it. The dotted key is the path inside config.json.
DEFAULTS: dict[str, Any] = {
    # --- Interface --------------------------------------------------------
    # Empty means "ask the operating system, and fall back to English".
    "ui.language": "",
    # --- Audio extraction -------------------------------------------------
    "audio.mp3_bitrate": "128k",
    "audio.sample_rate": 16000,
    # --- Speech to text ---------------------------------------------------
    "transcription.model": "small",
    "transcription.language": "es",
    "transcription.compute_type": "int8",
    "transcription.beam_size": 5,
    "transcription.cpu_threads": 0,  # 0 = use every available core (max 16)
    # --- Speaker separation ----------------------------------------------
    "speakers.count": 0,  # 0 = detect automatically
    "speakers.max_count": 6,
    "speakers.label": "Person",  # produces Person1, Person2, ...
    # --- Visual narration -------------------------------------------------
    "narration.enabled": True,
    "narration.frame_interval_seconds": 10,
    "narration.window_seconds": 120,
    "narration.max_frame_edge": 1568,
    "narration.vision_model": "sonnet",
    "narration.synthesis_model": "opus",
    "narration.output_language": "Spanish",
    # --- Folders ----------------------------------------------------------
    "paths.inbox": "inbox",
    "paths.output": "output",
    "paths.ffmpeg": "",  # empty = search PATH and the usual install folders
    # --- Housekeeping -----------------------------------------------------
    "cleanup.keep_wav": False,
    "cleanup.keep_frames": False,
}

# Environment variable name for each dotted key.
ENV_OVERRIDES: dict[str, str] = {
    "ui.language": "VIDEOSCRIBE_UI_LANGUAGE",
    "audio.mp3_bitrate": "VIDEOSCRIBE_MP3_BITRATE",
    "transcription.model": "VIDEOSCRIBE_MODEL",
    "transcription.language": "VIDEOSCRIBE_LANGUAGE",
    "transcription.compute_type": "VIDEOSCRIBE_COMPUTE_TYPE",
    "transcription.cpu_threads": "VIDEOSCRIBE_CPU_THREADS",
    "speakers.count": "VIDEOSCRIBE_SPEAKERS",
    "speakers.max_count": "VIDEOSCRIBE_MAX_SPEAKERS",
    "speakers.label": "VIDEOSCRIBE_SPEAKER_LABEL",
    "narration.enabled": "VIDEOSCRIBE_NARRATION",
    "narration.frame_interval_seconds": "VIDEOSCRIBE_FRAME_INTERVAL",
    "narration.window_seconds": "VIDEOSCRIBE_WINDOW_SECONDS",
    "narration.vision_model": "VIDEOSCRIBE_VISION_MODEL",
    "narration.synthesis_model": "VIDEOSCRIBE_SYNTHESIS_MODEL",
    "narration.output_language": "VIDEOSCRIBE_NARRATION_LANGUAGE",
    "paths.inbox": "VIDEOSCRIBE_INBOX",
    "paths.output": "VIDEOSCRIBE_OUTPUT",
    "paths.ffmpeg": "VIDEOSCRIBE_FFMPEG",
    "cleanup.keep_wav": "VIDEOSCRIBE_KEEP_WAV",
    "cleanup.keep_frames": "VIDEOSCRIBE_KEEP_FRAMES",
}

_TRUE = {"1", "true", "yes", "y", "on", "si", "sí"}
_FALSE = {"0", "false", "no", "n", "off"}


def _coerce(value: Any, like: Any) -> Any:
    """Convert a string coming from .env into the type of the default value."""
    if not isinstance(value, str):
        return value
    text = value.strip()
    if isinstance(like, bool):
        low = text.lower()
        if low in _TRUE:
            return True
        if low in _FALSE:
            return False
        raise ValueError(f"Expected a yes/no value, got {value!r}")
    if isinstance(like, int):
        return int(text)
    if isinstance(like, float):
        return float(text)
    return text


def load_dotenv(path: Path) -> dict[str, str]:
    """Read a ``.env`` file into a dict. Missing file yields an empty dict.

    Supports ``KEY=value`` lines, ``#`` comments, and optional quotes. Values
    are not expanded or interpolated -- what you write is what you get.
    """
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        values[key.strip()] = val
    return values


def _dig(data: dict, dotted: str) -> Any:
    """Fetch ``a.b.c`` from a nested dict, or None when any level is missing."""
    node: Any = data
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


@dataclass
class Config:
    """Resolved settings for one run.

    Values live in a flat dict keyed by the dotted names listed in
    :data:`DEFAULTS`. Read them through :meth:`get` or the typed properties
    below -- the properties exist so that a typo becomes an AttributeError
    instead of a silent ``None``.
    """

    values: dict[str, Any] = field(default_factory=dict)

    def get(self, dotted: str, default: Any = None) -> Any:
        return self.values.get(dotted, default)

    # --- Audio ------------------------------------------------------------
    @property
    def mp3_bitrate(self) -> str:
        return self.values["audio.mp3_bitrate"]

    @property
    def sample_rate(self) -> int:
        return self.values["audio.sample_rate"]

    # --- Transcription ----------------------------------------------------
    @property
    def model(self) -> str:
        return self.values["transcription.model"]

    @property
    def language(self) -> str:
        return self.values["transcription.language"]

    @property
    def compute_type(self) -> str:
        return self.values["transcription.compute_type"]

    @property
    def beam_size(self) -> int:
        return self.values["transcription.beam_size"]

    @property
    def cpu_threads(self) -> int:
        configured = self.values["transcription.cpu_threads"]
        return configured if configured > 0 else min(16, os.cpu_count() or 4)

    # --- Speakers ---------------------------------------------------------
    @property
    def speaker_count(self) -> int:
        return self.values["speakers.count"]

    @property
    def max_speakers(self) -> int:
        return self.values["speakers.max_count"]

    @property
    def speaker_label(self) -> str:
        return self.values["speakers.label"]

    # --- Narration --------------------------------------------------------
    @property
    def narration_enabled(self) -> bool:
        return self.values["narration.enabled"]

    @property
    def frame_interval(self) -> int:
        return self.values["narration.frame_interval_seconds"]

    @property
    def window_seconds(self) -> int:
        return self.values["narration.window_seconds"]

    @property
    def max_frame_edge(self) -> int:
        return self.values["narration.max_frame_edge"]

    @property
    def vision_model(self) -> str:
        return self.values["narration.vision_model"]

    @property
    def synthesis_model(self) -> str:
        return self.values["narration.synthesis_model"]

    @property
    def narration_language(self) -> str:
        return self.values["narration.output_language"]

    # --- Interface --------------------------------------------------------
    @property
    def ui_language(self) -> str:
        """The chosen interface language, or empty to detect it."""
        return self.values["ui.language"]

    # --- Folders and housekeeping ----------------------------------------
    @property
    def ffmpeg_override(self) -> str:
        return self.values["paths.ffmpeg"]

    @property
    def keep_wav(self) -> bool:
        return self.values["cleanup.keep_wav"]

    @property
    def keep_frames(self) -> bool:
        return self.values["cleanup.keep_frames"]

    @property
    def inbox_dir(self) -> Path:
        return self._resolve_dir(self.values["paths.inbox"])

    @property
    def output_dir(self) -> Path:
        return self._resolve_dir(self.values["paths.output"])

    @staticmethod
    def _resolve_dir(value: str) -> Path:
        path = Path(value).expanduser()
        return path if path.is_absolute() else (REPO_ROOT / path)

    def describe(self) -> str:
        """Human-readable dump, used by ``videoscribe doctor``."""
        width = max(len(k) for k in self.values)
        lines = []
        for key in sorted(self.values):
            lines.append(f"  {key.ljust(width)} = {self.values[key]!r}")
        return "\n".join(lines)


def load_config(
    config_path: Path | None = None,
    env_path: Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> Config:
    """Build a :class:`Config` from defaults, config.json, .env and CLI args.

    Parameters
    ----------
    config_path:
        Path to ``config.json``. Defaults to the one next to this repository.
    env_path:
        Path to ``.env``. Defaults to the one next to this repository.
    overrides:
        Dotted-key values from the command line. ``None`` entries are ignored,
        so callers can pass argparse results directly.
    """
    values = dict(DEFAULTS)

    # 2nd priority source: config.json
    config_path = config_path or (REPO_ROOT / "config.json")
    if config_path.is_file():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"config.json is not valid JSON: {exc}") from exc
        for key in DEFAULTS:
            found = _dig(data, key)
            if found is not None:
                values[key] = _coerce(found, DEFAULTS[key])

    # 3rd priority source: .env file, then real environment variables
    env_path = env_path or (REPO_ROOT / ".env")
    dotenv = load_dotenv(env_path)
    for key, env_name in ENV_OVERRIDES.items():
        raw = os.environ.get(env_name, dotenv.get(env_name))
        if raw is not None and raw != "":
            try:
                values[key] = _coerce(raw, DEFAULTS[key])
            except ValueError as exc:
                raise SystemExit(f"{env_name}: {exc}") from exc

    # Highest priority: explicit command-line arguments
    for key, val in (overrides or {}).items():
        if val is not None:
            values[key] = val

    return Config(values)


def save_setting(key_env_name: str, value: str, env_path: Path | None = None) -> Path:
    """Write one ``NAME=value`` into ``.env``, replacing any existing line.

    Used when the user changes something from the menu and expects it to stick.
    Only ``.env`` is ever written; ``config.json`` is left alone because it is
    the shared, version-controlled file.
    """
    env_path = env_path or (REPO_ROOT / ".env")
    lines = env_path.read_text(encoding="utf-8-sig").splitlines() if env_path.is_file() else []

    replaced = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        if stripped.split("=", 1)[0].strip() == key_env_name:
            lines[index] = f"{key_env_name}={value}"
            replaced = True
            break

    if not replaced:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(f"{key_env_name}={value}")

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return env_path
