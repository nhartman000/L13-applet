from __future__ import annotations
import hashlib, json, math, random, time, logging
from typing import Dict, Any, Tuple, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    start_time = time.time()

    logger.info(f"Starting A13 run with params: {P}")

    for k in range(1, 14):
        pass_start = time.time()
        state = dict(
            pass_id=k, 
            data=dict(seed),
            timestamp=pass_start,
            pass_name=f"A{k}"
        )
        
        if mirror_pairs:
            rmax = max(dsvm_residual(a, b) for (a, b) in mirror_pairs)
            state["dsvm_r"] = rmax
            logger.info(f"A{k}: DSVM residual = {rmax:.6f}")
            if rmax > P["tau"]:
                decision = "escape_dsvm"
                state["termination_reason"] = f"DSVM residual {rmax:.6f} > tau {P['tau']}"
                history.append(state)
                logger.info(f"A{k}: Terminating due to DSVM escape")
                break
                
        delta = compute_delta(state["data"], prev_state)
        state["delta"] = delta
        state["duration_ms"] = (time.time() - pass_start) * 1000
        
        logger.info(f"A{k}: Delta = {delta:.6f}")
        
        history.append(state)
        prev_state = state["data"]
        
        if delta <= P["epsilon"]:
            decision = "converged_a13"
            state["termination_reason"] = f"Delta {delta:.6f} <= epsilon {P['epsilon']}"
            logger.info(f"A{k}: Converged")
            break

    if decision not in ("converged_a13","escape_dsvm"):
        logger.info("Entering Julia infinity analysis")
        c = encode_context(seed)
        outcome, iters = julia_infinity(c, p=P["p"], R=P["R"], max_iter=P["max_iter"], sigma=P["sigma"])
        decision = f"infinity_{outcome}"
        infinity_state = {
            "pass_id": "∞",
            "pass_name": "Infinity",
            "c": (c.real, c.imag),
            "outcome": outcome,
            "iters": iters,
            "timestamp": time.time()
        }
        history.append(infinity_state)
        logger.info(f"Julia analysis: {outcome} after {iters} iterations")

    total_duration = time.time() - start_time
    result = {
        "decision": decision, 
        "params": P, 
        "history": history,
        "total_duration_ms": total_duration * 1000,
        "total_passes": len([h for h in history if h.get("pass_id") != "∞"])
    }
    
    logger.info(f"A13 run completed: {decision} in {total_duration:.3f}s")
    
    if log_path:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
    return result
