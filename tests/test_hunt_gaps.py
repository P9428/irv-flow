"""A span with both streams down is journalled once as a blind gap; a refused reconnect never miscounts the twin."""
import asyncio
import importlib.util
import json
import os

from websockets.datastructures import Headers
from websockets.exceptions import ConnectionClosedError, InvalidStatusCode, ProtocolError
from websockets.frames import Close

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
spec = importlib.util.spec_from_file_location("hunt", os.path.join(ROOT, "ops", "hunt.py"))
H = importlib.util.module_from_spec(spec)
spec.loader.exec_module(H)
real_sleep = asyncio.sleep


class Socket:
    response_headers = Headers({"x-ratelimit-endpoint-remaining": "1200"})

    def __init__(self, life):
        self.life = life

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def send(self, _):
        pass

    def __aiter__(self):
        return self

    async def __anext__(self):
        await real_sleep(self.life)
        raise ConnectionClosedError(None, Close(1002, ""), None) from ProtocolError("invalid status code")


def run(monkeypatch, tmp_path, script, seconds):
    steps = {name: iter(s) for name, s in script.items()}

    def connect(*_, **__):
        step = next(steps[asyncio.current_task().get_name()])
        if step == "refuse":
            raise InvalidStatusCode(413, Headers({"retry-after": "30", "x-ratelimit-endpoint-remaining": "-19570"}))
        return Socket(step)

    monkeypatch.setattr(H.J, "JOURNAL", str(tmp_path))
    monkeypatch.setattr(H.C, "HUNT_LOG", str(tmp_path / "hunt.log"))
    monkeypatch.setattr(H.websockets, "connect", connect)
    waits = []
    monkeypatch.setattr(H.asyncio, "sleep", lambda t: waits.append(t) or real_sleep(0.01))
    hunter = H.Hunter()
    hunter.waits = waits

    async def go():
        tasks = [asyncio.create_task(hunter.stream(i), name=f"s{i}") for i in (0, 1)]
        await real_sleep(seconds)
        for t in tasks:
            t.cancel()

    asyncio.run(go())
    gaps = [json.loads(x) for f in sorted((tmp_path / "gaps").glob("*.jsonl")) for x in open(f)] if (tmp_path / "gaps").exists() else []
    return hunter, gaps


def test_both_down_is_one_blind_gap(tmp_path, monkeypatch):
    hunter, gaps = run(monkeypatch, tmp_path, {
        "s0": [0.10, "refuse", "refuse", 9],                # up, cut with its twin, refused twice, back
        "s1": [0.10, "refuse", "refuse", "refuse", 9],
    }, 0.5)
    assert hunter.stats["connected"] == 2 and hunter.blind is None
    assert len(gaps) == 1
    g = gaps[0]
    assert g["kind"] == "blind" and g["backfilled"] is False and g["refusals"] >= 2 and 0 <= g["seconds"] < 1
    assert "1002" in g["why"] and "invalid status code" in g["why"]
    log = (tmp_path / "hunt.log").read_text()
    assert set(hunter.waits) == {2, 30}                       # a cut retries in 2 s, a 413 honours retry-after
    assert "HTTP 413 endpoint-remaining=-19570" in log and "connected endpoint-remaining=1200" in log


def test_refused_stream_does_not_unseat_its_live_twin(tmp_path, monkeypatch):
    hunter, gaps = run(monkeypatch, tmp_path, {
        "s0": [9],
        "s1": ["refuse"] * 20 + [9],
    }, 0.1)
    assert hunter.stats["connected"] == 1 and hunter.blind is None and gaps == []


def test_start_refused_is_not_a_blind_gap(tmp_path, monkeypatch):
    hunter, gaps = run(monkeypatch, tmp_path, {"s0": ["refuse", "refuse", 9], "s1": ["refuse", "refuse", 9]}, 0.2)
    assert hunter.stats["connected"] == 2 and gaps == []


def test_budget_reads_the_rate_limit_headers():
    h = Headers({"X-RateLimit-Endpoint-Remaining": "-19570", "x-ratelimit-pubsub-remaining": "7", "retry-after": "30"})
    assert H.Hunter.budget(h) == "endpoint-remaining=-19570 pubsub-remaining=7"
