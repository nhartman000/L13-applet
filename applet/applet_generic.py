import json, os
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse

async def ingest(request: Request):
    payload = await request.json()
    # Minimal echo stub
    return JSONResponse({"ok": True, "echo": payload})

routes = [Route("/ingest", ingest, methods=["POST"])]
app = Starlette(debug=False, routes=routes)
