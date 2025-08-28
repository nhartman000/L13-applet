import hashlib, math, random
from typing import Dict, Any, List, Tuple

DEFAULTS = dict(p=2, R=2.0, epsilon=0.1, tau=0.05, sigma=0.0, max_iter=512)

def compute_delta(cur: Dict[str, Any], prev: Dict[str, Any]) -> float:
    if prev is None: return 1.0
    shared = len(set(cur.items()) & set(prev.items()))
    total = max(len(set(cur.items()) | set(prev.items())), 1)
    return 1.0 - (shared / total)

def dsvm_residual(x: List[float], y: List[float]) -> float:
    num = math.sqrt(sum((a - b)**2 for a, b in zip(x, y)))
    den = math.sqrt(sum(a**2 for a in x)) or 1.0
    return num / den

def encode_context(features: Dict[str, Any]) -> complex:
    blob = "|".join(f"{k}={v}" for k, v in sorted(features.items())).encode()
    h = hashlib.sha256(blob).digest()
    re = int.from_bytes(h[:8], "big") / 2**64
    im = int.from_bytes(h[8:16], "big") / 2**64
    return complex(re, im)

def julia_infinity(c: complex, p: int, R: float, max_iter: int, sigma: float) -> Tuple[str, int]:
    z = 0 + 0j
    for i in range(max_iter):
        drift = sigma * (random.random() - 0.5) + 1j * sigma * (random.random() - 0.5)
        z = (z**p) + c + drift
        if abs(z) > R:
            return "escape", i
    return "bounded", max_iter

def a13_run(seed: Dict[str, Any], params: Dict[str, Any] = None,
            mirror_pairs: List[Tuple[List[float], List[float]]] = None) -> Dict[str, Any]:
    P = {**DEFAULTS, **(params or {})}
    history = []
    prev = None
    decision = "continue"

    for k in range(1, 14):
        state = dict(pass_id=k, note=f"Pass {k}", data=dict(seed))
        if mirror_pairs:
            rmax = max(dsvm_residual(a, b) for a, b in mirror_pairs)
            state["dsvm_r"] = rmax
            if rmax > P["tau"]:
                decision = "escape_dsvm"; history.append(state); break

        delta = compute_delta(state["data"], prev)
        state["delta"] = delta
        history.append(state)
        prev = state["data"]
        if delta <= P["epsilon"]:
            decision = "converged_a13"; break

    if decision not in ("converged_a13", "escape_dsvm"):
        c = encode_context(seed)
        outcome, iters = julia_infinity(c, P["p"], P["R"], P["max_iter"], P["sigma"])
        decision = f"infinity_{outcome}"
        history.append({"pass_id": "∞", "c": (c.real, c.imag), "outcome": outcome, "iters": iters})

    return {"decision": decision, "params": P, "history": history}
