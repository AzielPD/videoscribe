"""The version is written in three places, and they must agree.

`VERSION` is what a user reads, `videoscribe.__version__` is what the program
reports, and `CHANGELOG.md` is what explains the difference between releases.
Bumping one and forgetting another is the easiest mistake to make and the
hardest to notice, because nothing breaks -- the program simply lies about
which version it is.
"""

from __future__ import annotations

import re
from pathlib import Path

import videoscribe

REPO_ROOT = Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def version_file() -> str:
    return (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()


def changelog_versions() -> list[str]:
    """Every version heading in the changelog, newest first."""
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    return re.findall(r"^##\s+(\d+\.\d+\.\d+)", text, re.M)


class TestVersionsAgree:
    def test_version_file_matches_the_package(self):
        assert version_file() == videoscribe.__version__

    def test_changelog_leads_with_the_current_version(self):
        assert changelog_versions()[0] == version_file()

    def test_the_version_is_a_plain_semver(self):
        assert SEMVER.match(version_file()), f"{version_file()!r} is not X.Y.Z"


class TestChangelogIsUsable:
    def test_it_has_at_least_one_release(self):
        assert changelog_versions()

    def test_versions_are_listed_newest_first(self):
        as_numbers = [tuple(int(n) for n in v.split(".")) for v in changelog_versions()]
        assert as_numbers == sorted(as_numbers, reverse=True)

    def test_no_version_appears_twice(self):
        found = changelog_versions()
        assert len(found) == len(set(found))

    def test_every_release_has_a_date(self):
        """A release with no date cannot be placed against anything else."""
        text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        for heading in re.findall(r"^##\s+.*$", text, re.M):
            assert re.search(r"\d{4}-\d{2}-\d{2}", heading), heading
