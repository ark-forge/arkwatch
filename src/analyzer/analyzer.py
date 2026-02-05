"""Content analyzer using Ollama"""
import httpx
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class AnalysisResult:
    """Result of AI analysis"""
    summary: str
    key_changes: list[str]
    sentiment: str  # positive, negative, neutral
    importance: str  # low, medium, high, critical
    analyzed_at: datetime
    model_used: str
    error: Optional[str] = None


class ContentAnalyzer:
    """Analyze content changes using Ollama"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "mistral"):
        self.ollama_url = ollama_url
        self.model = model
    
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
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 500,
                        }
                    }
                )
                
                if response.status_code != 200:
                    return self._error_result(f"Ollama error: {response.status_code}")
                
                result = response.json()
                text = result.get("response", "")
                
                # Parse JSON response
                import json
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
                            analyzed_at=datetime.utcnow(),
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
                    analyzed_at=datetime.utcnow(),
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
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 200,
                        }
                    }
                )
                
                if response.status_code == 200:
                    return response.json().get("response", "")[:max_length]
                return "Résumé non disponible"
        except:
            return "Erreur lors du résumé"
    
    def _error_result(self, error: str) -> AnalysisResult:
        return AnalysisResult(
            summary="Analyse non disponible",
            key_changes=[],
            sentiment="neutral",
            importance="medium",
            analyzed_at=datetime.utcnow(),
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
    if result.error:
        print(f"Error: {result.error}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_analyzer())
