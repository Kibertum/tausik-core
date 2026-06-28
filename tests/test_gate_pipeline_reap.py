"""fix-pipeline-proc-wait-timeout: bound the intermediate-stage reap.

After the last stage of a `|`-pipeline finishes, _exec_pipeline reaps the
upstream stages. Previously that reap used `proc.wait()` with no timeout, so
an intermediate stage that ignores SIGPIPE (or otherwise refuses to exit)
would wedge the whole gate forever even though the gate's real work was done.
The reap is now bounded by `timeout` + kill.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from gate_command_runner import _exec_pipeline  # noqa: E402

PY = sys.executable


def test_multi_stage_happy_path_returns_last_stage_output():
    """AC3: a normal two-stage pipeline returns the last stage's (rc, output)."""
    producer = [PY, "-c", "print('a'); print('b'); print('c')"]
    counter = [PY, "-c", "import sys; print(len(sys.stdin.read().split()))"]
    rc, out = _exec_pipeline([producer, counter], timeout=30)
    assert rc == 0, out
    assert out.strip() == "3"


def test_hanging_intermediate_stage_does_not_wedge_the_gate():
    """AC2 (negative): an upstream stage that ignores SIGPIPE and sleeps must
    not block the reap forever — it is killed after `timeout` and the pipeline
    returns promptly with the last stage's result."""
    # Stage 0: emit one line, then ignore SIGPIPE and sleep far longer than the
    # timeout. Without the bounded reap, proc.wait() would block until sleep ends.
    hanging = [
        PY,
        "-c",
        (
            "import sys, time, signal\n"
            "try:\n"
            "    signal.signal(signal.SIGPIPE, signal.SIG_IGN)\n"
            "except (AttributeError, ValueError):\n"
            "    pass\n"
            "sys.stdout.write('hello\\n'); sys.stdout.flush()\n"
            "time.sleep(30)\n"
        ),
    ]
    # Last stage: read one line and exit immediately, closing the pipe.
    consumer = [PY, "-c", "import sys; sys.stdout.write(sys.stdin.readline())"]

    start = time.monotonic()
    rc, out = _exec_pipeline([hanging, consumer], timeout=3)
    elapsed = time.monotonic() - start

    assert rc == 0, out
    assert out.strip() == "hello"
    # Bounded: reap kills the hung stage at ~timeout (3s), nowhere near sleep(30).
    assert elapsed < 15, f"pipeline reap took {elapsed:.1f}s — intermediate not bounded"
