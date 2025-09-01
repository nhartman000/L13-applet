import hashlib, json
from typing import Dict, Any
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.requests import Request
from starlette.middleware.cors import CORSMiddleware
from a13_dsvm_infinity import a13_run, encode_context, DEFAULTS

APPLET_REGISTRY: Dict[str, Dict[str, str]] = {}

async def heartbeat(request: Request):
    return JSONResponse({"ok": True})

async def schema(request: Request):
    return JSONResponse({
        "service": "L13 Kernel Wrapper (Starlette)",
        "version": "1.0.1",
        "endpoints": ["GET /heartbeat", "GET /schema", "POST /run", "POST /register_applet"]
    })

async def register_applet(request: Request):
    body = await request.json()
    name, endpoint, token = body.get("name"), body.get("endpoint"), body.get("token")
    if not name or not endpoint:
        return JSONResponse({"error": "name and endpoint required"}, status_code=400)
    APPLET_REGISTRY[name] = {"endpoint": endpoint}
    if token: APPLET_REGISTRY[name]["token"] = token
    return JSONResponse({"ok": True, "registered": list(APPLET_REGISTRY.keys())})

def _extract_julia_c(history, seed):
    for h in history or []:
        if h.get("pass_id") == "∞" and "c" in h:
            cre, cim = h["c"]
            return float(cre), float(cim)
    c = encode_context(seed or {})
    return float(c.real), float(c.imag)

async def run_kernel(request: Request):
    body = await request.json()
    seed        = body.get("seed", {})
    params      = {**DEFAULTS, **(body.get("params", {}) or {})}
    anchors_in  = body.get("anchors", [])
    state_vecs  = body.get("state_vecs", {})
    fanout      = body.get("fanout_applets", [])

    mirror_pairs = []
    for a in anchors_in:
        name = a.get("name"); target = a.get("target", [])
        cur = state_vecs.get(name, target)
        mirror_pairs.append((cur, target))

    result = a13_run(seed=seed, params=params, mirror_pairs=mirror_pairs)
    run_id = hashlib.sha1(json.dumps(seed, sort_keys=True).encode("utf-8")).hexdigest()

    active_attractor = (body.get("params", {}) or {}).get("attractor", "julia").lower()
    if active_attractor not in ("julia", "mandelbulb"):
        active_attractor = "julia"

    cre, cim = _extract_julia_c(result.get("history"), seed)
    viz = {
        "attractor": active_attractor,
        "julia": {"c": [cre, cim], "p": int(params.get("p", 2)), "R": float(params.get("R", 2.0))},
        "mandelbulb": {"p": 8, "max_steps": 96, "bailout": 8.0}  # visualization defaults
    }

    payload = {
        "run_id": run_id,
        "decision": result.get("decision"),
        "params": params,
        "history": result.get("history", []),
        "viz": viz,
        "broker": {"applets_requested": fanout, "fanout": []}  # (hook up later)
    }
    return JSONResponse(payload)

routes = [
    Route("/heartbeat", heartbeat, methods=["GET"]),
    Route("/schema", schema, methods=["GET"]),
    Route("/register_applet", register_applet, methods=["POST"]),
    Route("/run", run_kernel, methods=["POST"]),
]
app = Starlette(debug=False, routes=routes)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
