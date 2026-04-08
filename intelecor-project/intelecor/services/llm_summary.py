import json
import structlog
from api.config import get_settings

logger = structlog.get_logger()


class LLMSummaryService:
    """
    Generates natural language practice summaries from analytics results.

    Routes to cloud (Anthropic) or local (Ollama) based on config.
    Only receives de-identified aggregate data — no patient information.
    """

    SYSTEM_PROMPT = """You are a practice intelligence assistant for an Australian 
medical specialist. Generate a concise morning briefing from the analytics data provided. 
Use Australian medical terminology (MBS items, Medicare, DVA, ECLIPSE). 
Be direct and actionable. Highlight what needs attention first, then summarise 
performance. Keep it under 200 words. Do not include any patient names or identifiers."""

    async def generate(self, tenant_id: str, results: dict | None = None) -> str:
        settings = get_settings()

        if not results:
            logger.warning("llm_summary.no_results", tenant_id=tenant_id)
            return "No analytics data available for summary generation."

        prompt = self._build_prompt(results)

        if settings.llm_provider == "anthropic":
            return await self._call_anthropic(prompt)
        elif settings.llm_provider == "ollama":
            return await self._call_ollama(prompt)
        else:
            logger.error("llm_summary.unknown_provider", provider=settings.llm_provider)
            return "LLM provider not configured."

    async def _call_anthropic(self, prompt: str) -> str:
        from anthropic import AsyncAnthropic

        settings = get_settings()
        client = AsyncAnthropic(api_key=settings.anthropic_api_key)

        try:
            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            logger.error("llm_summary.anthropic_error", error=str(e))
            return f"Summary generation failed: {str(e)}"

    async def _call_ollama(self, prompt: str) -> str:
        import httpx

        settings = get_settings()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={
                        "model": "llama3.2",
                        "prompt": f"{self.SYSTEM_PROMPT}\n\n{prompt}",
                        "stream": False,
                    },
                    timeout=60.0,
                )
                return response.json().get("response", "No response from local model.")
        except Exception as e:
            logger.error("llm_summary.ollama_error", error=str(e))
            return f"Local summary generation failed: {str(e)}"

    def _build_prompt(self, results: dict) -> str:
        return f"""Generate a morning practice briefing from these analytics results. 
Focus on what needs attention and how the practice performed this period.

Analytics data (de-identified aggregates only):

{json.dumps(results, indent=2, default=str)}"""
