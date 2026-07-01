"""
Auto-update checker — queries GitHub Releases for new versions.

Cross-platform: works identically on Windows and macOS.
The only platform difference is which download asset is selected
(.exe installer on Windows, .dmg on macOS).

Version format: "1.2" / "1.2.1" — compared as tuples of ints.
"""

import sys
import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional


# ── Single source of truth for the current version ─────────────────
# When bumping the version (update.ps1 / update_mac.sh), this constant
# MUST be updated together with installer.nsi, i18n.py, .spec files.
VERSION = "1.4.0"

GITHUB_REPO = "Yvonne6475/TwelveToneAnalyzer"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


@dataclass
class UpdateInfo:
    """Structured result from the update check."""
    has_update: bool
    current_version: str
    latest_version: str
    release_notes: str       # Markdown
    download_url: str        # platform-appropriate asset URL
    download_name: str       # filename
    download_size: int       # bytes, 0 if unknown
    html_url: str            # GitHub release page (fallback)


def _parse_version(v: str) -> tuple[int, ...]:
    """Parse "1.2" or "v1.2.1" into a comparable tuple."""
    v = v.strip().lstrip("v")
    return tuple(int(x) for x in v.split(".") if x.isdigit())


def _is_newer(latest: str, current: str) -> bool:
    """Return True if *latest* is strictly greater than *current*."""
    return _parse_version(latest) > _parse_version(current)


def check_for_updates(timeout: int = 10) -> Optional[UpdateInfo]:
    """Query GitHub Releases for the latest version.

    Returns an UpdateInfo if a newer version exists, None if up-to-date,
    or raises ConnectionError / ValueError on network/parse failures.
    """
    try:
        req = urllib.request.Request(
            RELEASES_API,
            headers={"Accept": "application/vnd.github+json",
                     "User-Agent": "TwelveToneAnalyzer-Update/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 403:
            raise ConnectionError("GitHub API rate-limited. Try again later.")
        if e.code == 404:
            raise ConnectionError("No releases found on GitHub.")
        raise ConnectionError(f"GitHub API error: {e.code}")
    except urllib.error.URLError as e:
        raise ConnectionError(f"Cannot reach GitHub: {e.reason}")
    except json.JSONDecodeError:
        raise ValueError("Invalid response from GitHub API.")

    latest_tag = data.get("tag_name", "").lstrip("v")
    if not latest_tag:
        raise ValueError("Release has no tag_name.")

    if not _is_newer(latest_tag, VERSION):
        return None  # Already up to date

    # ── Pick platform-appropriate download asset ──────────────
    is_mac = sys.platform == "darwin"
    download_url = data.get("html_url", "")
    download_name = ""
    download_size = 0

    for asset in data.get("assets", []):
        name = asset.get("name", "")
        if is_mac and name.endswith(".dmg"):
            download_url = asset["browser_download_url"]
            download_name = name
            download_size = asset.get("size", 0)
            break
        if (not is_mac) and (name.endswith(".exe") and "Setup" in name):
            download_url = asset["browser_download_url"]
            download_name = name
            download_size = asset.get("size", 0)
            break

    # Fallback: use the first asset
    if not download_name and data.get("assets"):
        asset = data["assets"][0]
        download_url = asset["browser_download_url"]
        download_name = asset.get("name", "")
        download_size = asset.get("size", 0)

    return UpdateInfo(
        has_update=True,
        current_version=VERSION,
        latest_version=latest_tag,
        release_notes=data.get("body", ""),
        download_url=download_url,
        download_name=download_name,
        download_size=download_size,
        html_url=data.get("html_url", ""),
    )
