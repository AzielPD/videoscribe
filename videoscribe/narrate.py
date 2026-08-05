"""Building a written account of a video from its frames and its transcript.

The recording is cut into windows of a couple of minutes. For each window the
chosen vision model receives the frames of that stretch together with the words
spoken during it, and writes one paragraph describing what happens. A final
pass joins the paragraphs into a single continuous account.

Two rules shape the prompts, and both exist because of the intended readers:

* **Say only what is there.** Anything inferred must be marked as such, and
  unreadable text must be reported as unreadable rather than guessed.
* **Never invent a timecode.** Every ``[HH:MM:SS]`` is checked against the real
  frame and transcript times for that window, and removed if it does not match
  (see :func:`videoscribe.timecode.strip_invented_timecodes`). A wrong timecode
  sends a reader to the wrong minute of a long recording.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .timecode import format_timecode, strip_invented_timecodes
from .vision import VisionBackend

# Openers a model tends to prepend despite being told not to.
#
# The second group is the model talking about its own situation rather than
# about the video -- "I don't see any image files attached", "Unfortunately I
# cannot". One of those reached a finished account, in English, at the top of a
# Spanish document meant for a court file. Whatever the prompt says, this is the
# last thing standing between the model's chatter and the reader.
PREAMBLE_PATTERN = re.compile(
    r"^\s*(here (is|are)|i (will|'ll|have)|now i|let me|based on|looking at|"
    r"the following|sure|certainly|okay|ok|understood|perfect|"
    r"i (don't|do not|can't|cannot|couldn't|could not|'m|am)\b|"
    r"(it|that) (looks|seems|appears)\b|unfortunately|note that|apologies|"
    r"(sorry|thanks|thank you)\b|that said)\b",
    re.IGNORECASE,
)

# A horizontal rule the model draws between its remarks and the real answer.
SEPARATOR_PATTERN = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")

WINDOW_RULES = """\
Rules:
- Describe ONLY what can be seen in the frames and heard in the audio. Mark
  anything you infer with "apparently" or "it seems".
- Quote any readable text exactly: signs, badges, uniforms, documents, figures
  on paper. If text cannot be read, say so instead of guessing.
- Refer to people by their visible role or appearance. Do not invent names or
  job titles that are not shown in the video.
- The transcript is produced automatically and contains errors. Flag any figure
  or word that sounds doubtful.
- TIMECODES: whenever you cite a time in square brackets, COPY IT EXACTLY from
  the lists above. Never estimate, calculate or interpolate one. If something
  has no time in the lists, cite no time for it.
- Answer with the paragraph only. No headings, no bullet points, no preamble.
  Start with the narrative itself.
"""

SYNTHESIS_RULES = """\
Write all of the above into ONE continuous account, in the third person, that
tells what happened from beginning to end.

- Join the sections into a single story and remove repetition.
- Keep the concrete details: readable text, figures, documents handed over,
  job titles visible on clothing or badges.
- Keep the square-bracket timecodes so each fact can be checked against the
  video. Copy them exactly as they appear above; never invent one.
- Keep the distinction between what the video shows and what is interpretation
  ("apparently", "it seems").
- Do not add any fact that is not in the sections above.
- Answer with the account only.
"""


@dataclass
class Window:
    """One stretch of video handed to the vision model as a unit."""

    index: int
    start: float
    end: float
    frames: list[tuple[float, Path]] = field(default_factory=list)
    dialogue: list[dict] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.frames and not self.dialogue

    def allowed_timecodes(self) -> set[str]:
        """Exactly the times this window is permitted to cite."""
        stamps = {format_timecode(second) for second, _ in self.frames}
        stamps |= {format_timecode(line["start"]) for line in self.dialogue}
        return stamps

    def build_prompt(self, speaker_label: str, output_language: str) -> str:
        """Assemble the instruction sent to the vision model."""
        lines = [
            "Analyse one stretch of a video recording.",
            f"Stretch: {format_timecode(self.start)} to {format_timecode(self.end)}.",
            "",
            "FRAMES (the time of each frame comes first):",
        ]
        for second, path in self.frames:
            lines.append(f"  [{format_timecode(second)}] {path}")
        if not self.frames:
            lines.append("  (no frames available for this stretch)")

        lines += ["", "TRANSCRIPT OF THE AUDIO FOR THE SAME STRETCH:"]
        if not self.dialogue:
            lines.append("  (no speech detected in this stretch)")
        for line in self.dialogue:
            speaker = f"{speaker_label}{line.get('speaker', 1)}"
            lines.append(f"  [{format_timecode(line['start'])}] {speaker}: {line['text']}")

        lines += [
            "",
            "Write one narrative paragraph describing what happens in this stretch,",
            "combining what is SEEN with what is HEARD.",
            f"Write it in {output_language}, in the third person.",
            "",
            WINDOW_RULES,
        ]
        return "\n".join(lines)


def strip_preamble(text: str) -> str:
    """Drop leading remarks such as "Here is the paragraph:" or an apology.

    Only ever removes from the front, and never the last remaining line, so a
    short account that happens to begin with one of these words survives. The
    account itself is what the reader takes to court; the model's remarks about
    its own working conditions are not part of it.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    while len(lines) > 1:
        first = lines[0].strip()
        looks_like_preamble = (
            bool(PREAMBLE_PATTERN.match(first))
            or bool(SEPARATOR_PATTERN.match(first))
            # A short line ending in a colon is introducing what follows.
            or (first.endswith(":") and len(first) < 160)
        )
        if not looks_like_preamble:
            break
        lines = lines[1:]
        while len(lines) > 1 and not lines[0].strip():
            lines = lines[1:]
    return "\n".join(lines).strip()


def build_windows(
    frames: list[Path],
    segments: list[dict],
    total_seconds: float,
    frame_interval: int,
    window_seconds: int,
    offset: float = 0.0,
) -> list[Window]:
    """Split the recording into windows carrying their frames and dialogue.

    Frame *n* (counting from one) was taken at ``offset + (n - 1) * interval``
    seconds, which is how a file name becomes a position in the video.
    """
    timed_frames = [
        (offset + index * frame_interval, path) for index, path in enumerate(frames)
    ]

    windows: list[Window] = []
    count = max(1, int((total_seconds + window_seconds - 1) // window_seconds))
    for index in range(count):
        start = offset + index * window_seconds
        end = min(offset + total_seconds, start + window_seconds)
        windows.append(
            Window(
                index=index,
                start=start,
                end=end,
                frames=[(sec, path) for sec, path in timed_frames if start <= sec < end],
                dialogue=[
                    line for line in segments if line["end"] > start and line["start"] < end
                ],
            )
        )
    return windows


def narrate_window(
    backend: VisionBackend,
    window: Window,
    model: str,
    speaker_label: str,
    output_language: str,
) -> tuple[str, int]:
    """Describe one window. Returns ``(paragraph, invented_timecodes_removed)``."""
    prompt = window.build_prompt(speaker_label, output_language)
    answer = backend.generate(prompt, [path for _, path in window.frames], model)
    if not answer.strip():
        raise RuntimeError("The vision model returned an empty answer.")
    cleaned, removed = strip_invented_timecodes(
        strip_preamble(answer), window.allowed_timecodes()
    )
    return cleaned, removed


def build_synthesis_prompt(paragraphs: list[tuple[Window, str]], output_language: str) -> str:
    """Assemble the final pass that turns the paragraphs into one account."""
    lines = [
        "Below are paragraphs describing, in chronological order, the stretches of",
        "a video recording. Each one combines what is visible in the frames with",
        "what is audible in the sound.",
        "",
    ]
    for window, paragraph in paragraphs:
        lines += [f"## {format_timecode(window.start)}", "", paragraph, ""]
    lines += ["", f"Write the final account in {output_language}.", "", SYNTHESIS_RULES]
    return "\n".join(lines)


def synthesise(
    backend: VisionBackend,
    paragraphs: list[tuple[Window, str]],
    model: str,
    output_language: str,
) -> str:
    """Join per-window paragraphs into one continuous account."""
    prompt = build_synthesis_prompt(paragraphs, output_language)
    allowed: set[str] = set()
    for window, _ in paragraphs:
        allowed |= window.allowed_timecodes()

    answer = backend.generate(prompt, [], model)
    if not answer.strip():
        raise RuntimeError("The vision model returned an empty final account.")
    cleaned, _ = strip_invented_timecodes(strip_preamble(answer), allowed)
    return cleaned
