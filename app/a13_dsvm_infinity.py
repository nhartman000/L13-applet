from __future__ import annotations
import hashlib, json, math, random
from typing import Dict, Any, Tuple, List

DEFAULTS = dict(
    p=2, R=2.0, epsilon=0.1, tau=0.05, sigma=0.0, max_iter=1024
)

def encode_context(features: Dict[str, Any]) -> complex:
    items = sorted((str(k), str(features[k])) for k in features)
    blob = "|".join(f"{k}={v}" for k, v in items).encode("utf-8")
    h = hashlib.sha256(blob).digest()
    def to_unit(b: bytes) -> float:
        n = int.from_bytes(b, "big") / (1 << 64)
        return 2.0 * n - 1.0
    return complex(to_unit(h[:8]), to_unit(h[8:16]))

def dsvm_residual(x: List[float], y: List[float]) -> float:
    num = math.sqrt(sum((a - b) ** 2 for a, b in zip(x, y)))
    den = math.sqrt(sum(a*a for a in x)) or 1.0
    return num / den

def julia_infinity(c: complex, p: int=2, R: float=2.0, max_iter: int=1024, sigma: float=0.0) -> Tuple[str,int]:
    z = 0+0j
    for i in range(max_iter):
        drift = sigma*(random.random()-0.5) + 1j*sigma*(random.random()-0.5)
        z = (z**p) + c + drift
        if abs(z) > R: return "escape", i
    return "bounded", max_iter

def compute_delta(cur: Dict[str, Any], prev: Dict[str, Any]) -> float:
    if prev is None: return 1.0
    cur_items, prev_items = set(cur.items()), set(prev.items())
    inter, union = len(cur_items & prev_items), max(len(cur_items | prev_items), 1)
    return 1.0 - inter/union

def a13_run(seed: Dict[str, Any], params: Dict[str, Any]=None,
            mirror_pairs: List[Tuple[List[float], List[float]]] = None,
            log_path: str = None) -> Dict[str, Any]:
    P = {**DEFAULTS, **(params or {})}
    history, prev_state, decision = [], None, "continue"

    for k in range(1, 14):
        state = dict(pass_id=k, data=dict(seed))
        if mirror_pairs:
            rmax = max(dsvm_residual(a, b) for (a, b) in mirror_pairs)
            state["dsvm_r"] = rmax
            if rmax > P["tau"]:
                decision = "escape_dsvm"; history.append(state); break
        delta = compute_delta(state["data"], prev_state)
        state["delta"] = delta; history.append(state); prev_state = state["data"]
        if delta <= P["epsilon"]:
            decision = "converged_a13"; break

    if decision not in ("converged_a13","escape_dsvm"):
        c = encode_context(seed)
        outcome, iters = julia_infinity(c, p=P["p"], R=P["R"], max_iter=P["max_iter"], sigma=P["sigma"])
        decision = f"infinity_{outcome}"
        history.append({"pass_id":"∞","c":(c.real,c.imag),"outcome":outcome,"iters":iters})

    result = {"decision": decision, "params": P, "history": history}
    if log_path:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
    return result
