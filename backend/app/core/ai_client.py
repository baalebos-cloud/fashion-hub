import httpx
from app.core.config import settings
from app.core.exceptions import ExternalAPIError

class N8nAIClient:
    def __init__(self):
        self.url = getattr(settings, "AI_API_URL", "http://localhost:5678")
        self.token = getattr(settings, "AI_API_KEY", "")

    async def generate_response(self, prompt: str, system_instruction: str = None) -> str:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        payload = {
            "message": prompt,
            "system_prompt": system_instruction,
            "source": "fashion_hub_backend"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(self.url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                # Standardized response normalization path across varied n8n workflows
                if isinstance(data, dict):
                    return data.get("output") or data.get("response") or data.get("text") or str(data)
                return str(data)
                
            except httpx.HTTPStatusError as e:
                raise ExternalAPIError(f"n8n Gateway communication error: {e.response.text}")
            except Exception as e:
                raise ExternalAPIError(f"Failed to route message through n8n gateway: {str(e)}")

# Instantiate global service singleton
ai_client = N8nAIClient()
