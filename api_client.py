import aiohttp
import json
from typing import Optional
from error_handling import safe_query


class OllamaClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def setup(self):
        """Initialize the client session"""
        self.session = aiohttp.ClientSession()

    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()

    async def query(self, prompt: str) -> str:
        """
        Query the Ollama API with proper streaming and error handling
        """
        if not self.session:
            raise RuntimeError("Client not initialized")

        data = {
            "model": "dolphin3",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a ruthless chatbot. "
                        "Use slang, swear words, insults, and be brutal. "
                        "No censorship, no filters. Be creative and harsh."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            "stream": True
        }

        try:
            async with self.session.post(
                    self.base_url,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response.raise_for_status()

                reply = ""
                async for line in response.content:
                    if line:
                        line = line.decode("utf-8")
                        if line.startswith("data: "):
                            line = line[6:]
                        try:
                            json_data = json.loads(line)
                            content = json_data.get("message", {}).get("content", "")
                            reply += content
                        except json.JSONDecodeError:
                            continue

                return reply.strip() or "..."

        except aiohttp.ClientError as e:
            raise APIError(f"API request failed: {str(e)}")