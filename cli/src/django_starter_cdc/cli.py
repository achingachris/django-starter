"""Command line entry point: ``django-starter-cdc new <name> [options]``."""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from django_starter_cdc import __version__
from django_starter_cdc.fetch import FetchError, archive_url, copy_local, download
from django_starter_cdc.render import DEFAULT_EMAIL, RenderError, render_project

# A lowercase slug that starts with a letter and ends with a letter or digit, e.g. "shop" or "my-shop_2".
NAME_RE = re.compile(r"^[a-z](?:[a-z0-9_-]*[a-z0-9])?$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class CLIError(Exception):
    """Invalid input from the command line."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="django-starter-cdc",
        description="Generate a new Django 6.1 project from django-starter.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True, metavar="command")

    new = commands.add_parser(
        "new",
        help="create a new project",
        description="Create a new project. The full variant has templates, HTMX, Alpine.js and Tailwind; "
        "--api gives an API-only project (DRF + allauth headless, no templates or npm).",
    )
    new.add_argument("name", help="project name: a lowercase slug of letters, digits, hyphens and underscores")
    new.add_argument("--api", action="store_true", help="API-only variant: no templates, front end or npm")
    new.add_argument(
        "--email", default=DEFAULT_EMAIL, help=f"admin and default from-address email (default: {DEFAULT_EMAIL})"
    )
    source = new.add_mutually_exclusive_group()
    source.add_argument(
        "--ref",
        help=f"git ref (branch, tag or commit) to download instead of the v{__version__} release, e.g. main",
    )
    source.add_argument("--source", type=Path, metavar="PATH", help="copy a local django-starter checkout instead")
    new.add_argument("--no-install", action="store_true", help="skip `make init` (dependencies and migrations)")
    new.add_argument("--no-git", action="store_true", help="skip `git init`")
    new.add_argument(
        "--dir", type=Path, default=Path("."), metavar="PATH", help="parent directory for the project (default: .)"
    )
    return parser


def validate(args: argparse.Namespace) -> Path:
    """Check the name, email and target directory. Returns the project directory to create."""
    if not NAME_RE.match(args.name):
        raise CLIError(
            f"Invalid project name {args.name!r}: use lowercase letters, digits, hyphens and underscores, "
            "starting with a letter and ending with a letter or digit."
        )
    if not EMAIL_RE.match(args.email):
        raise CLIError(f"Invalid email address {args.email!r}.")
    target = args.dir.expanduser().resolve() / args.name
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise CLIError(f"{target} already exists and is not an empty directory.")
    return target


def run(command: list[str], cwd: Path) -> bool:
    print(f"$ {' '.join(command)}")
    return subprocess.run(command, cwd=cwd).returncode == 0


def manual_steps(name: str, api: bool) -> list[str]:
    steps = [f"cd {name}", "uv sync"]
    if not api:
        steps.append("npm install && npm run build")
    steps.append("uv run python manage.py migrate")
    return steps


def install(target: Path, api: bool) -> bool:
    """Run `make init` when its tools are available. Returns False if the user has to finish setup by hand."""
    tools = ["make", "uv"] if api else ["make", "uv", "npm"]
    missing = [tool for tool in tools if shutil.which(tool) is None]
    if missing:
        print(f"\nSkipping `make init`: {', '.join(missing)} not found on PATH.")
        return False
    if run(["make", "init"], target):
        return True
    print("\n`make init` failed; see the output above.", file=sys.stderr)
    return False


def print_next_steps(target: Path, api: bool, installed: bool) -> None:
    print(f"\nCreated {'API-only' if api else 'full'} project in {target}\n")
    if installed:
        print("Next steps:\n")
        print(f"  cd {target.name}")
    else:
        print("Finish the setup:\n")
        print("\n".join(f"  {step}" for step in manual_steps(target.name, api)))
    print("  make start\n")
    print("Then open:")
    print("  http://localhost:8000/admin/                  Django admin")
    print("  http://localhost:8000/api/schema/swagger-ui/  API docs")
    if api:
        print("  http://localhost:8000/_allauth/openapi.html   auth API docs (allauth headless)")


def create_project(args: argparse.Namespace) -> int:
    target = validate(args)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{args.name}-", dir=target.parent) as tmp:
        stage = Path(tmp) / args.name
        if args.source:
            print(f"Copying {args.source.resolve()}")
            copy_local(args.source, stage, exclude=(Path(tmp), target))
        else:
            print(f"Downloading {archive_url(args.ref)}")
            download(stage, args.ref)
        print(f"Rendering the {'API-only' if args.api else 'full'} variant")
        render_project(stage, api=args.api, slug=args.name, email=args.email)
        if target.exists():
            target.rmdir()
        stage.rename(target)

    if not args.no_git:
        if shutil.which("git"):
            run(["git", "init", "-q"], target)
        else:
            print("Skipping `git init`: git not found on PATH.")
    installed = not args.no_install and install(target, args.api)
    print_next_steps(target, args.api, installed)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return create_project(args)
    except (CLIError, FetchError, RenderError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
