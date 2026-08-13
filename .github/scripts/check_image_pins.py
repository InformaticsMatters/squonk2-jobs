#!/usr/bin/env python3
"""Check every container image pinned by a Job Definition.

Two questions, and they fail very differently:

1. **Does the pinned tag exist?** If not the Job cannot run at all. Two
   `silicos-it` Jobs pinned `3dechem/silicos-it:stable` - a tag that had never
   been published - and shipped that way for years, in a deployed manifest,
   without anything noticing. That is an error.

2. **How old is the image behind the tag?** A dynamic tag (`latest`, `stable`)
   is re-pulled by the Data Manager, so a stale one means users are running old
   code with nothing to signal it. That is a warning, not an error: most of the
   estate is stale today for reasons that need a decision rather than a commit
   (see issue #43), and failing the build on it would just be noise.

Run it locally the same way CI does:

    python3 .github/scripts/check_image_pins.py

Exit status is 1 if any pinned tag is missing, 0 otherwise (unless
--fail-on-stale is given).
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
from typing import Iterator, NamedTuple

import yaml

# Job Definitions declare their image as 'image: {name: ..., tag: ...}'. The
# same shape appears nested (e.g. under a test's 'image'), so we walk rather
# than index a fixed path.
JOB_DEFINITION_KIND = "DataManagerJobDefinition"

HUB_API = "https://hub.docker.com/v2/repositories/{repo}/tags/{tag}"
DEFAULT_MAX_AGE_DAYS = 365
TIMEOUT_SECONDS = 30


class Pin(NamedTuple):
    """One 'name:tag' pin, and where it came from."""

    image: str
    tag: str
    sources: set[str]

    @property
    def ref(self) -> str:
        return f"{self.image}:{self.tag}"


class Result(NamedTuple):
    pin: Pin
    exists: bool
    last_pushed: datetime.date | None
    note: str


def find_job_definitions(root: pathlib.Path) -> Iterator[pathlib.Path]:
    """Yield every Job Definition file, skipping the decoder's own fixtures."""
    for path in sorted(root.glob("*/data-manager/**/*.yaml")):
        if "example-definitions" in path.parts:
            continue
        try:
            content = yaml.safe_load(path.read_text())
        except (yaml.YAMLError, UnicodeDecodeError):
            continue
        if isinstance(content, dict) and content.get("kind") == JOB_DEFINITION_KIND:
            yield path


def walk_for_images(node: object, source: str, found: dict[tuple[str, str], set[str]]) -> None:
    """Collect every {name, tag} pair anywhere in a definition."""
    if isinstance(node, dict):
        name, tag = node.get("name"), node.get("tag")
        if isinstance(name, str) and isinstance(tag, (str, int, float)):
            found.setdefault((name, str(tag)), set()).add(source)
        for value in node.values():
            walk_for_images(value, source, found)
    elif isinstance(node, list):
        for value in node:
            walk_for_images(value, source, found)


def collect_pins(root: pathlib.Path) -> list[Pin]:
    found: dict[tuple[str, str], set[str]] = {}
    for path in find_job_definitions(root):
        source = str(path.relative_to(root))
        walk_for_images(yaml.safe_load(path.read_text()), source, found)
    return [Pin(image, tag, sources) for (image, tag), sources in sorted(found.items())]


def is_docker_hub(image: str) -> bool:
    """False for images hosted on a named registry (e.g. quay.io/org/name)."""
    head = image.split("/")[0]
    return "/" not in image or ("." not in head and ":" not in head)


def hub_repo_path(image: str) -> str:
    """Docker Hub official images live under 'library/'."""
    return image if "/" in image else f"library/{image}"


def check(pin: Pin, today: datetime.date) -> Result:
    if not is_docker_hub(pin.image):
        # Existence could be checked via the registry v2 API, but staleness
        # could not - so report rather than pass silently.
        return Result(pin, True, None, "not on Docker Hub - not checked")

    url = HUB_API.format(repo=hub_repo_path(pin.image), tag=pin.tag)
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return Result(pin, False, None, "tag does not exist")
        return Result(pin, True, None, f"could not check (HTTP {error.code})")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        return Result(pin, True, None, f"could not check ({type(error).__name__})")

    stamp = (data.get("last_updated") or "")[:10]
    try:
        pushed = datetime.date(*(int(part) for part in stamp.split("-")))
    except (TypeError, ValueError):
        return Result(pin, True, None, "no push date reported")
    return Result(pin, True, pushed, "")


def render(results: list[Result], max_age_days: int, today: datetime.date) -> tuple[str, int, int]:
    missing = [r for r in results if not r.exists]
    stale = [
        r
        for r in results
        if r.exists and r.last_pushed and (today - r.last_pushed).days > max_age_days
    ]

    lines = ["| Image | Tag | Exists | Last pushed | Age | Used by |",
             "| ----- | --- | ------ | ----------- | --- | ------- |"]
    for result in sorted(results, key=lambda r: (r.exists, r.last_pushed or datetime.date.min)):
        if not result.exists:
            exists, pushed, age = "**NO**", "—", "—"
        elif result.last_pushed:
            days = (today - result.last_pushed).days
            exists = "yes"
            pushed = result.last_pushed.isoformat()
            age = f"{days // 365}y {days % 365}d" + (" ⚠️" if days > max_age_days else "")
        else:
            exists, pushed, age = "?", "—", result.note
        uses = len(result.pin.sources)
        lines.append(
            f"| `{result.pin.image}` | `{result.pin.tag}` | {exists} | {pushed} | {age} | "
            f"{uses} file{'s' if uses != 1 else ''} |"
        )
    return "\n".join(lines), len(missing), len(stale)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root (default: .)")
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=DEFAULT_MAX_AGE_DAYS,
        help=f"Warn above this age (default: {DEFAULT_MAX_AGE_DAYS})",
    )
    parser.add_argument(
        "--fail-on-stale",
        action="store_true",
        help="Also exit non-zero when an image is older than --max-age-days",
    )
    args = parser.parse_args()

    root = pathlib.Path(args.root).resolve()
    today = datetime.date.today()

    pins = collect_pins(root)
    if not pins:
        print("No image pins found - are the submodules checked out?", file=sys.stderr)
        return 1

    results = [check(pin, today) for pin in pins]
    table, missing, stale = render(results, args.max_age_days, today)

    print(table)
    print()
    print(f"{len(pins)} distinct pins | missing: {missing} | "
          f"older than {args.max_age_days} days: {stale}")

    for result in results:
        if not result.exists:
            files = ", ".join(sorted(result.pin.sources))
            print(f"::error::{result.pin.ref} does not exist. Used by: {files}")
    for result in results:
        if result.exists and result.last_pushed:
            days = (today - result.last_pushed).days
            if days > args.max_age_days:
                print(
                    f"::warning::{result.pin.ref} was last pushed "
                    f"{result.last_pushed.isoformat()} ({days} days ago)"
                )

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write("## Job Definition image pins\n\n")
            handle.write(table + "\n\n")
            handle.write(
                f"**{len(pins)} distinct pins** — missing: **{missing}**, "
                f"older than {args.max_age_days} days: **{stale}**\n"
            )

    if missing:
        return 1
    if stale and args.fail_on_stale:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
