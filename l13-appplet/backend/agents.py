import httpx
from typing import Dict

# Define your agent registry
AGENTS = {
    "GPT-A": {
        "name": "GPT-A 🤖",
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "headers": {"Authorization": "Bearer YOUR_API_KEY_A"},
        "model": "gpt-4"
    },
    "GPT-B": {
        "name": "GPT-B 🧠",
        "endpoint": "https://api.anothergpt.com/v1/chat",
        "headers": {"Authorization": "Bearer YOUR_API_KEY_B"},
        "model": "gpt-4"
    }
}

async def query_agent(agent_id: str, prompt: str) -> Dict[str, str]:
    agent = AGENTS[agent_id]
    payload = {
        "model": agent["model"],
        "messages": [{"role": "user", "content": prompt}]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(agent["endpoint"], json=payload, headers=agent["headers"])
        data = response.json()
        reply = data["choices"][0]["message"]["content"]
        return {
            "agent": agent["name"],
            "response": reply
        }
