"""Fetching ffmpeg when it is not already on the computer.

Being told "ffmpeg is missing, go install it" is a dead end for someone who has
never opened a terminal. So when it is missing we offer to fetch it, and the
offer has to work without administrator rights: a lawyer on a managed work
laptop usually cannot run an installer, and often has no package manager at all.

Two routes, tried in this order:

1. **The system package manager** -- winget, apt, dnf, pacman, zypper, brew.
   Installs system-wide, needs elevation, but leaves ffmpeg on the PATH for
   every other program too.
2. **A portable static build**, downloaded into ``tools/ffmpeg/`` next to this
   repository. No elevation, nothing registered with the operating system, and
   deleting the folder undoes it completely. The path is recorded in ``.env``
   so later runs find it.

Nothing here downloads anything without being asked first. The caller shows the
size and the source, and only calls in once the user has agreed.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .config import REPO_ROOT, save_setting

# Static builds that need no installer and no administrator rights.
#
# These are the download pages the projects themselves point at. They are
# checked at run time rather than pinned to a version, because a pinned URL
# rots and a broken download is worse than a slightly newer ffmpeg.
PORTABLE_BUILDS = {
    "windows-amd64": {
        "url": "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
        "size_mb": 40,
        "source": "gyan.dev (the build ffmpeg.org links to for Windows)",
        "archive": "zip",
    },
    "linux-amd64": {
        "url": "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz",
        "size_mb": 30,
        "source": "johnvansickle.com (the static build ffmpeg.org links to for Linux)",
        "archive": "tar.xz",
    },
    "linux-arm64": {
        "url": "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz",
        "size_mb": 30,
        "source": "johnvansickle.com (the static build ffmpeg.org links to for Linux)",
        "archive": "tar.xz",
    },
}

# How each package manager installs ffmpeg, and whether it needs elevation.
PACKAGE_MANAGERS = [
    ("winget", ["winget", "install", "--id", "Gyan.FFmpeg",
                "--accept-source-agreements", "--accept-package-agreements", "--silent"], False),
    ("brew", ["brew", "install", "ffmpeg"], False),
    ("apt-get", ["sudo", "apt-get", "install", "-y", "ffmpeg"], True),
    ("dnf", ["sudo", "dnf", "install", "-y", "ffmpeg"], True),
    ("pacman", ["sudo", "pacman", "-S", "--noconfirm", "ffmpeg"], True),
    ("zypper", ["sudo", "zypper", "install", "-y", "ffmpeg"], True),
]


@dataclass
class InstallOption:
    """One way of getting ffmpeg onto this machine."""

    kind: str            # "package-manager" or "portable"
    label: str           # what to show the user
    detail: str          # size, source, and whether elevation is needed
    needs_admin: bool


def portable_key() -> str | None:
    """Identify which portable build fits this machine, if any."""
    machine = platform.machine().lower()
    architecture = "arm64" if machine in {"arm64", "aarch64"} else "amd64"

    if os.name == "nt":
        return "windows-amd64" if architecture == "amd64" else None
    if platform.system() == "Linux":
        return f"linux-{architecture}"
    # macOS static builds are distributed as a signed .zip per component and
    # Homebrew is near-universal there, so we do not offer a portable route.
    return None


def available_package_manager() -> tuple[str, list[str], bool] | None:
    """The first package manager present on this machine, if any."""
    for name, command, needs_sudo in PACKAGE_MANAGERS:
        if shutil.which(name):
            return name, command, needs_sudo
    return None


def install_options() -> list[InstallOption]:
    """Every way ffmpeg could be installed here, best first."""
    options: list[InstallOption] = []

    manager = available_package_manager()
    if manager:
        name, _, needs_sudo = manager
        options.append(InstallOption(
            kind="package-manager",
            label=f"Install with {name}",
            detail=("asks for your password" if needs_sudo else
                    "may ask Windows for permission" if name == "winget" else
                    "no password needed"),
            needs_admin=needs_sudo or name == "winget",
        ))

    key = portable_key()
    if key:
        build = PORTABLE_BUILDS[key]
        options.append(InstallOption(
            kind="portable",
            label="Download a portable copy",
            detail=f"about {build['size_mb']} MB from {build['source']}; "
                   "no permissions needed, goes in the tools folder",
            needs_admin=False,
        ))

    return options


def install_with_package_manager(on_message=print) -> str | None:
    """Run the system package manager. Returns the ffmpeg path, or None."""
    manager = available_package_manager()
    if not manager:
        return None
    name, command, _ = manager

    on_message(f"Running: {' '.join(command)}")
    on_message("This can take a few minutes.")
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        on_message(f"{name} exited with code {result.returncode}.")
        return None

    # A fresh install is not on the PATH of this already-running process.
    from .tools import ToolMissing, find_ffmpeg

    try:
        return find_ffmpeg()
    except ToolMissing:
        on_message("Installed, but not visible until this window is reopened.")
        return None


def _zip_names_staying_inside(bundle: zipfile.ZipFile, destination: Path) -> list[str]:
    """Return the archive's entry names, refusing any that escape ``destination``.

    ``ZipFile.extractall`` already drops drive letters and ``..`` segments, but
    that is an implementation detail of the standard library rather than a
    promise. Checking here costs nothing and means the Windows route -- the one
    most users take -- is guarded by the same rule as the Linux one.
    """
    root = destination.resolve()
    names = bundle.namelist()
    for name in names:
        if not (root / name).resolve().is_relative_to(root):
            raise ValueError(f"Archive entry escapes the target folder: {name}")
    return names


def _members_staying_inside(bundle: tarfile.TarFile, destination: Path):
    """Yield only the archive entries that unpack inside ``destination``.

    A tar entry may name ``../../etc/something`` or be a symlink pointing out
    of the tree, and plain ``extractall`` will happily follow it. Python's
    ``filter="data"`` refuses those, but it is missing from older releases, and
    the fallback used to be an unfiltered extract -- which is precisely the
    thing being guarded against. This does the check by hand instead, so an
    old Python is slower to unpack rather than unsafe.
    """
    root = destination.resolve()
    for member in bundle.getmembers():
        target = (root / member.name).resolve()
        if not target.is_relative_to(root):
            raise ValueError(f"Archive entry escapes the target folder: {member.name}")
        if member.issym() or member.islnk():
            link = (target.parent / member.linkname).resolve()
            if not link.is_relative_to(root):
                raise ValueError(f"Archive link points outside: {member.name}")
        yield member


def _download(url: str, target: Path, on_progress=None) -> Path:
    """Fetch a URL to a file, reporting bytes as they arrive."""
    # Only ever fetch over TLS. Without this a tampered build table -- or a
    # redirect -- could name file:// and have the "download" read local disk.
    if not url.lower().startswith("https://"):
        raise ValueError(f"Refusing to download over anything but HTTPS: {url}")

    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "VideoScribe"})  # noqa: S310 - HTTPS enforced above

    with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310  # nosec B310 - HTTPS enforced above
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        with target.open("wb") as handle:
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                done += len(chunk)
                if on_progress:
                    on_progress(done, total)
    return target


def _find_binary(root: Path, name: str) -> Path | None:
    """Locate ffmpeg/ffprobe inside an unpacked archive."""
    wanted = name + (".exe" if os.name == "nt" else "")
    for candidate in root.rglob(wanted):
        if candidate.is_file():
            return candidate
    return None


def install_portable(on_message=print, on_progress=None) -> str | None:
    """Download and unpack a static ffmpeg into ``tools/ffmpeg``.

    Returns the path to the ffmpeg binary, or None if it could not be done.
    """
    key = portable_key()
    if not key:
        on_message("No portable build is available for this system.")
        return None

    build = PORTABLE_BUILDS[key]
    tools_dir = REPO_ROOT / "tools" / "ffmpeg"
    tools_dir.mkdir(parents=True, exist_ok=True)
    archive = tools_dir / ("download.zip" if build["archive"] == "zip" else "download.tar.xz")

    on_message(f"Downloading about {build['size_mb']} MB from {build['source']}")
    try:
        _download(build["url"], archive, on_progress)
    except Exception as exc:  # noqa: BLE001 - network failures take many shapes
        on_message(f"Download failed: {exc}")
        on_message(f"You can fetch it by hand from: {build['url']}")
        return None

    on_message("Unpacking...")
    unpacked = tools_dir / "unpacked"
    if unpacked.exists():
        shutil.rmtree(unpacked, ignore_errors=True)
    unpacked.mkdir(parents=True)

    try:
        if build["archive"] == "zip":
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(  # noqa: S202  # nosec B202 - names validated by _zip_names_staying_inside
                    unpacked, members=_zip_names_staying_inside(bundle, unpacked)
                )
        else:
            with tarfile.open(archive) as bundle:
                # filter="data" refuses absolute paths and symlinks pointing
                # outside the destination. Older Pythons lack it, so the same
                # check is applied by hand rather than extracting unfiltered.
                try:
                    bundle.extractall(unpacked, filter="data")  # noqa: S202 - filtered
                except TypeError:
                    bundle.extractall(  # noqa: S202  # nosec B202 - members validated by _members_staying_inside
                        unpacked, members=_members_staying_inside(bundle, unpacked)
                    )
    except Exception as exc:  # noqa: BLE001
        on_message(f"Could not unpack the download: {exc}")
        return None
    finally:
        archive.unlink(missing_ok=True)

    ffmpeg = _find_binary(unpacked, "ffmpeg")
    if not ffmpeg:
        on_message("The download did not contain an ffmpeg program.")
        return None

    if os.name != "nt":
        for binary in (ffmpeg, _find_binary(unpacked, "ffprobe")):
            if binary:
                binary.chmod(0o755)

    # Remember it, so the next run finds it without searching.
    save_setting("VIDEOSCRIBE_FFMPEG", str(ffmpeg))
    on_message(f"Ready: {ffmpeg}")
    on_message("Recorded in .env, so it will be found automatically from now on.")
    return str(ffmpeg)
