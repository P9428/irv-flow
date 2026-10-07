"""THE HUNTER. Two merged keyless subscriptions, one incremental state machine per mint, the frozen
scorer once per signal. Runs forever. ZERO CAPITAL: the sockets only receive.

Feed: logsSubscribe(mentions=[pump.fun], processed) on the public RPC, held TWICE and merged by
transaction signature, so a server-side close on one stream loses nothing while the other is up.
Decoder: byte layout of CreateEvent / TradeEvent mirrored from wallet-independence's collect17.py.
Rule: for every create, the frozen reclaim (src/rule.py) is advanced one print at a time; when it
fires, score_mint() runs once on the full path to produce the record, and again at close. The
live state never overrides the frozen scorer — if they disagree, the scorer wins and the state is
dropped.

After a position closes its mint's prints are still kept to the end of the lookback, for one purpose: at
expiry src/excursion.py measures how far price ran and what a later fill would have got, and that goes to
journal/after/<utc-day>.jsonl. The live line is written at the same moment from the same prints as before;
nothing in the after-line is read by the rule, a filter, a look or a bar.
"""
import asyncio
import base64
import bisect
import hashlib
import json
import os
import struct
import sys
import time
from collections import deque

import websockets

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import common as C            # noqa: E402
import excursion as X         # noqa: E402
import journal as J           # noqa: E402
import rule as R              # noqa: E402

WS_URL = os.environ.get("IRV_FLOW_WS", "wss://api.mainnet-beta.solana.com")
PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
STREAMS = int(os.environ.get("IRV_FLOW_STREAMS", "2"))  # the public RPC meters usage per IP: every stream draws on the same budget
GRACE_S = 120                       # a mint is kept this long past its lookback so late exits settle
MAX_PRINTS = 6000                   # more prints than this inside 900 s is a bot swarm; tracking stops
SEEN_SIGNATURES = 200_000           # dedupe window across the two streams
HEARTBEAT_S = 10
_B58 = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58(b):
    n, out = int.from_bytes(b, "big"), bytearray()
    while n:
        n, r = divmod(n, 58)
        out.append(_B58[r])
    return (_B58[:1] * (len(b) - len(b.lstrip(b"\0"))) + bytes(reversed(out))).decode()


def _discriminator(name):
    return hashlib.sha256(b"event:" + name.encode()).digest()[:8]


D_CREATE, D_TRADE = _discriminator("CreateEvent"), _discriminator("TradeEvent")


def _str(raw, o):
    n = struct.unpack_from("<I", raw, o)[0]
    return raw[o + 4:o + 4 + n].decode("utf-8", "replace"), o + 4 + n


def decode_create(raw):
    o = 8
    name, o = _str(raw, o)
    symbol, o = _str(raw, o)
    _uri, o = _str(raw, o)
    mint, creator = b58(raw[o:o + 32]), b58(raw[o + 96:o + 128])
    ts = struct.unpack_from("<q", raw, o + 128)[0]
    return {"mint": mint, "name": name, "symbol": symbol, "creator": creator, "timestamp": ts}


def decode_trade(raw, slot):
    mint = b58(raw[8:40])
    sol, tok = struct.unpack_from("<QQ", raw, 40)
    user = b58(raw[57:89])
    ts, vsr, vtr, rsr, rtr = struct.unpack_from("<qQQQQ", raw, 89)
    return {"mint": mint, "timestamp": ts, "slot": slot, "is_buy": bool(raw[56]), "sol_amount": sol, "token_amount": tok,
            "user": user, "virtual_sol_reserves": vsr, "virtual_token_reserves": vtr, "real_sol_reserves": rsr,
            "invariant_ok": vtr - rtr == 279_900_000_000_000, "sol_offset_standard": vsr - rsr == 30_000_000_000}


def events(logs):
    for line in logs:
        if line.startswith("Program data: "):
            try:
                raw = base64.b64decode(line[14:])
            except ValueError:
                continue
            yield raw[:8], raw


class Mint:
    __slots__ = ("c0", "name", "symbol", "creator", "keys", "trades", "seen", "run_max", "h1", "t_low", "sig", "flow", "signal_wall", "written", "rec")

    def __init__(self, c):
        self.c0, self.name, self.symbol, self.creator = c["timestamp"], c["name"], c["symbol"], c["creator"]
        self.keys, self.trades, self.seen = [], [], time.time()
        self.run_max = self.h1 = self.t_low = self.sig = self.flow = self.signal_wall = self.rec = None
        self.written = False


class Hunter:
    def __init__(self):
        self.mints = {}
        self.seen = deque(maxlen=SEEN_SIGNATURES)
        self.seen_set = set()
        self.stats = {"creates": 0, "trades": 0, "signals": 0, "flow": 0, "closed": 0, "drops": 0,
                      "started": time.time(), "last_event": None, "connected": 0, "lag_s": 0.0}
        self.blind = None                   # (since, why, refusals) while every stream that was up is down
        os.makedirs(C.MON, exist_ok=True)

    def log(self, msg):
        with open(C.HUNT_LOG, "a", encoding="utf-8") as fh:
            fh.write(f"{C.stamp()} {msg}\n")

    # ---------------------------------------------------------------- per-event
    def dedupe(self, sig):
        if sig in self.seen_set:
            return False
        if len(self.seen) == self.seen.maxlen:
            self.seen_set.discard(self.seen[0])
        self.seen.append(sig)
        self.seen_set.add(sig)
        return True

    def on_create(self, c):
        self.stats["creates"] += 1
        self.mints[c["mint"]] = Mint(c)

    def on_trade(self, t):
        m = self.mints.get(t["mint"])
        if m is None or len(m.trades) >= MAX_PRINTS:
            return
        if not m.written:
            self.stats["trades"] += 1
            self.stats["lag_s"] = round(time.time() - t["timestamp"], 1)
        dt = t["timestamp"] - m.c0
        s = R.spot(t)
        if not 0 <= dt <= R.LOOKBACK_S or s is None:
            return
        key = (t["timestamp"], t["slot"])
        i = bisect.bisect_right(m.keys, key)
        m.keys.insert(i, key)
        m.trades.insert(i, t)
        if m.written:                                    # closed: the print is kept for the after-line and reaches no rule
            return
        if i < len(m.keys) - 1 and m.sig is None:        # arrived out of order before any signal: replay
            m.run_max = m.h1 = m.t_low = None
            for (ts, _slot), tr in zip(m.keys, m.trades):
                if self.step(t["mint"], m, ts - m.c0, R.spot(tr)):
                    break
            return
        self.step(t["mint"], m, dt, s)

    def step(self, mint, m, dt, s):
        """Advance the running detect/manage state by one print. True once a signal exists."""
        if m.sig is None:
            if m.run_max is None:
                m.run_max = s
            elif m.h1 is None:
                if s > m.run_max:
                    m.run_max = s
                elif s <= m.run_max * (1 - R.D):
                    m.h1, m.t_low = m.run_max, dt
            elif dt > m.t_low and s > m.h1:
                m.sig = {"t_entry": dt, "entry": s, "t_fill": None, "fill": None, "zero": None, "honest": None}
                self.signal(mint, m)
            return m.sig is not None
        g = m.sig
        if g["t_fill"] is None:
            g["t_fill"], g["fill"] = dt, s
        if g["zero"] is None and dt > g["t_entry"]:
            g["zero"] = "STOP" if s <= m.h1 else "TARGET" if s >= g["entry"] * R.MULTIPLE else None
        if g["honest"] is None and dt > g["t_fill"]:
            g["honest"] = "STOP" if s <= m.h1 else "TARGET" if s >= g["fill"] * R.MULTIPLE else None
        if g["zero"] and g["honest"]:
            self.close(mint, m)
        return True

    def signal(self, mint, m):
        rec = R.score_mint(mint, m.trades, m.c0)
        if rec is None:
            m.sig = None
            return
        m.flow, m.signal_wall = rec["flow"], C.stamp()
        self.stats["signals"] += 1
        if rec["flow"]:
            self.stats["flow"] += 1
            f = rec["features"]
            with open(C.ALERTS, "a", encoding="utf-8") as fh:
                fh.write(f"{m.signal_wall} FLOW {mint} {m.symbol!r} age {f['age_s']}s run {f['run_x']:.2f}x buyers {f['buyers']} "
                         f"pace {f['pace']:.2f}/s h1 {rec['h1']:.3e} https://pump.fun/{mint}\n")

    def close(self, mint, m):
        m.written = True
        rec = R.score_mint(mint, m.trades, m.c0)
        if rec is None:
            return
        rec.update({"name": m.name, "symbol": m.symbol, "creator": m.creator, "signal_wall": m.signal_wall,
                    "live": True, "closed_wall": C.stamp()})
        J.append_line("live", C.utc_day(m.c0 + rec["t_entry_s"]), rec)
        self.stats["closed"] += 1
        m.rec = rec

    def after(self, mint, m):
        """The excursion line, once, when the mint's lookback is over. A failure here is logged and costs only this line."""
        try:
            x = X.measure(R.build_path(m.trades, m.c0), m.rec)
            if x:
                J.append_line("after", C.utc_day(m.c0 + m.rec["t_entry_s"]), {"mint": mint, "c0": m.c0, "x": x})
        except Exception as e:
            self.log(f"after {mint} {type(e).__name__}: {str(e)[:80]}")

    def expire(self):
        cutoff = time.time() - R.LOOKBACK_S - GRACE_S
        for mint in [k for k, m in self.mints.items() if m.seen < cutoff]:
            m = self.mints.pop(mint)
            if m.sig and not m.written:
                self.close(mint, m)
            if m.rec:
                self.after(mint, m)

    def heartbeat(self):
        self.expire()
        C.write_json(C.HEARTBEAT, {**self.stats, "pid": os.getpid(), "wall": C.stamp(), "watching": len(self.mints),
                                   "open": sum(1 for m in self.mints.values() if m.sig and not m.written)})

    # ---------------------------------------------------------------- streams
    def handle(self, msg):
        d = json.loads(msg)
        if d.get("method") != "logsNotification":
            return
        v = d["params"]["result"]["value"]
        if v.get("err") is not None or not self.dedupe(v.get("signature")):
            return
        slot, logs = d["params"]["result"]["context"]["slot"], v.get("logs") or []
        is_create = any("Instruction: Create" in x for x in logs)
        for disc, raw in events(logs):
            if disc == D_TRADE:
                self.on_trade(decode_trade(raw, slot))
            elif disc == D_CREATE and is_create:
                self.on_create(decode_create(raw))
        self.stats["last_event"] = time.time()

    def went_blind(self, why):
        self.blind = (time.time(), why, 0)

    def saw_again(self):
        """Both streams were down and one is back: the span is a gap, journalled, never backfilled (V4)."""
        since, why, refused = self.blind
        self.blind, now = None, time.time()
        J.append_line("gaps", C.utc_day(since), {
            "at": C.stamp(), "kind": "blind", "backfilled": False, "from": C.iso(since), "to": C.iso(now),
            "seconds": round(now - since, 1), "refusals": refused, "why": why, "watching": len(self.mints),
            "lost": "every print on every watched mint inside the span, and every create in it: those mints are never followed"})

    @staticmethod
    def budget(headers):
        """The public RPC's per-IP meter, as it reports itself on every handshake (x-ratelimit-*)."""
        h = {k.lower(): v for k, v in headers.raw_items()}
        return " ".join(f"{k[12:]}={h[k]}" for k in ("x-ratelimit-endpoint-remaining", "x-ratelimit-pubsub-remaining",
                                                       "x-ratelimit-conn-remaining") if k in h)

    async def stream(self, idx):
        sub = json.dumps({"jsonrpc": "2.0", "id": idx, "method": "logsSubscribe",
                          "params": [{"mentions": [PUMP]}, {"commitment": "processed"}]})
        while True:
            up = False
            try:
                async with websockets.connect(WS_URL, ping_interval=20, max_size=None, open_timeout=15) as ws:
                    await ws.send(sub)
                    up = True
                    self.stats["connected"] += 1
                    if self.blind:
                        self.saw_again()
                    self.log(f"stream {idx} connected {self.budget(ws.response_headers)}")
                    async for msg in ws:
                        self.handle(msg)
            except Exception as e:                      # any drop: count, log, reconnect; the twin stream covers the gap
                why = f"{type(e).__name__}: {str(e)[:80]}"
                wait = 2
                if isinstance(e.__cause__, websockets.ProtocolError):   # the server's close carried a code outside RFC 6455
                    why += f" ({e.__cause__})"
                if isinstance(e, websockets.InvalidStatusCode):         # 413: the IP's usage budget is overdrawn
                    why += f" {self.budget(e.headers)}"
                    wait = max(wait, int(e.headers.get("retry-after", "").strip() or 0))
                self.stats["drops"] += 1
                if up:
                    self.stats["connected"] -= 1
                    if self.stats["connected"] == 0:
                        self.went_blind(why)
                elif self.blind:                        # the public RPC refuses reconnects (HTTP 413, retry-after 30) once the budget is overdrawn
                    self.blind = (self.blind[0], self.blind[1], self.blind[2] + 1)
                self.log(f"stream {idx} drop {why}")
                await asyncio.sleep(wait)

    async def pulse(self):
        last_log = 0
        while True:
            await asyncio.sleep(HEARTBEAT_S)
            self.heartbeat()
            if time.time() - last_log >= 3600:
                self.log(json.dumps({k: v for k, v in self.stats.items() if k != "started"}) + f" watching {len(self.mints)}")
                last_log = time.time()

    async def run(self):
        await asyncio.gather(self.pulse(), *(self.stream(i) for i in range(STREAMS)))


def another_hunter_is_alive():
    hb, age = C.heartbeat()
    if hb is None or age > 60 or hb.get("pid") == os.getpid():
        return False
    try:
        os.kill(hb["pid"], 0)
        return True
    except OSError:
        return False


if __name__ == "__main__":
    if not another_hunter_is_alive():
        asyncio.run(Hunter().run())
