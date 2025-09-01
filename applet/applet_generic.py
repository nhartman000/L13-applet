import json, os, asyncio, logging
import httpx
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GPT_URL = os.getenv("GPT_URL", "https://api.openai.com/v1/chat/completions")
GPT_BEARER = os.getenv("GPT_BEARER", "")
APPLET_STUB = os.getenv("APPLET_STUB", "false").lower() == "true"

async def call_llm_with_retries(prompt: str, max_retries: int = 3) -> dict:
    if APPLET_STUB:
        logger.info("Using stub mode - returning mock response")
        return {"response": f"Mock LLM response for: {prompt[:50]}..."}
    
    if not GPT_BEARER:
        raise ValueError("GPT_BEARER environment variable not set")
    
    headers = {
        "Authorization": f"Bearer {GPT_BEARER}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": 0.7
    }
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(GPT_URL, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]
                    logger.info(f"LLM call successful on attempt {attempt + 1}")
                    return {"response": content}
                else:
                    raise ValueError("Invalid response format from LLM API")
                    
        except httpx.TimeoutException:
            logger.warning(f"LLM API timeout on attempt {attempt + 1}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
            
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM API HTTP error {e.response.status_code} on attempt {attempt + 1}")
            if e.response.status_code == 429:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
            else:
                raise
                
        except Exception as e:
            logger.error(f"LLM API error on attempt {attempt + 1}: {str(e)}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
    
    raise Exception("Max retries exceeded for LLM API call")

async def ingest(request: Request):
    try:
        payload = await request.json()
        prompt = payload.get("prompt", "")
        
        if not prompt:
            return JSONResponse({"error": "prompt field required"}, status_code=400)
        
        logger.info(f"Processing prompt: {prompt[:100]}...")
        
        llm_result = await call_llm_with_retries(prompt)
        
        return JSONResponse({
            "ok": True,
            "prompt": prompt,
            "llm_response": llm_result["response"],
            "stub_mode": APPLET_STUB
        })
        
    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        return JSONResponse({"error": f"Configuration error: {str(e)}"}, status_code=500)
        
    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        return JSONResponse({"error": f"Processing failed: {str(e)}"}, status_code=500)

routes = [Route("/ingest", ingest, methods=["POST"])]
app = Starlette(debug=False, routes=routes)
