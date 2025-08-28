from fastapi import FastAPI, Request
from backend.kernel import auto13_run
from backend.agents import query_agent
import time

app = FastAPI()
start_time = time.time()

@app.post("/multi-agent")
async def multi_agent_chat(req: Request):
    body = await req.json()
    prompt = body.get("prompt", "")
    seed = body.get("seed", {"prompt": prompt})

    # Query external agents
    agent_a = await query_agent("GPT-A", prompt)
    agent_b = await query_agent("GPT-B", prompt)

    # Run kernel logic
    kernel_result = auto13_run(seed)

    # Compute elapsed time
    elapsed = int(time.time() - start_time)

    return {
        "elapsed": elapsed,
        "user_prompt": prompt,
        "agent_a": agent_a,
        "agent_b": agent_b,
        "kernel": kernel_result
    }
