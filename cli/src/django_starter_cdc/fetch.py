"""Get the django-starter source tree: from a local checkout or a GitHub release tarball."""

import shutil
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from django_starter_cdc import __version__

REPO_URL = "https://github.com/achingachris/django-starter"

# Skipped by name wherever they appear in a local checkout.
IGNORED_NAMES = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "__pycache__",
        ".ruff_cache",
        ".mypy_cache",
        ".pytest_cache",
        ".DS_Store",
        ".idea",
        ".vscode",
        ".playwright-mcp",
    }
)

# Skipped only at these paths, relative to the checkout root: build output, local data and secrets.
IGNORED_PATHS = frozenset(
    {
        "cli",
        "db.sqlite3",
        "static/vendor",
        "static/css",
        "static_root",
        "media",
        ".env",
        ".env.prod",
        ".claude/settings.local.json",
    }
)


class FetchError(Exception):
    """The template source could not be copied or downloaded."""


def archive_url(ref: str | None = None) -> str:
    """URL of the source tarball: the release tag matching this CLI's version, or any git ref."""
    if ref:
        return f"{REPO_URL}/archive/{ref}.tar.gz"
    return f"{REPO_URL}/archive/refs/tags/v{__version__}.tar.gz"


def copy_local(source: Path, dest: Path) -> None:
    """Copy a local checkout into ``dest``, leaving out VCS data, dependencies, build output and secrets."""
    source = source.resolve()
    if not (source / "manage.py").is_file():
        raise FetchError(f"{source} does not look like a django-starter checkout (no manage.py).")

    def ignore(directory: str, names: list[str]) -> set[str]:
        rel_dir = Path(directory).resolve().relative_to(source)
        ignored = set()
        for name in names:
            rel = (rel_dir / name).as_posix()
            if name in IGNORED_NAMES or rel in IGNORED_PATHS:
                ignored.add(name)
        return ignored

    shutil.copytree(source, dest, ignore=ignore, symlinks=True)


def download(dest: Path, ref: str | None = None) -> None:
    """Download and extract the source tarball into ``dest``, stripping its single top-level folder."""
    url = archive_url(ref)
    with tempfile.TemporaryDirectory(prefix="django-starter-cdc-") as tmp:
        archive = Path(tmp) / "source.tar.gz"
        request = urllib.request.Request(url, headers={"User-Agent": f"django-starter-cdc/{__version__}"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response, archive.open("wb") as fh:
                shutil.copyfileobj(response, fh)
        except urllib.error.HTTPError as e:
            hint = "" if ref else " Pass --ref main to use the latest code instead of a release."
            raise FetchError(f"Could not download {url}: HTTP {e.code}.{hint}") from e
        except urllib.error.URLError as e:
            raise FetchError(f"Could not download {url}: {e.reason}") from e

        extracted = Path(tmp) / "extracted"
        try:
            with tarfile.open(archive, "r:gz") as tar:
                tar.extractall(extracted, filter="data")
        except (tarfile.TarError, OSError) as e:
            raise FetchError(f"Could not extract {url}: {e}") from e

        entries = list(extracted.iterdir())
        if len(entries) != 1 or not entries[0].is_dir():
            raise FetchError(f"Unexpected archive layout in {url}: expected a single top-level folder.")
        shutil.move(entries[0], dest)
