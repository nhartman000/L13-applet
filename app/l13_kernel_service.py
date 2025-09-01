import hashlib, json, logging, asyncio
import httpx
from typing import Dict, Any, List
from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.requests import Request
from starlette.middleware.cors import CORSMiddleware
from a13_dsvm_infinity import a13_run

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

async def fan_out_to_applets(seed: Dict[str, Any], applet_names: List[str] = None) -> Dict[str, Any]:
    if not applet_names:
        applet_names = list(APPLET_REGISTRY.keys())
    
    fanout_results = {}
    
    for name in applet_names:
        if name not in APPLET_REGISTRY:
            fanout_results[name] = {"error": f"Applet '{name}' not registered"}
            continue
            
        applet_config = APPLET_REGISTRY[name]
        endpoint = applet_config["endpoint"]
        
        try:
            headers = {"Content-Type": "application/json"}
            if "token" in applet_config:
                headers["Authorization"] = f"Bearer {applet_config['token']}"
            
            payload = {"prompt": json.dumps(seed)}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                fanout_results[name] = response.json()
                
        except Exception as e:
            logger.error(f"Error calling applet '{name}' at {endpoint}: {str(e)}")
            fanout_results[name] = {"error": str(e)}
    
    return fanout_results

async def run_kernel(request: Request):
    body = await request.json()
    seed        = body.get("seed", {})
    params      = body.get("params", {})
    anchors_in  = body.get("anchors", [])
    state_vecs  = body.get("state_vecs", {})
    applet_names = body.get("applets", [])

    mirror_pairs = []
    for a in anchors_in:
        name = a.get("name"); target = a.get("target", [])
        cur = state_vecs.get(name, target)
        mirror_pairs.append((cur, target))

    logger.info(f"Running A13 kernel with seed: {seed}")
    result = a13_run(seed=seed, params=params, mirror_pairs=mirror_pairs)
    
    broker_fanout = {}
    if APPLET_REGISTRY or applet_names:
        logger.info(f"Fanning out to applets: {applet_names or list(APPLET_REGISTRY.keys())}")
        broker_fanout = await fan_out_to_applets(seed, applet_names)

    payload = {
        "run_id": hashlib.sha1(json.dumps(seed, sort_keys=True).encode("utf-8")).hexdigest(),
        "seed": seed, 
        "decision": result.get("decision"),
        "params": params, 
        "history": result.get("history", []),
        "broker": {
            "fanout": broker_fanout
        }
    }
    
    logger.info(f"A13 kernel completed with decision: {result.get('decision')}")
    return JSONResponse(payload)

routes = [
    Route("/heartbeat", heartbeat, methods=["GET"]),
    Route("/schema", schema, methods=["GET"]),
    Route("/register_applet", register_applet, methods=["POST"]),
    Route("/run", run_kernel, methods=["POST"]),
]
app = Starlette(debug=False, routes=routes)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
