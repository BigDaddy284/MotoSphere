"""Checks that the published site is the site that was built.

    python scripts/live.py <site.tar> <address>

`site.tar` is the built site as it was handed to GitHub Pages, and `address`
is where the site is published, for example
`https://bigdaddy284.github.io/MotoSphere/`. Every file of the built site is
fetched from the address and compared, byte for byte, with the built one, and
its content type is checked. The data manifest names the moment it was
exported, so a site that is an older deployment never matches.

A deployment takes a little while to reach every server, so the check tries
again for a few minutes before it gives its verdict.

The script uses the Python standard library only. Its exit code is 0 when
every file is the built one and 1 when not, or when the check could not be
carried out.
"""

import argparse
import functools
import sys
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TextIO

# How long the check keeps trying, and how long it waits between tries.
WAIT_SECONDS = 300
PAUSE_SECONDS = 10

# How long one answer may take.
TIMEOUT_SECONDS = 30

# The page a visitor gets at the address itself.
INDEX = "index.html"

# What a browser must be told each kind of file is. A script served as plain
# text is not run, so the content type is part of the site working. Every
# kind of file the built site holds has its rule here: the kinds are listed
# in `frontend/e2e/siteKinds.json`, which one test holds to the site as it
# is built and another to these rules.
CONTENT_TYPES: dict[str, tuple[str, ...]] = {
    ".html": ("text/html",),
    ".js": ("text/javascript", "application/javascript"),
    ".css": ("text/css",),
    ".json": ("application/json",),
    ".svg": ("image/svg+xml",),
    ".png": ("image/png",),
    ".ico": ("image/x-icon", "image/vnd.microsoft.icon"),
    # A program for the browser's own machine. A browser compiles it while
    # it arrives only when it is told that this is what arrives.
    ".wasm": ("application/wasm",),
    ".jpg": ("image/jpeg",),
    # The two names of XML mean the same to a browser.
    ".xml": ("application/xml", "text/xml"),
    # Told to be anything else, a text is offered for saving and not shown.
    ".txt": ("text/plain",),
}

# Computers that are this one. Only they may be reached without encryption.
THIS_COMPUTER = ("127.0.0.1", "localhost", "::1")


class UnusableError(Exception):
    """The check could not be carried out. The message says why, in plain words."""


class UnreachableError(UnusableError):
    """The address gave no answer at all. That may pass, so it is tried again."""


@dataclass(frozen=True)
class Answer:
    """What a server answered: the status, the content type and the content."""

    status: int
    content_type: str
    body: bytes


Fetch = Callable[[str], Answer]


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    """A file of the site is where it is: being sent elsewhere is a failure."""

    def redirect_request(self, *_: object, **__: object) -> None:
        return None


@functools.cache
def _opener() -> urllib.request.OpenerDirector:
    """One opener for every fetch: making one reads this computer's certificates."""
    return urllib.request.build_opener(_NoRedirects)


def fetch(url: str) -> Answer:
    """Fetch an address once. An answer that is not 200 is still an answer."""
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})  # noqa: S310
    try:
        with _opener().open(request, timeout=TIMEOUT_SECONDS) as response:
            kind = response.headers.get_content_type()
            return Answer(response.status, kind, response.read())
    except urllib.error.HTTPError as error:
        return Answer(error.code, error.headers.get_content_type(), b"")
    except (OSError, ValueError) as error:
        raise UnreachableError(f"{url} could not be reached: {error}") from None


def checked_address(address: str) -> str:
    """The address of the site, which must be a folder on an encrypted connection."""
    parts = urllib.parse.urlsplit(address)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise UnusableError(f"{address} is not a web address")
    if parts.scheme == "http" and parts.hostname not in THIS_COMPUTER:
        raise UnusableError(f"{address} must start with https://")
    if parts.query or parts.fragment or parts.username or parts.password:
        raise UnusableError(f"{address} must be an address and nothing else")
    if not parts.path.endswith("/"):
        raise UnusableError(f"{address} must end with a slash")
    return address


def built_files(archive: Path) -> Iterator[tuple[str, bytes]]:
    """Every file of the built site, as its path inside the site and its content."""
    try:
        opened = tarfile.open(archive)  # noqa: SIM115
    except (OSError, tarfile.TarError):
        raise UnusableError(f"{archive.name} cannot be read as the built site") from None
    with opened:
        for member in opened:
            path = PurePosixPath(member.name)
            if member.isdir():
                continue
            if (
                not member.isfile()
                or path.is_absolute()
                or ".." in path.parts
                or "\\" in member.name
            ):
                raise UnusableError(
                    f"{archive.name} holds {member.name}, which is not a plain file of the site"
                )
            content = opened.extractfile(member)
            if content is None:
                raise UnusableError(f"{archive.name}: {member.name} cannot be read")
            yield path.as_posix(), content.read()


def expected_types(name: str) -> tuple[str, ...]:
    """The content types a file may be served as; none when its kind has no rule."""
    return CONTENT_TYPES.get(PurePosixPath(name).suffix.lower(), ())


def judge(answer: Answer, name: str, content: bytes) -> str | None:
    """What is wrong with one answer, in plain words, or None when it is right."""
    if answer.status != 200:
        return f"answered {answer.status}"
    kinds = expected_types(name)
    if kinds and answer.content_type not in kinds:
        return f"is served as {answer.content_type}, expected {kinds[0]}"
    if answer.body != content:
        return "differs from the built file"
    return None


def compare(archive: Path, address: str, fetcher: Fetch) -> tuple[int, dict[str, str]]:
    """Fetch every file once. Returns how many were looked at and what is wrong."""
    wrong: dict[str, str] = {}
    looked_at = 0
    seen_index = False
    for name, content in built_files(archive):
        looked_at += 1
        problem = judge(fetcher(address + urllib.parse.quote(name)), name, content)
        if problem is not None:
            wrong[name] = problem
        if name == INDEX:
            seen_index = True
            # The page a visitor gets without naming a file.
            problem = judge(fetcher(address), name, content)
            if problem is not None:
                wrong[address] = problem
    if not seen_index:
        raise UnusableError(f"{archive.name} holds no {INDEX}, so it is not the built site")
    return looked_at, wrong


def main(
    arguments: list[str] | None = None,
    out: TextIO = sys.stdout,
    fetcher: Fetch = fetch,
    pause: Callable[[float], None] = time.sleep,
    wait: float = WAIT_SECONDS,
) -> int:
    """Run the check and write what it found. Returns the exit code."""
    parser = argparse.ArgumentParser(
        description="Check that the published site is the site that was built."
    )
    parser.add_argument("site", type=Path, help="the built site, as a tar file")
    parser.add_argument("address", help="where the site is published, ending with a slash")
    options = parser.parse_args(arguments)

    try:
        address = checked_address(options.address)
        waited = 0.0
        tries = 0
        while True:
            tries += 1
            try:
                looked_at, wrong = compare(options.site, address, fetcher)
                waiting_for = f"{len(wrong)} of {looked_at} files are not the built ones yet"
            except UnreachableError as error:
                if waited >= wait:
                    raise
                looked_at, wrong = 0, {address: "could not be reached"}
                waiting_for = str(error)
            if not wrong or waited >= wait:
                break
            # A new deployment needs a moment to reach every server. The line is
            # sent at once, so that a log shows the waiting while it happens.
            out.write(f"Try {tries}: {waiting_for}.\n")
            out.flush()
            pause(PAUSE_SECONDS)
            waited += PAUSE_SECONDS
    except UnusableError as error:
        out.write(f"The published site could not be checked: {error}\n")
        return 1

    if wrong:
        out.write(f"FAILED: {address} is not the site that was built:\n")
        for name, problem in wrong.items():
            out.write(f"  - {name} {problem}\n")
        return 1
    out.write(f"{address} is the site that was built: {looked_at} of {looked_at} files.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
