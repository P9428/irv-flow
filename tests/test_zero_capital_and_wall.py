"""Zero capital is machine-checked, and the wall to mimicry is read-only by AST."""
import ast
import os
import re

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CODE_DIRS = ("src", "lib", "ops")
FORBIDDEN = ("Keypair", "keypair", "private_key", "secret_key", "sign_transaction", "signTransaction",
             "send_transaction", "sendTransaction", "submit_order", "place_order", "jupiter", "swap(", "wallet.pay")


def _py_files():
    for d in CODE_DIRS:
        for dp, _dn, fn in os.walk(os.path.join(ROOT, d)):
            for f in fn:
                if f.endswith(".py"):
                    yield os.path.join(dp, f)


def test_no_key_or_order_vocabulary_anywhere():
    hits = []
    for p in _py_files():
        src = open(p, encoding="utf-8").read()
        for tok in FORBIDDEN:
            if tok in src:
                hits.append((os.path.relpath(p, ROOT), tok))
    assert not hits, hits


def test_hunter_only_receives():
    src = open(os.path.join(ROOT, "ops", "hunt.py"), encoding="utf-8").read()
    assert src.count("ws.send(") == 1 and '"logsSubscribe"' in src          # the one send is the subscription
    assert "sendTransaction" not in src and "simulateTransaction" not in src


def test_captures_reader_has_no_write_path():
    tree = ast.parse(open(os.path.join(ROOT, "lib", "captures.py"), encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name in ("open",):
                modes = [a.value for a in node.args[1:2] if isinstance(a, ast.Constant)] + \
                        [k.value.value for k in node.keywords if k.arg == "mode" and isinstance(k.value, ast.Constant)]
                assert all(not re.search(r"[wax+]", m) for m in modes), "write mode in lib/captures.py"
            mod = getattr(getattr(node.func, "value", None), "id", None)
            assert not (mod in ("os", "shutil") and name in ("remove", "unlink", "rename", "replace", "rmtree", "makedirs", "mkdir")), name


def test_nothing_writes_under_mimicry():
    for p in _py_files():
        src = open(p, encoding="utf-8").read()
        assert not re.search(r"open\([^)]*mimicry[^)]*['\"][wax]", src), p
