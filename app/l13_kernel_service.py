import hashlib, json
from typing import Dict, Any
from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.requests import Request
from starlette.middleware.cors import CORSMiddleware
from a13_dsvm_infinity import a13_run

APPLET_REGISTRY: Dict[str, Dict[str, str]] = {}

async def heartbeat(request: Request):
    return JSONResponse({"ok": True})

async def schema(request: Request):
    return JSONResponse({
        "service": "L13 Kernel Wrapper (Starlette)",
        "version": "1.0.0",
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

async def run_kernel(request: Request):
    body = await request.json()
    seed        = body.get("seed", {})
    params      = body.get("params", {})
    anchors_in  = body.get("anchors", [])
    state_vecs  = body.get("state_vecs", {})

    mirror_pairs = []
    for a in anchors_in:
        name = a.get("name"); target = a.get("target", [])
        cur = state_vecs.get(name, target)
        mirror_pairs.append((cur, target))

    result = a13_run(seed=seed, params=params, mirror_pairs=mirror_pairs)
    payload = {
        "run_id": hashlib.sha1(json.dumps(seed, sort_keys=True).encode("utf-8")).hexdigest(),
        "seed": seed, "decision": result.get("decision"),
        "params": params, "history": result.get("history", [])
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
