"""Working out what this computer can handle, and recommending a model.

The toolkit ships with ``small`` as the default because it runs anywhere and
finishes a one-hour recording in about half an hour on a normal laptop. But a
machine with a graphics card, or with plenty of cores and memory, can run a
noticeably more accurate model. Rather than making the user guess, we measure
the machine and say so.

Nothing here changes any setting on its own; it produces a recommendation the
caller can accept or ignore.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .i18n import t
from .timecode import format_duration

# Rough cost of each model relative to `small`, from published benchmarks and
# measurements on this toolkit. Used only to estimate how long a run will take.
MODEL_COST = {
    "tiny": 0.25,
    "base": 0.45,
    "small": 1.00,
    "medium": 2.60,
    "large-v2": 7.50,
    "large-v3": 8.00,
}

# Approximate download size, so the user knows what they are agreeing to.
MODEL_DOWNLOAD_MB = {
    "tiny": 75,
    "base": 145,
    "small": 480,
    "medium": 1500,
    "large-v2": 3100,
    "large-v3": 3100,
}

# Memory needed to load the model with int8 quantisation, in GB.
MODEL_RAM_GB = {
    "tiny": 1.0,
    "base": 1.2,
    "small": 2.0,
    "medium": 5.0,
    "large-v2": 10.0,
    "large-v3": 10.0,
}

# On a 16-core CPU, `small` transcribed 50 minutes of audio in 19 minutes,
# i.e. it processed 2.7 seconds of audio per second of wall clock.
REFERENCE_CORES = 16
REFERENCE_SPEED = 2.7  # x real time, for `small`, at REFERENCE_CORES


@dataclass
class MachineProfile:
    """What we could find out about the computer."""

    cores: int
    ram_gb: float
    free_disk_gb: float
    gpu_name: str = ""
    gpu_vram_gb: float = 0.0
    platform_name: str = ""

    @property
    def has_gpu(self) -> bool:
        return bool(self.gpu_name) and self.gpu_vram_gb > 0

    def summary(self) -> list[str]:
        """Human-readable description, in the user's chosen language."""
        lines = [
            t("machine.system", value=self.platform_name),
            t("machine.cores", value=self.cores),
            t("machine.memory", value=f"{self.ram_gb:.1f}"),
            t("machine.disk", value=f"{self.free_disk_gb:.1f}"),
        ]
        if self.has_gpu:
            lines.append(t("machine.gpu", name=self.gpu_name,
                           vram=f"{self.gpu_vram_gb:.1f}"))
        else:
            lines.append(t("machine.no_gpu"))
        return lines


def _detect_ram_gb() -> float:
    """Total physical memory in GB, best effort across platforms."""
    # POSIX (Linux, most BSDs, and macOS)
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return pages * page_size / (1024 ** 3)
    except (ValueError, OSError, AttributeError):
        pass

    if os.name == "nt":
        try:
            import ctypes

            class MemoryStatusEx(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatusEx()
            status.dwLength = ctypes.sizeof(MemoryStatusEx)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return status.ullTotalPhys / (1024 ** 3)
        except (ImportError, OSError, AttributeError):
            pass

    return 0.0


def _detect_gpu() -> tuple[str, float]:
    """Return (name, VRAM in GB) for an NVIDIA card, or ("", 0.0)."""
    # Prefer torch when it is installed: it reports what will actually be usable.
    try:
        import torch

        if torch.cuda.is_available():
            properties = torch.cuda.get_device_properties(0)
            return properties.name, properties.total_memory / (1024 ** 3)
    except (ImportError, RuntimeError, AssertionError):
        pass

    # Otherwise ask the driver directly.
    if shutil.which("nvidia-smi"):
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=15, check=False,
            )
            first = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
            if "," in first:
                name, _, memory = first.partition(",")
                return name.strip(), float(memory.strip()) / 1024.0
        except (OSError, subprocess.SubprocessError, ValueError, IndexError):
            pass

    return "", 0.0


def profile_machine(disk_target: Path | None = None) -> MachineProfile:
    """Measure the current computer."""
    target = disk_target or Path.home()
    try:
        free_gb = shutil.disk_usage(target).free / (1024 ** 3)
    except OSError:
        free_gb = 0.0

    gpu_name, gpu_vram = _detect_gpu()
    return MachineProfile(
        cores=os.cpu_count() or 1,
        ram_gb=_detect_ram_gb(),
        free_disk_gb=free_gb,
        gpu_name=gpu_name,
        gpu_vram_gb=gpu_vram,
        platform_name=f"{platform.system()} {platform.release()} ({platform.machine()})",
    )


def recommend_model(machine: MachineProfile) -> tuple[str, str]:
    """Pick the largest model this machine can run comfortably.

    Returns ``(model_name, reason)``. The reason is written for someone who has
    never heard of a transcription model.
    """
    if machine.has_gpu and machine.gpu_vram_gb >= 8:
        return "large-v3", t("recommend.gpu_large", gpu=machine.gpu_name)
    if machine.has_gpu and machine.gpu_vram_gb >= 5:
        return "medium", t("recommend.gpu_medium", gpu=machine.gpu_name)

    # 15.0 rather than 16.0: a nominal 16 GB machine reports about 15.7 GB once
    # firmware and integrated graphics have taken their share.
    if machine.ram_gb >= 15.0 and machine.cores >= 12:
        return "medium", t("recommend.cpu_medium",
                           cores=machine.cores, ram=f"{machine.ram_gb:.0f}")
    if machine.ram_gb >= 8 and machine.cores >= 4:
        return "small", t("recommend.cpu_small")
    return "base", t("recommend.cpu_base")


def estimate_runtime(model: str, audio_seconds: float, machine: MachineProfile) -> float:
    """Estimated wall-clock seconds to transcribe ``audio_seconds`` of audio."""
    cost = MODEL_COST.get(model, 1.0)

    if machine.has_gpu:
        # A mid-range card runs roughly 12x real time on `small`, and scales far
        # better than a CPU with model size.
        speed = 12.0 / (cost ** 0.6)
    else:
        core_ratio = max(machine.cores, 1) / REFERENCE_CORES
        # Speed grows with cores but with diminishing returns.
        speed = REFERENCE_SPEED * (core_ratio ** 0.7) / cost

    return audio_seconds / max(speed, 0.05)


def describe_choice(model: str, audio_seconds: float, machine: MachineProfile) -> str:
    """One line describing what running ``model`` on this audio would cost."""
    runtime = estimate_runtime(model, audio_seconds, machine)
    download = MODEL_DOWNLOAD_MB.get(model, 0)
    return f"{model:<9} {format_duration(runtime):<22} first-time download {download} MB"


def can_run(model: str, machine: MachineProfile) -> bool:
    """False when the model would not fit in this machine's memory."""
    needed = MODEL_RAM_GB.get(model, 2.0)
    if machine.has_gpu and machine.gpu_vram_gb >= needed:
        return True
    # Leave about 2 GB for the operating system and everything else.
    return machine.ram_gb <= 0 or machine.ram_gb - 2.0 >= needed


def model_is_downloaded(model: str) -> bool:
    """True when the model is already in the Hugging Face cache."""
    cache = Path.home() / ".cache" / "huggingface" / "hub"
    if not cache.is_dir():
        return False
    return any(cache.glob(f"models--*faster-whisper-{model}"))
