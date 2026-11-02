"""Turn a django-starter source tree into a new project: variant markers, pruning, renaming and ``.env``."""

import os
import re
import secrets
from pathlib import Path

# `# >>> web`, `<!-- >>> web -->` or `{# >>> web #}` opens a block; `<<< web` closes it. A `web` block is kept
# (without its markers) in the full variant and dropped from the API variant. A `starter` block holds text that
# only makes sense in the starter repo itself and is always dropped.
BLOCK_MARKER = re.compile(r"^\s*(#|<!--|\{#)\s*(>>>|<<<)\s*(web|starter)\b")

# `# api-only: <code>` is a commented-out line that the API variant uncomments.
API_ONLY = re.compile(r"^(\s*)# api-only: (.*)$")

# Removed from the API variant. Entries ending in "/" are directories.
API_REMOVED_PATHS = (
    "templates/",
    "assets/",
    "static/css/",
    "static/javascript/",
    "static/images/undraw/",
    "static/images/web/",
    "package.json",
    "package-lock.json",
    ".npmrc",
    ".github/workflows/build_frontend.yml",
    "apps/web/views.py",
    "apps/web/urls.py",
    "apps/web/forms.py",
    "apps/web/sitemaps.py",
    "apps/web/meta.py",
    "apps/web/context_processors.py",
    "apps/web/templatetags/",
    "apps/users/views.py",
    "apps/users/urls.py",
    "apps/users/forms.py",
    "apps/web/tests/test_basic_views.py",
    "apps/web/tests/test_logged_in_views.py",
    "apps/web/tests/test_meta_tags.py",
    "apps/web/tests/test_admin_dashboard.py",
    "apps/users/tests/test_profile.py",
    ".cursor/rules/django-templates.mdc",
    ".cursor/rules/javascript-guidelines.mdc",
)

# Kept in the API variant even though a parent is in API_REMOVED_PATHS: allauth still sends these emails.
API_KEPT_PATHS = ("templates/account/email/",)

# Removed from every generated project: the generator itself and the workflows that publish it.
ALWAYS_REMOVED_PATHS = (
    "cli/",
    ".github/workflows/publish_cli.yml",
    ".github/workflows/starter_cli.yml",
)

DEFAULT_EMAIL = "admin@example.com"


class RenderError(Exception):
    """The source tree could not be rendered, e.g. because of unbalanced variant markers."""


def process_text(text: str, api: bool, path: str = "<text>") -> str:
    """Apply the web/starter blocks and api-only markers for the chosen variant to one file's text."""
    out = []
    # Line number of the open block for each tag, or None. Blocks of different tags may overlap.
    open_blocks: dict[str, int | None] = {"web": None, "starter": None}
    for lineno, line in enumerate(text.splitlines(keepends=True), start=1):
        body = line.rstrip("\r\n")
        marker = BLOCK_MARKER.match(body)
        if marker:
            direction, tag = marker.group(2), marker.group(3)
            start = open_blocks[tag]
            if direction == ">>>":
                if start is not None:
                    raise RenderError(f"{path}:{lineno}: '>>> {tag}' inside the block opened on line {start}.")
                open_blocks[tag] = lineno
            else:
                if start is None:
                    raise RenderError(f"{path}:{lineno}: '<<< {tag}' without a matching '>>> {tag}'.")
                open_blocks[tag] = None
            continue
        if open_blocks["starter"] is not None or (api and open_blocks["web"] is not None):
            continue
        api_only = API_ONLY.match(body)
        if api_only:
            if api:
                out.append(api_only.group(1) + api_only.group(2) + line[len(body) :])
            continue
        out.append(line)
    for tag, start in open_blocks.items():
        if start is not None:
            raise RenderError(f"{path}:{start}: '>>> {tag}' is never closed with '<<< {tag}'.")
    return "".join(out)


def _matches(rel: str, patterns: tuple[str, ...]) -> bool:
    return any(rel.startswith(p) if p.endswith("/") else rel == p for p in patterns)


def removed_paths(api: bool) -> tuple[str, ...]:
    return ALWAYS_REMOVED_PATHS + API_REMOVED_PATHS if api else ALWAYS_REMOVED_PATHS


def prune(root: Path, api: bool) -> list[str]:
    """Delete the paths that do not belong in the chosen variant. Returns the removed files, relative to root."""
    patterns = removed_paths(api)
    removed = []
    emptied_dirs = set()
    for dirpath, dirnames, filenames in os.walk(root):
        directory = Path(dirpath)
        # Symlinks to directories are listed in dirnames but not walked; remove them like files.
        links = [d for d in dirnames if (directory / d).is_symlink()]
        for name in filenames + links:
            path = directory / name
            rel = path.relative_to(root).as_posix()
            if _matches(rel, patterns) and not _matches(rel, API_KEPT_PATHS if api else ()):
                path.unlink()
                removed.append(rel)
                emptied_dirs.add(directory)
    for directory in sorted(emptied_dirs, key=lambda d: len(d.parts), reverse=True):
        while directory != root and directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()
            directory = directory.parent
    return sorted(removed)


def rename_map(slug: str, email: str = DEFAULT_EMAIL) -> dict[str, str]:
    """Template names and contact details mapped to the new project's values."""
    return {
        "CHRISDEVCODE_": slug.upper().replace("-", "_") + "_",
        "chrisdevcode": slug,
        "django-starter": slug,
        "django-template": slug,
        "achinga.chris@gmail.com": email,
    }


def rename(text: str, slug: str, email: str = DEFAULT_EMAIL) -> str:
    """Replace the template's names in one pass, so a slug containing an old name is not replaced again."""
    mapping = rename_map(slug, email)
    pattern = re.compile("|".join(re.escape(k) for k in sorted(mapping, key=len, reverse=True)))
    return pattern.sub(lambda m: mapping[m.group(0)], text)


def read_text(path: Path) -> str | None:
    """The file's text, or None for binary or non-UTF-8 files."""
    data = path.read_bytes()
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def render_tree(root: Path, api: bool, slug: str, email: str = DEFAULT_EMAIL) -> None:
    """Apply the variant markers and renaming to every UTF-8 text file under root."""
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            path = Path(dirpath) / name
            if path.is_symlink():
                continue
            text = read_text(path)
            if text is None:
                continue
            rel = path.relative_to(root).as_posix()
            new = rename(process_text(text, api, rel), slug, email)
            if new != text:
                path.write_text(new, encoding="utf-8", newline="")


def write_env(root: Path) -> bool:
    """Create .env from .env.example with a fresh SECRET_KEY. Returns False if there is no .env.example."""
    example = root / ".env.example"
    if not example.is_file():
        return False
    text = example.read_bytes().decode("utf-8")
    secret_line = f'SECRET_KEY="{secrets.token_urlsafe(50)}"'
    text, count = re.subn(r"^SECRET_KEY=[^\r\n]*", lambda _: secret_line, text, count=1, flags=re.MULTILINE)
    if not count:
        text = text.rstrip("\n") + f"\n{secret_line}\n"
    (root / ".env").write_text(text, encoding="utf-8", newline="")
    return True


def render_project(root: Path, *, api: bool, slug: str, email: str = DEFAULT_EMAIL) -> None:
    """Turn a copied source tree into the chosen variant of a new project, in place."""
    prune(root, api)
    render_tree(root, api, slug, email)
    write_env(root)
