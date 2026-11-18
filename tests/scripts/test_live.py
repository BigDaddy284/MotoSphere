"""Tests for the check of the published site, `scripts/live.py` (task FND-035).

Run from the repository root:

    python -m unittest discover -s tests/scripts -v

No test reaches the internet. The published site is played by a small web
server on this computer, which serves whatever a test tells it to.
"""

import http.server
import io
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import unittest
from pathlib import Path

# The script is not an installed package, so its folder is added to the places
# Python imports from.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import live

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "live.py"

PAGE = b"<!doctype html><title>MotoSphere</title>"
MANIFEST = b'{"format_version": 1, "generated_at": "2026-11-17T19:32:40Z"}'
OLDER = b'{"format_version": 1, "generated_at": "2026-11-16T02:00:00Z"}'

# A small built site: its files, as the upload step names them in the tar.
SITE = {
    "./index.html": PAGE,
    "./favicon.svg": b"<svg xmlns='http://www.w3.org/2000/svg'/>",
    "./favicon.ico": b"\x00\x00\x01\x00",
    "./assets/index-2wkFWPoH.css": b"body{margin:0}",
    "./assets/index-DS90V5py.js": b"console.log('MotoSphere')",
    "./data/manifest.json": MANIFEST,
}
TYPES = {
    "html": "text/html; charset=utf-8",
    "svg": "image/svg+xml",
    "ico": "image/vnd.microsoft.icon",
    "css": "text/css; charset=utf-8",
    "js": "application/javascript; charset=utf-8",
    "json": "application/json; charset=utf-8",
}

Served = dict[str, tuple[int, str, bytes]]


class StandInHandler(http.server.BaseHTTPRequestHandler):
    """Answers with what the test put into the server's `served` table."""

    # An answer leaves in one piece. Sent as headers first and content after,
    # each answer takes a tenth of a second on Windows.
    wbufsize = 64 * 1024

    def do_GET(self) -> None:
        served: Served = self.server.served  # type: ignore[attr-defined]
        self.server.asked.append(self.path)  # type: ignore[attr-defined]
        status, kind, body = served.get(self.path, (404, "text/html", b"not here"))
        self.send_response(status)
        self.send_header("Content-Type", kind)
        if status in (301, 302):
            self.send_header("Location", "/elsewhere/")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_: object) -> None:
        """Keep the test output free of the server's own lines."""


def as_served(site: dict[str, bytes], under: str = "/MotoSphere/") -> Served:
    """The table of a server that publishes this site correctly."""
    served: Served = {}
    for name, content in site.items():
        path = under + name.removeprefix("./")
        served[path] = (200, TYPES[name.rsplit(".", 1)[-1]], content)
    served[under] = served[under + "index.html"]
    return served


class SiteTest(unittest.TestCase):
    """A temporary folder for the built site and a stand-in for the published one."""

    def setUp(self) -> None:
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        self.folder = Path(folder).resolve()

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), StandInHandler)
        self.server.served = as_served(SITE)  # type: ignore[attr-defined]
        self.server.asked = []  # type: ignore[attr-defined]
        # The short interval keeps stopping the server from slowing every test.
        serving = {"poll_interval": 0.01}
        thread = threading.Thread(target=self.server.serve_forever, kwargs=serving, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.address = f"http://127.0.0.1:{self.server.server_port}/MotoSphere/"

    @property
    def served(self) -> Served:
        table: Served = self.server.served  # type: ignore[attr-defined]
        return table

    @property
    def asked(self) -> list[str]:
        paths: list[str] = self.server.asked  # type: ignore[attr-defined]
        return paths

    def built(self, site: dict[str, bytes] | None = None, name: str = "artifact.tar") -> Path:
        """Write the built site as a tar file, the way the upload step does."""
        archive = self.folder / name
        with tarfile.open(archive, "w") as tar:
            folder = tarfile.TarInfo("./")
            folder.type = tarfile.DIRTYPE
            tar.addfile(folder)
            for path, content in (SITE if site is None else site).items():
                member = tarfile.TarInfo(path)
                member.size = len(content)
                tar.addfile(member, io.BytesIO(content))
        return archive

    def check(self, archive: Path | None = None, wait: float = 0) -> tuple[int, str, list[float]]:
        """Run the check against the stand-in. Returns the code, the output and the pauses."""
        out = io.StringIO()
        pauses: list[float] = []
        code = live.main(
            [str(archive or self.built()), self.address], out, pause=pauses.append, wait=wait
        )
        return code, out.getvalue(), pauses


def no_answer(url: str) -> live.Answer:
    """A fetcher for a site that gives no answer at all."""
    raise live.UnreachableError(f"{url} could not be reached: no answer")


class Recorder(io.StringIO):
    """Output that remembers how much of it had been written each time it was sent."""

    def __init__(self) -> None:
        super().__init__()
        self.sent: list[str] = []

    def flush(self) -> None:
        super().flush()
        self.sent.append(self.getvalue())


class AddressTest(unittest.TestCase):
    def test_accepts_an_encrypted_address_that_ends_with_a_slash(self) -> None:
        address = "https://bigdaddy284.github.io/MotoSphere/"
        self.assertEqual(live.checked_address(address), address)

    def test_accepts_this_computer_without_encryption(self) -> None:
        for address in ("http://127.0.0.1:4173/MotoSphere/", "http://localhost/"):
            with self.subTest(address=address):
                self.assertEqual(live.checked_address(address), address)

    def refused(self, address: str, why: str) -> None:
        with self.assertRaises(live.UnusableError) as caught:
            live.checked_address(address)
        self.assertEqual(str(caught.exception), f"{address} {why}")

    def test_refuses_another_computer_without_encryption(self) -> None:
        self.refused("http://bigdaddy284.github.io/MotoSphere/", "must start with https://")

    def test_refuses_what_is_not_a_web_address(self) -> None:
        for address in (
            "",
            "MotoSphere/",
            "file:///etc/passwd/",
            "ftp://example.org/",
            "https:///",
        ):
            with self.subTest(address=address):
                self.refused(address, "is not a web address")

    def test_refuses_an_address_that_is_not_a_folder(self) -> None:
        self.refused("https://bigdaddy284.github.io/MotoSphere", "must end with a slash")
        self.refused("https://bigdaddy284.github.io", "must end with a slash")

    def test_refuses_an_address_that_carries_more_than_an_address(self) -> None:
        for address in (
            "https://example.org/site/?page=1",
            "https://example.org/site/#top",
            "https://someone:secret@example.org/site/",
        ):
            with self.subTest(address=address):
                self.refused(address, "must be an address and nothing else")


class BuiltFilesTest(SiteTest):
    def refused(self, archive: Path, why: str) -> None:
        with self.assertRaises(live.UnusableError) as caught:
            list(live.built_files(archive))
        self.assertEqual(str(caught.exception), why)

    def test_reads_every_file_with_its_path_inside_the_site(self) -> None:
        self.assertEqual(
            dict(live.built_files(self.built())),
            {path.removeprefix("./"): content for path, content in SITE.items()},
        )

    def test_refuses_a_file_that_is_not_a_tar(self) -> None:
        archive = self.folder / "artifact.tar"
        archive.write_bytes(b"this is not a tar file")

        self.refused(archive, "artifact.tar cannot be read as the built site")

    def test_refuses_a_file_that_is_not_there(self) -> None:
        self.refused(self.folder / "missing.tar", "missing.tar cannot be read as the built site")

    def test_refuses_a_link_inside_the_site(self) -> None:
        archive = self.built()
        with tarfile.open(archive, "a") as tar:
            link = tarfile.TarInfo("./passwords")
            link.type = tarfile.SYMTYPE
            link.linkname = "/etc/passwd"
            tar.addfile(link)

        self.refused(
            archive, "artifact.tar holds ./passwords, which is not a plain file of the site"
        )

    def test_refuses_a_path_that_leaves_the_site(self) -> None:
        for path in ("../outside.txt", "/etc/outside.txt", "assets/../../outside.txt"):
            with self.subTest(path=path):
                archive = self.built({"./index.html": PAGE, path: b"x"}, name="odd.tar")
                self.refused(
                    archive, f"odd.tar holds {path}, which is not a plain file of the site"
                )


class JudgeTest(unittest.TestCase):
    def test_the_built_file_with_its_content_type_is_right(self) -> None:
        answer = live.Answer(200, "application/json", MANIFEST)
        self.assertIsNone(live.judge(answer, "data/manifest.json", MANIFEST))

    def test_an_answer_that_is_not_200_is_wrong(self) -> None:
        for status in (204, 301, 404, 500):
            with self.subTest(status=status):
                answer = live.Answer(status, "application/json", MANIFEST)
                self.assertEqual(
                    live.judge(answer, "data/manifest.json", MANIFEST), f"answered {status}"
                )

    def test_another_content_is_wrong(self) -> None:
        answer = live.Answer(200, "application/json", OLDER)
        self.assertEqual(
            live.judge(answer, "data/manifest.json", MANIFEST), "differs from the built file"
        )

    def test_a_content_type_a_browser_would_not_accept_is_wrong(self) -> None:
        answer = live.Answer(200, "text/plain", b"x")
        self.assertEqual(
            live.judge(answer, "assets/index.js", b"x"),
            "is served as text/plain, expected text/javascript",
        )

    def test_every_kind_of_file_of_the_site_has_a_content_type_rule(self) -> None:
        for name in SITE:
            with self.subTest(file=name):
                self.assertTrue(live.expected_types(name))
        self.assertEqual(live.expected_types("apple-touch-icon.png"), ("image/png",))
        self.assertEqual(live.expected_types("ICON.SVG"), ("image/svg+xml",))

    def test_a_script_may_be_served_under_either_of_its_names(self) -> None:
        for kind in ("text/javascript", "application/javascript"):
            with self.subTest(kind=kind):
                self.assertIsNone(live.judge(live.Answer(200, kind, b"x"), "assets/a.js", b"x"))

    def test_a_file_of_a_kind_without_a_rule_is_judged_by_its_content(self) -> None:
        self.assertIsNone(live.judge(live.Answer(200, "font/woff2", b"x"), "a.woff2", b"x"))
        self.assertEqual(
            live.judge(live.Answer(200, "font/woff2", b"y"), "a.woff2", b"x"),
            "differs from the built file",
        )


class FetchTest(SiteTest):
    def test_returns_the_status_the_content_type_and_the_content(self) -> None:
        self.assertEqual(
            live.fetch(self.address + "data/manifest.json"),
            live.Answer(200, "application/json", MANIFEST),
        )

    def test_an_answer_that_is_not_200_is_returned_not_raised(self) -> None:
        self.assertEqual(live.fetch(self.address + "missing.js").status, 404)

    def test_does_not_follow_a_redirect(self) -> None:
        self.served["/MotoSphere/moved.js"] = (301, "text/html", b"")
        self.served["/elsewhere/"] = (200, "text/javascript", b"x")

        self.assertEqual(live.fetch(self.address + "moved.js").status, 301)
        self.assertNotIn("/elsewhere/", self.asked)

    def test_a_server_that_cannot_be_reached_is_refused_in_plain_words(self) -> None:
        self.server.shutdown()
        self.server.server_close()

        with self.assertRaises(live.UnreachableError) as caught:
            live.fetch(self.address)
        self.assertIn(f"{self.address} could not be reached: ", str(caught.exception))


class MainTest(SiteTest):
    def test_passes_when_every_file_is_the_built_one(self) -> None:
        code, output, pauses = self.check()

        self.assertEqual(code, 0)
        self.assertEqual(output, f"{self.address} is the site that was built: 6 of 6 files.\n")
        self.assertEqual(pauses, [])

    def test_asks_for_every_file_and_for_the_address_itself(self) -> None:
        self.check()

        self.assertEqual(sorted(self.asked), sorted(as_served(SITE)))

    def test_fails_when_a_file_is_missing(self) -> None:
        del self.served["/MotoSphere/assets/index-DS90V5py.js"]

        code, output, _ = self.check()

        self.assertEqual(code, 1)
        self.assertEqual(
            output,
            f"FAILED: {self.address} is not the site that was built:\n"
            "  - assets/index-DS90V5py.js answered 404\n",
        )

    def test_fails_when_the_data_is_from_an_older_deployment(self) -> None:
        self.served["/MotoSphere/data/manifest.json"] = (200, TYPES["json"], OLDER)

        code, output, _ = self.check()

        self.assertEqual(code, 1)
        self.assertIn("  - data/manifest.json differs from the built file\n", output)

    def test_fails_when_a_script_is_served_as_text(self) -> None:
        path = "/MotoSphere/assets/index-DS90V5py.js"
        self.served[path] = (200, "text/plain", SITE["./assets/index-DS90V5py.js"])

        code, output, _ = self.check()

        self.assertEqual(code, 1)
        self.assertIn("index-DS90V5py.js is served as text/plain, expected text/javascript", output)

    def test_fails_when_the_address_itself_shows_another_page(self) -> None:
        self.served["/MotoSphere/"] = (200, TYPES["html"], b"<title>Site not found</title>")

        code, output, _ = self.check()

        self.assertEqual(code, 1)
        self.assertEqual(
            output,
            f"FAILED: {self.address} is not the site that was built:\n"
            f"  - {self.address} differs from the built file\n",
        )

    def test_fails_when_a_file_was_moved_elsewhere(self) -> None:
        self.served["/MotoSphere/favicon.svg"] = (302, "text/html", b"")

        code, output, _ = self.check()

        self.assertEqual(code, 1)
        self.assertIn("  - favicon.svg answered 302\n", output)

    def test_names_every_file_that_is_wrong(self) -> None:
        self.server.served = {}  # type: ignore[attr-defined]

        code, output, _ = self.check()

        self.assertEqual(code, 1)
        self.assertEqual(output.count(" answered 404\n"), 7)

    def test_fetches_a_file_whose_name_needs_quoting(self) -> None:
        site = {**SITE, "./data/two words.json": b"{}"}
        self.server.served = as_served(site)  # type: ignore[attr-defined]
        self.served["/MotoSphere/data/two%20words.json"] = self.served.pop(
            "/MotoSphere/data/two words.json"
        )

        code, output, _ = self.check(self.built(site))

        self.assertEqual(code, 0, output)
        self.assertIn("7 of 7 files", output)

    def test_waits_for_a_deployment_that_has_not_arrived_everywhere_yet(self) -> None:
        right = self.served["/MotoSphere/data/manifest.json"]
        self.served["/MotoSphere/data/manifest.json"] = (200, TYPES["json"], OLDER)
        out = io.StringIO()
        pauses: list[float] = []

        def pause(seconds: float) -> None:
            pauses.append(seconds)
            if len(pauses) == 2:
                self.served["/MotoSphere/data/manifest.json"] = right

        code = live.main([str(self.built()), self.address], out, pause=pause, wait=300)

        self.assertEqual(code, 0)
        self.assertEqual(pauses, [live.PAUSE_SECONDS] * 2)
        self.assertEqual(
            out.getvalue(),
            "Try 1: 1 of 6 files are not the built ones yet.\n"
            "Try 2: 1 of 6 files are not the built ones yet.\n"
            f"{self.address} is the site that was built: 6 of 6 files.\n",
        )

    def test_gives_up_when_the_time_is_over(self) -> None:
        self.served["/MotoSphere/data/manifest.json"] = (200, TYPES["json"], OLDER)

        code, output, pauses = self.check(wait=30)

        self.assertEqual(code, 1)
        self.assertEqual(pauses, [live.PAUSE_SECONDS] * 3)
        self.assertEqual(output.count("Try "), 3)
        self.assertIn("FAILED: ", output)

    def test_tries_again_when_the_site_gives_no_answer_at_first(self) -> None:
        calls: list[str] = []

        def fetcher(url: str) -> live.Answer:
            calls.append(url)
            return no_answer(url) if len(calls) == 1 else live.fetch(url)

        out = io.StringIO()
        pauses: list[float] = []

        code = live.main([str(self.built()), self.address], out, fetcher, pauses.append, wait=300)

        self.assertEqual(code, 0)
        self.assertEqual(pauses, [live.PAUSE_SECONDS])
        self.assertRegex(out.getvalue(), r"^Try 1: http://\S+ could not be reached: no answer\.\n")
        self.assertIn("is the site that was built: 6 of 6 files.\n", out.getvalue())

    def test_gives_up_on_a_site_that_never_answers_when_the_time_is_over(self) -> None:
        out = io.StringIO()
        pauses: list[float] = []

        code = live.main([str(self.built()), self.address], out, no_answer, pauses.append, wait=20)

        self.assertEqual(code, 1)
        self.assertEqual(pauses, [live.PAUSE_SECONDS] * 2)
        self.assertEqual(out.getvalue().count("Try "), 2)
        self.assertIn("The published site could not be checked: ", out.getvalue())
        self.assertNotIn("is the site that was built", out.getvalue())

    def test_sends_each_line_about_waiting_before_it_waits(self) -> None:
        # A log must show the waiting while it happens, not after it.
        self.served["/MotoSphere/data/manifest.json"] = (200, TYPES["json"], OLDER)
        out = Recorder()
        not_sent: list[str] = []

        def pause(_: float) -> None:
            sent = out.sent[-1] if out.sent else ""
            not_sent.append(out.getvalue().removeprefix(sent))

        live.main([str(self.built()), self.address], out, pause=pause, wait=20)

        self.assertEqual(not_sent, ["", ""])
        self.assertIn("Try 2: ", out.sent[-1])

    def test_waits_five_minutes_unless_told_otherwise(self) -> None:
        self.assertEqual(live.WAIT_SECONDS, 300)
        self.assertEqual(live.PAUSE_SECONDS, 10)
        self.assertEqual(live.main.__kwdefaults__, None)
        self.assertIn(live.WAIT_SECONDS, live.main.__defaults__ or ())

    def test_fails_in_plain_words_when_the_site_cannot_be_reached(self) -> None:
        out = io.StringIO()
        pauses: list[float] = []

        code = live.main([str(self.built()), self.address], out, no_answer, pauses.append, wait=0)

        self.assertEqual(code, 1)
        self.assertEqual(
            out.getvalue(),
            f"The published site could not be checked: {self.address}index.html"
            " could not be reached: no answer\n",
        )
        self.assertEqual(pauses, [])

    def test_fails_in_plain_words_when_the_built_site_has_no_page(self) -> None:
        site = {path: content for path, content in SITE.items() if path != "./index.html"}

        code, output, _ = self.check(self.built(site))

        self.assertEqual(code, 1)
        self.assertEqual(
            output,
            "The published site could not be checked: "
            "artifact.tar holds no index.html, so it is not the built site\n",
        )

    def test_fails_in_plain_words_when_the_address_is_not_one(self) -> None:
        out = io.StringIO()

        code = live.main([str(self.built()), "bigdaddy284.github.io/MotoSphere/"], out)

        self.assertEqual(code, 1)
        self.assertEqual(
            out.getvalue(),
            "The published site could not be checked: "
            "bigdaddy284.github.io/MotoSphere/ is not a web address\n",
        )
        self.assertEqual(self.asked, [])


class ProgramTest(SiteTest):
    """The script as a separate process, the way the workflow starts it."""

    def run_script(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        # The arguments are the real Python, this repository's script and
        # values the test wrote.
        return subprocess.run(  # noqa: S603
            [sys.executable, str(SCRIPT), *arguments],
            cwd=self.folder,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )

    def test_passes_on_a_site_that_is_the_built_one(self) -> None:
        finished = self.run_script(str(self.built()), self.address)

        self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)
        self.assertEqual(
            finished.stdout, f"{self.address} is the site that was built: 6 of 6 files.\n"
        )
        self.assertEqual(finished.stderr, "")

    def test_fails_without_a_traceback_when_it_cannot_check(self) -> None:
        finished = self.run_script(str(self.folder / "missing.tar"), self.address)

        self.assertEqual(finished.returncode, 1)
        self.assertEqual(
            finished.stdout,
            "The published site could not be checked: "
            "missing.tar cannot be read as the built site\n",
        )
        self.assertEqual(finished.stderr, "")


if __name__ == "__main__":
    unittest.main()
