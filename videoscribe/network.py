"""Checking that the servers this toolkit needs are actually reachable.

Corporate networks block by destination, not by protocol, so "I have internet"
and "I can download a model" are different questions. This module answers the
second one, per service, and says what each service is for.

The failure that prompted this: on a network running Fortinet, Ollama's manifest
server answered in 268 ms while the Cloudflare bucket holding the actual model
weights timed out. ``ollama pull`` showed a spinner labelled "pulling manifest"
and nothing else; the real cause was only visible in Ollama's own log file. A
user without that log would conclude the tool was broken.

Two failure kinds are reported separately, because the fix differs:

* **blocked** -- the name resolves but the connection times out or is refused.
  Something between this machine and the server is dropping it. Ask whoever runs
  the network, or use a different one.
* **unreachable** -- the name does not resolve at all. Usually no internet, or
  DNS is down. When *everything* fails this way, say that instead of listing
  twelve separate blockages.

**What this cannot tell you.** A TCP handshake proves the route opens; it says
nothing about whether a multi-gigabyte download will survive. On the network
that prompted this module, `r2.cloudflarestorage.com` answered in 313 ms and was
reported "ok", while the actual model download crawled at 0.13 MB/s with the
server logging "stalled; retrying" throughout. A firewall can allow the
connection and then throttle or drop the transfer. Say "ok" here to mean the
route is open, never that a download will finish.
"""

from __future__ import annotations

import socket
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

# Anything slower than this is unusable for a multi-gigabyte download anyway.
TIMEOUT_SECONDS = 8.0


@dataclass(frozen=True)
class Endpoint:
    """One server, and why this toolkit would ever talk to it."""

    label: str
    host: str
    port: int
    purpose_key: str          # i18n key explaining what it is for
    required: bool            # False when only an optional feature needs it


# Ordered so the things everyone needs come first.
ENDPOINTS = [
    # Two hosts, because they can be blocked independently: huggingface.co
    # answers the "which file do I need" question, and the CDN below serves the
    # file itself. Hugging Face moved that CDN to the Xet bridge on hf.co; the
    # older cdn-lfs.huggingface.co no longer resolves at all, and listing it
    # here produced a false "BLOCKED" on a network where downloads worked fine.
    # Verify with a real download before changing these:
    #   https://huggingface.co/Systran/faster-whisper-tiny/resolve/main/model.bin
    Endpoint("huggingface.co", "huggingface.co", 443,
             "network.purpose_whisper", required=True),
    Endpoint("us.aws.cdn.hf.co", "us.aws.cdn.hf.co", 443,
             "network.purpose_whisper_files", required=True),

    # The portable ffmpeg download offered when ffmpeg is missing.
    Endpoint("gyan.dev", "www.gyan.dev", 443,
             "network.purpose_ffmpeg_windows", required=False),
    Endpoint("johnvansickle.com", "johnvansickle.com", 443,
             "network.purpose_ffmpeg_linux", required=False),

    # Ollama: the manifest and the weights live on different hosts, and only
    # the second one was blocked. Checking just the first would have missed it.
    Endpoint("registry.ollama.ai", "registry.ollama.ai", 443,
             "network.purpose_ollama_manifest", required=False),
    Endpoint("r2.cloudflarestorage.com",
             "dd20bb891979d25aebc8bec07b2b3bbc.r2.cloudflarestorage.com",
             443, "network.purpose_ollama_weights", required=False),

    # Cloud image models, for the visual description.
    Endpoint("api.anthropic.com", "api.anthropic.com", 443,
             "network.purpose_anthropic", required=False),
    Endpoint("api.openai.com", "api.openai.com", 443,
             "network.purpose_openai", required=False),
    Endpoint("generativelanguage.googleapis.com", "generativelanguage.googleapis.com", 443,
             "network.purpose_gemini", required=False),
]

# The Ollama server, when it is running on this machine. Not an internet check,
# but it belongs on the same screen.
LOCAL_OLLAMA = Endpoint("localhost:11434", "127.0.0.1", 11434,
                        "network.purpose_ollama_local", required=False)


@dataclass
class Result:
    """What happened when we tried to reach one endpoint."""

    endpoint: Endpoint
    ok: bool
    milliseconds: int = 0
    kind: str = ""            # "" | "blocked" | "unreachable"

    @property
    def status_word(self) -> str:
        if self.ok:
            return "ok"
        return self.kind or "blocked"


def check_endpoint(endpoint: Endpoint, timeout: float = TIMEOUT_SECONDS) -> Result:
    """Open a TCP connection and close it again.

    A TCP handshake is enough: it proves the firewall lets traffic through to
    that host and port. Fetching an actual file would be slower, would need
    credentials for some of these, and would not tell us anything more about
    whether the route is open.
    """
    started = time.monotonic()
    try:
        connection = socket.create_connection((endpoint.host, endpoint.port), timeout=timeout)
        connection.close()
        return Result(endpoint, True, int((time.monotonic() - started) * 1000))
    except socket.gaierror:
        # The name did not resolve: no DNS, or no network at all.
        return Result(endpoint, False, kind="unreachable")
    except TimeoutError:
        return Result(endpoint, False, kind="blocked")
    except OSError:
        # Refused, unreachable host, and similar. From a user's point of view
        # this is the same situation as a timeout: something is in the way.
        return Result(endpoint, False, kind="blocked")


def check_all(include_local: bool = True, timeout: float = TIMEOUT_SECONDS) -> list[Result]:
    """Check every endpoint at once. Takes about as long as the slowest one."""
    targets = list(ENDPOINTS)
    if include_local:
        targets.append(LOCAL_OLLAMA)

    with ThreadPoolExecutor(max_workers=len(targets)) as pool:
        return list(pool.map(lambda e: check_endpoint(e, timeout), targets))


def diagnose(results: list[Result]) -> str:
    """Turn the results into one sentence, as an i18n key.

    Returning a key rather than a sentence keeps this module free of language.
    The caller translates it.
    """
    internet = [r for r in results if r.endpoint is not LOCAL_OLLAMA]
    if not internet:
        return ""

    failed = [r for r in internet if not r.ok]
    if not failed:
        return "network.all_reachable"

    if all(r.kind == "unreachable" for r in failed) and len(failed) == len(internet):
        return "network.no_internet"

    if any(r.endpoint.required and not r.ok for r in internet):
        return "network.required_blocked"

    return "network.some_blocked"


def blocked_features(results: list[Result]) -> list[str]:
    """i18n keys naming what will not work, given what is blocked.

    Grouped by feature rather than by host, because "you cannot download a
    local vision model" is actionable and "r2.cloudflarestorage.com timed out"
    is not.
    """
    by_host = {r.endpoint.label: r for r in results}

    def down(*labels: str) -> bool:
        return any(label in by_host and not by_host[label].ok for label in labels)

    broken: list[str] = []
    if down("huggingface.co", "us.aws.cdn.hf.co"):
        broken.append("network.broken_whisper")
    if down("registry.ollama.ai", "r2.cloudflarestorage.com"):
        broken.append("network.broken_ollama")
    if down("api.anthropic.com") and down("api.openai.com") and \
            down("generativelanguage.googleapis.com"):
        broken.append("network.broken_cloud_vision")
    if down("gyan.dev", "johnvansickle.com"):
        broken.append("network.broken_ffmpeg")
    return broken
