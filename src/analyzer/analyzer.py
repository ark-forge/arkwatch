"""Content analyzer using Mistral API (was Ollama)"""

import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

# Ajouter le path pour importer mistral_client
sys.path.insert(0, "/opt/claude-ceo/automation")

# Charger les credentials Mistral
CREDENTIALS_FILE = "/opt/claude-ceo/config/mistral_credentials.env"
if Path(CREDENTIALS_FILE).exists():
    with open(CREDENTIALS_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
MISTRAL_API_URL = os.environ.get("MISTRAL_API_URL", "https://api.mistral.ai/v1")


@dataclass
class AnalysisResult:
    """Result of AI analysis"""

    summary: str
    key_changes: list[str]
    sentiment: str  # positive, negative, neutral
    importance: str  # low, medium, high, critical
    analyzed_at: datetime
    model_used: str
    error: str | None = None


class ContentAnalyzer:
    """Analyze content changes using Mistral API"""

    def __init__(self, model: str = "mistral-small-latest"):
        self.model = model
        self.api_url = f"{MISTRAL_API_URL}/chat/completions"
        self.api_key = MISTRAL_API_KEY

    async def analyze_changes(self, url: str, old_content: str, new_content: str, diff: str) -> AnalysisResult:
        """Analyze changes between old and new content"""

        prompt = f"""Tu es un assistant d'analyse de veille web. Analyse les changements suivants sur une page web.

URL surveillée: {url}

Diff des changements:
{diff[:2000]}

Réponds en JSON avec ce format exact:
{{
    "summary": "Résumé en 1-2 phrases des changements",
    "key_changes": ["changement 1", "changement 2"],
    "sentiment": "positive|negative|neutral",
    "importance": "low|medium|high|critical"
}}

Réponds UNIQUEMENT avec le JSON, sans texte avant ou après."""

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    self.api_url,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={
                        "model": self.model,
                        "temperature": 0.3,
                        "max_tokens": 500,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )

                if response.status_code != 200:
                    return self._error_result(f"Mistral error: {response.status_code}")

                result = response.json()
                text = result["choices"][0]["message"]["content"]

                # Parse JSON response
                try:
                    # Find JSON in response
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    if start >= 0 and end > start:
                        data = json.loads(text[start:end])
                        return AnalysisResult(
                            summary=data.get("summary", "Analyse non disponible"),
                            key_changes=data.get("key_changes", []),
                            sentiment=data.get("sentiment", "neutral"),
                            importance=data.get("importance", "medium"),
                            analyzed_at=datetime.now(UTC),
                            model_used=self.model,
                        )
                except json.JSONDecodeError:
                    pass

                # Fallback if JSON parsing fails
                return AnalysisResult(
                    summary=text[:500],
                    key_changes=[],
                    sentiment="neutral",
                    importance="medium",
                    analyzed_at=datetime.now(UTC),
                    model_used=self.model,
                )

        except Exception as e:
            return self._error_result(str(e))

    async def summarize_content(self, content: str, max_length: int = 200) -> str:
        """Summarize content"""
        prompt = f"""Résume ce contenu web en {max_length} caractères maximum, en français:

{content[:3000]}

Résumé:"""

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    self.api_url,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={
                        "model": self.model,
                        "temperature": 0.3,
                        "max_tokens": 200,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )

                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"][:max_length]
                return "Résumé non disponible"
        except Exception:
            return "Erreur lors du résumé"

    def _error_result(self, error: str) -> AnalysisResult:
        return AnalysisResult(
            summary="Analyse non disponible",
            key_changes=[],
            sentiment="neutral",
            importance="medium",
            analyzed_at=datetime.now(UTC),
            model_used=self.model,
            error=error,
        )


# Test
async def test_analyzer():
    analyzer = ContentAnalyzer()

    old = "Prix: 100 EUR. Stock: disponible."
    new = "Prix: 80 EUR. Stock: limité. Promotion!"
    diff = "-Prix: 100 EUR. Stock: disponible.\n+Prix: 80 EUR. Stock: limité. Promotion!"

    result = await analyzer.analyze_changes("https://example.com/product", old, new, diff)
    print(f"Summary: {result.summary}")
    print(f"Changes: {result.key_changes}")
    print(f"Importance: {result.importance}")
    print(f"Model: {result.model_used}")
    if result.error:
        print(f"Error: {result.error}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_analyzer())
