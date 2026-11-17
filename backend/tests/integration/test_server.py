"""Integration tests that start the real API server and call it over real HTTP.

Each test runs ``python -m motosphere`` as a child process on a free local port,
in an empty working directory so no real ``.env`` file is read. Every process
is stopped and its output collected before the test ends, pass or fail.
"""

import os
import re
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import httpx2
import pytest

import motosphere

HOST = "127.0.0.1"
HEALTH_PATH = "/api/health"
READY_TIMEOUT_SECONDS = 15.0
POLL_INTERVAL_SECONDS = 0.1
EXIT_TIMEOUT_SECONDS = 10.0
LOG_LINE_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z (DEBUG|INFO|WARNING|ERROR|CRITICAL) \[[\w.]+\] .*$"
)


@dataclass
class ServerRun:
    """A server process and, once it has stopped, its exit code and output."""

    port: int
    process: subprocess.Popen[str]
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    _collected: bool = field(default=False, repr=False)

    def collect(self) -> None:
        """Wait for the process to exit and keep its output.

        Kills the process and fails the test if it does not exit in time, so no
        process is ever left behind. Safe to call more than once.
        """
        if self._collected:
            return
        self._collected = True
        try:
            self.stdout, self.stderr = self.process.communicate(timeout=EXIT_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.stdout, self.stderr = self.process.communicate()
            self.returncode = self.process.returncode
            pytest.fail(
                f"The server did not exit within {EXIT_TIMEOUT_SECONDS} s and was killed.\n"
                f"Standard error:\n{self.stderr}"
            )
        self.returncode = self.process.returncode


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        port: int = sock.getsockname()[1]
    return port


def _start_server(cwd: Path, port: int | str) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["MOTOSPHERE_API_PORT"] = str(port)
    if sys.platform == "win32":
        # A new process group lets the test send Ctrl+Break to the server alone.
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        creationflags = 0
    return subprocess.Popen(
        [sys.executable, "-m", "motosphere"],
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=creationflags,
    )


def _interrupt(process: subprocess.Popen[str]) -> None:
    """Send the equivalent of pressing Ctrl+C in the server's terminal."""
    if sys.platform == "win32":
        process.send_signal(signal.CTRL_BREAK_EVENT)
    else:
        process.send_signal(signal.SIGINT)


def _health_url(port: int) -> str:
    return f"http://{HOST}:{port}{HEALTH_PATH}"


def _wait_until_ready(run: ServerRun) -> None:
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if run.process.poll() is not None:
            run.collect()
            pytest.fail(
                f"The server exited with code {run.returncode} before it was ready.\n"
                f"Standard error:\n{run.stderr}"
            )
        try:
            httpx2.get(_health_url(run.port), timeout=1.0)
        except httpx2.TransportError:
            time.sleep(POLL_INTERVAL_SECONDS)
        else:
            return
    pytest.fail(f"The server did not answer within {READY_TIMEOUT_SECONDS} s.")


@contextmanager
def _running_server(cwd: Path) -> Iterator[ServerRun]:
    """Start the server, wait until it answers, and interrupt it when the block ends."""
    port = _free_port()
    run = ServerRun(port=port, process=_start_server(cwd, port))
    try:
        _wait_until_ready(run)
        yield run
    finally:
        if run.process.poll() is None:
            _interrupt(run.process)
        run.collect()


def _run_until_exit(cwd: Path, port: int | str) -> ServerRun:
    """Start the server and wait for it to exit by itself."""
    run = ServerRun(port=0, process=_start_server(cwd, port))
    run.collect()
    return run


def test_server_answers_health_over_http(tmp_path: Path) -> None:
    with _running_server(tmp_path) as run:
        response = httpx2.get(_health_url(run.port), timeout=5.0)

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "name": "MotoSphere",
        "version": motosphere.__version__,
    }


def test_server_logs_use_motosphere_format(tmp_path: Path) -> None:
    with _running_server(tmp_path) as run:
        response = httpx2.get(_health_url(run.port), timeout=5.0)
        assert response.status_code == 200

    assert run.stdout == ""
    lines = [line for line in run.stderr.splitlines() if line.strip()]
    assert lines
    for line in lines:
        assert LOG_LINE_PATTERN.fullmatch(line), line
    assert any(f"http://{HOST}:{run.port}" in line for line in lines)
    assert any(f"GET {HEALTH_PATH}" in line for line in lines)


def test_server_stops_cleanly_on_interrupt(tmp_path: Path) -> None:
    with _running_server(tmp_path) as run:
        pass

    assert "Finished server process" in run.stderr
    if sys.platform != "win32":
        assert run.returncode == 0


def test_server_exits_when_port_is_in_use(tmp_path: Path) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as blocker:
        blocker.bind((HOST, 0))
        blocker.listen()
        port: int = blocker.getsockname()[1]

        run = _run_until_exit(tmp_path, port)

    assert run.returncode != 0
    assert any(" ERROR [" in line for line in run.stderr.splitlines()), run.stderr


def test_invalid_configuration_exits_with_code_2(tmp_path: Path) -> None:
    run = _run_until_exit(tmp_path, 0)

    assert run.returncode == 2
    assert run.stderr.startswith("Configuration error: ")
    assert "api_port" in run.stderr
    assert "Traceback" not in run.stderr
