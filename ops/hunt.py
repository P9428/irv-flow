"""THE HUNTER. Runs forever on the keyless public websocket and journals every reclaim it sees.

logsSubscribe(mentions=[pump], processed) on api.mainnet-beta.solana.com, exactly the feed
wallet-independence's collector used. Decoder mirrored from collect17.py. For every create it
follows the mint for LOOKBACK_S seconds, runs the frozen reclaim on each new print, fills on
paper at the NEXT print (honest arm) and at the signal print (zero arm), and writes one line
per closed position to journal/live/<utc-day>.jsonl. FLOW signals are also appended to
monitor/flow-alerts.log the second they fire.

ZERO CAPITAL. NO KEY. NO WALLET. NO ORDER. NO POSITION. The socket only receives.
"""
import asyncio
import base64
import hashlib
import json
import os
import struct
import sys
import time
from datetime import datetime, timezone

import websockets

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "src")]
import journal as J           # noqa: E402
import rule as R              # noqa: E402

WS_URL = os.environ.get("IRV_FLOW_WS") or "wss://api.mainnet-beta.solana.com"
PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
MON = os.path.join(ROOT, "monitor")
HEARTBEAT = os.path.join(MON, "hunt-heartbeat.json")
ALERTS = os.path.join(MON, "flow-alerts.log")
LOG = os.path.join(MON, "hunt.log")
GRACE_S = 120                    # keep a mint after its lookback so late exits settle
MAX_PRINTS = 6000                # a mint printing more than this inside 900 s is a bot swarm; dropped

_B58 = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58(b):
    n = int.from_bytes(b, "big"); out = bytearray()
    while n:
        n, r = divmod(n, 58); out.append(_B58[r])
    pad = len(b) - len(b.lstrip(b"\0"))
    return (_B58[:1] * pad + bytes(reversed(out))).decode()


def _evd(name):
    return hashlib.sha256(b"event:" + name.encode()).digest()[:8].hex()


D_CREATE, D_TRADE = _evd("CreateEvent"), _evd("TradeEvent")


def _rd_str(raw, o):
    ln = struct.unpack_from("<I", raw, o)[0]; o += 4
    return raw[o:o + ln].decode("utf-8", "replace"), o + ln


def decode_create(raw):
    o = 8
    name, o = _rd_str(raw, o); sym, o = _rd_str(raw, o); _uri, o = _rd_str(raw, o)
    mint = b58(raw[o:o + 32]); o += 32; o += 32
    _user = raw[o:o + 32]; o += 32
    creator = b58(raw[o:o + 32]); o += 32
    ts = struct.unpack_from("<q", raw, o)[0]
    return {"mint": mint, "name": name, "symbol": sym, "creator": creator, "timestamp": ts}


def decode_trade(raw, slot):
    o = 8
    mint = b58(raw[o:o + 32]); o += 32
    sol, tok = struct.unpack_from("<QQ", raw, o); o += 16
    is_buy = bool(raw[o]); o += 1
    user = b58(raw[o:o + 32]); o += 32
    ts = struct.unpack_from("<q", raw, o)[0]; o += 8
    vsr, vtr, rsr, rtr = struct.unpack_from("<QQQQ", raw, o)
    return {"mint": mint, "timestamp": ts, "slot": slot, "is_buy": is_buy, "sol_amount": sol,
            "token_amount": tok, "user": user, "virtual_sol_reserves": vsr, "virtual_token_reserves": vtr,
            "real_sol_reserves": rsr, "invariant_ok": vtr - rtr == 279_900_000_000_000,
            "sol_offset_standard": vsr - rsr == 30_000_000_000}


def _events(logs):
    for l in logs or []:
        if l.startswith("Program data: "):
            try:
                raw = base64.b64decode(l[14:])
            except Exception:
                continue
            yield raw[:8].hex(), raw


class Hunter:
    def __init__(self):
        self.mints = {}          # mint -> state
        self.stats = {"creates": 0, "trades": 0, "signals": 0, "flow": 0, "closed": 0, "drops": 0,
                      "started": time.time(), "last_event": None, "connected": False}
        os.makedirs(MON, exist_ok=True)

    def log(self, s):
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {s}\n")

    def on_create(self, c, slot):
        self.stats["creates"] += 1
        self.mints[c["mint"]] = {"c0": c["timestamp"], "name": c["name"], "symbol": c["symbol"], "creator": c["creator"],
                                 "trades": [], "rec": None, "seen": time.time()}

    def on_trade(self, t):
        st = self.mints.get(t["mint"])
        if st is None:
            return
        self.stats["trades"] += 1
        if len(st["trades"]) >= MAX_PRINTS:
            return
        st["trades"].append(t)
        if st["rec"] is None:
            path = R.build_path(st["trades"], st["c0"])
            if len(path) >= 3 and R.detect(path):
                self.signal(t["mint"], st)
        elif not st["rec"].get("_written"):
            self.follow(t["mint"], st)

    def signal(self, mint, st):
        rec = R.score_mint(mint, st["trades"], st["c0"])
        rec.update({"name": st["name"], "symbol": st["symbol"], "creator": st["creator"],
                    "signal_wall": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "why_zero": "OPEN", "why_honest": "OPEN", "live": True})
        st["rec"] = rec
        self.stats["signals"] += 1
        if rec["flow"]:
            self.stats["flow"] += 1
            with open(ALERTS, "a", encoding="utf-8") as fh:
                f = rec["features"]
                fh.write(f"{rec['signal_wall']} FLOW {mint} {st['symbol']!r} age {f['age_s']}s run {f['run_x']:.2f}x "
                         f"buyers {f['buyers']} pace {f['pace']:.2f}/s h1 {rec['h1']:.3e} https://pump.fun/{mint}\n")

    def follow(self, mint, st):
        """Re-run the frozen manage() on the growing path; close once BOTH arms hit a barrier.
        A HORIZON/NO_FILL reading mid-window is provisional; expire() makes it final at the lookback."""
        rec = R.score_mint(mint, st["trades"], st["c0"])
        rec.update({k: st["rec"][k] for k in ("name", "symbol", "creator", "signal_wall", "live")})
        final = rec["why_zero"] in ("STOP", "TARGET") and rec["why_honest"] in ("STOP", "TARGET")
        st["rec"] = rec if final else {**rec, "why_zero": "OPEN", "why_honest": "OPEN", "_final": rec}
        if final:
            self.close(mint, st)

    def close(self, mint, st):
        rec = st["rec"].get("_final") or st["rec"]
        if rec["why_zero"] == "OPEN":                      # signal print was the mint's last print
            rec = R.score_mint(mint, st["trades"], st["c0"])
            rec.update({k: st["rec"][k] for k in ("name", "symbol", "creator", "signal_wall", "live")})
        rec = {k: v for k, v in rec.items() if k != "_final"}
        rec["closed_wall"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        day = datetime.fromtimestamp(st["c0"] + rec["t_entry_s"], timezone.utc).strftime("%Y-%m-%d")
        J.append_line("live", day, rec)
        self.stats["closed"] += 1
        st["rec"] = {**rec, "_written": True}

    def expire(self):
        now = time.time()
        for mint in [m for m, s in self.mints.items() if now - s["seen"] > R.LOOKBACK_S + GRACE_S]:
            st = self.mints.pop(mint)
            if st["rec"] and not st["rec"].get("_written"):
                self.close(mint, st)

    def heartbeat(self):
        self.expire()
        hb = {**self.stats, "watching": len(self.mints), "open": sum(1 for s in self.mints.values() if s["rec"] and not s["rec"].get("_written")),
              "wall": datetime.now(timezone.utc).isoformat(timespec="seconds"), "pid": os.getpid()}
        tmp = HEARTBEAT + ".part"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(hb, fh, sort_keys=True)
        os.replace(tmp, HEARTBEAT)

    async def run(self):
        sub = {"jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
               "params": [{"mentions": [PUMP]}, {"commitment": "processed"}]}
        last_hb, last_log = 0, 0
        while True:
            try:
                async with websockets.connect(WS_URL, ping_interval=20, max_size=None) as ws:
                    await ws.send(json.dumps(sub))
                    self.stats["connected"] = True
                    self.log(f"connected {WS_URL}")
                    while True:
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=5)
                        except asyncio.TimeoutError:
                            msg = None
                        if msg:
                            d = json.loads(msg)
                            if d.get("method") == "logsNotification":
                                v = d["params"]["result"]["value"]
                                if v.get("err") is None:
                                    slot = d["params"]["result"]["context"]["slot"]
                                    logs = v.get("logs") or []
                                    is_create = any("Instruction: Create" in x for x in logs)
                                    for dh, raw in _events(logs):
                                        if dh == D_TRADE:
                                            self.on_trade(decode_trade(raw, slot))
                                        elif dh == D_CREATE and is_create:
                                            self.on_create(decode_create(raw), slot)
                                    self.stats["last_event"] = time.time()
                        now = time.time()
                        if now - last_hb >= 10:
                            self.heartbeat(); last_hb = now
                        if now - last_log >= 3600:
                            self.log(json.dumps({k: v for k, v in self.stats.items() if k != "started"}) + f" watching {len(self.mints)}")
                            last_log = now
            except Exception as e:                     # any drop: reconnect, count it, keep hunting
                self.stats["connected"] = False
                self.stats["drops"] += 1
                self.log(f"drop {type(e).__name__}: {e}")
                self.heartbeat()
                await asyncio.sleep(2)


def another_hunter_is_alive():
    """Refuse to double-write: a fresh heartbeat from a live python process means a hunter already runs."""
    try:
        hb = json.load(open(HEARTBEAT, encoding="utf-8"))
        if time.time() - os.path.getmtime(HEARTBEAT) > 60 or hb.get("pid") == os.getpid():
            return False
        os.kill(hb["pid"], 0)
        return True
    except (FileNotFoundError, ValueError, KeyError, OSError):
        return False


if __name__ == "__main__":
    if another_hunter_is_alive():
        sys.exit(0)
    asyncio.run(Hunter().run())
