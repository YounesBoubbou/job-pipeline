"""run_daily.ps1 (P8): runs a fake pipeline, never main.py, and logs to a temp folder."""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
POWERSHELL = shutil.which("powershell.exe")

pytestmark = pytest.mark.skipif(POWERSHELL is None, reason="needs Windows PowerShell")


def run_daily(tmp_path, script_text, python=sys.executable):
    tmp_path.mkdir(parents=True, exist_ok=True)
    fake = tmp_path / "fake_pipeline.py"
    fake.write_text(script_text, encoding="utf-8")
    log_dir = tmp_path / "logs"
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    result = subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", str(ROOT / "run_daily.ps1"),
         "-Python", str(python), "-Script", str(fake), "-LogDir", str(log_dir)],
        capture_output=True, env=env, timeout=60,
    )
    return result, log_dir


def only_log(log_dir):
    logs = list(log_dir.glob("run_*.log"))
    assert len(logs) == 1
    return logs[0].read_text(encoding="utf-8")


def test_logs_output_and_errors_with_non_ascii(tmp_path):
    result, log_dir = run_daily(tmp_path, (
        "import sys\n"
        "print('[IND✓] Ingénieur @ Société')\n"
        "print('a warning', file=sys.stderr)\n"
    ))
    assert result.returncode == 0
    text = only_log(log_dir)
    assert "[IND✓] Ingénieur @ Société" in text
    assert "a warning" in text
    assert "exit code 0" in text


def test_passes_on_the_pipeline_exit_code(tmp_path):
    result, log_dir = run_daily(tmp_path, "raise SystemExit(3)\n")
    assert result.returncode == 3
    assert "exit code 3" in only_log(log_dir)


def test_crash_traceback_lands_in_the_log(tmp_path):
    result, log_dir = run_daily(tmp_path, "raise RuntimeError('board exploded')\n")
    assert result.returncode == 1
    assert "RuntimeError: board exploded" in only_log(log_dir)


def test_missing_python_fails_with_a_clear_message(tmp_path):
    result, log_dir = run_daily(tmp_path, "print('never runs')\n", python=tmp_path / "nope.exe")
    assert result.returncode == 1
    text = only_log(log_dir)
    assert "no Python found" in text
    assert "never runs" not in text


def test_deletes_logs_older_than_30_days(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    old = log_dir / "run_2020-01-01_0800.log"
    recent = log_dir / "run_2099-01-01_0800.log"
    other = log_dir / "notes.txt"
    for f in (old, recent, other):
        f.write_text("x", encoding="utf-8")
    long_ago = time.time() - 31 * 24 * 3600
    os.utime(old, (long_ago, long_ago))
    os.utime(other, (long_ago, long_ago))

    result, _ = run_daily(tmp_path, "print('ok')\n")
    assert result.returncode == 0
    assert not old.exists()
    assert recent.exists()
    assert other.exists()


def test_works_when_every_path_has_a_space(tmp_path):
    # The project or its venv can sit under a folder with a space in its name.
    # The fake "python" is a .cmd file in that folder that hands over to the real one.
    spaced = tmp_path / "with space"
    spaced.mkdir()
    python = spaced / "fake python.cmd"
    python.write_text(f'@"{sys.executable}" %*\r\n', encoding="utf-8")
    result, log_dir = run_daily(spaced, "print('spaced ok')\nraise SystemExit(4)\n", python=python)
    assert result.returncode == 4
    text = only_log(log_dir)
    assert "spaced ok" in text
    assert "exit code 4" in text


def test_missing_python_message_with_a_spaced_log_dir(tmp_path):
    spaced = tmp_path / "with space"
    result, log_dir = run_daily(spaced, "print('never runs')\n", python=spaced / "no python.exe")
    assert result.returncode == 1
    assert "no Python found" in only_log(log_dir)
