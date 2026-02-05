"""Tests for the content analyzer module"""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

import sys
sys.path.insert(0, "/opt/claude-ceo/workspace/arkwatch")

from src.analyzer.analyzer import ContentAnalyzer, AnalysisResult


class TestAnalysisResult:
    """Tests for AnalysisResult dataclass"""

    def test_analysis_result_creation(self):
        """Test creating an AnalysisResult"""
        result = AnalysisResult(
            summary="Content was updated",
            key_changes=["Price changed", "Stock updated"],
            sentiment="positive",
            importance="high",
            analyzed_at=datetime.utcnow(),
            model_used="mistral",
        )
        assert result.summary == "Content was updated"
        assert len(result.key_changes) == 2
        assert result.error is None

    def test_analysis_result_with_error(self):
        """Test AnalysisResult with error"""
        result = AnalysisResult(
            summary="Analyse non disponible",
            key_changes=[],
            sentiment="neutral",
            importance="medium",
            analyzed_at=datetime.utcnow(),
            model_used="mistral",
            error="Ollama connection failed",
        )
        assert result.error == "Ollama connection failed"


class TestContentAnalyzer:
    """Tests for ContentAnalyzer class"""

    def test_analyzer_init_defaults(self):
        """Test ContentAnalyzer initialization with defaults"""
        analyzer = ContentAnalyzer()
        assert analyzer.ollama_url == "http://localhost:11434"
        assert analyzer.model == "mistral"

    def test_analyzer_init_custom(self):
        """Test ContentAnalyzer with custom settings"""
        analyzer = ContentAnalyzer(
            ollama_url="http://custom:8080",
            model="llama2"
        )
        assert analyzer.ollama_url == "http://custom:8080"
        assert analyzer.model == "llama2"

    def test_error_result(self):
        """Test _error_result method"""
        analyzer = ContentAnalyzer()
        result = analyzer._error_result("Test error")

        assert result.summary == "Analyse non disponible"
        assert result.key_changes == []
        assert result.sentiment == "neutral"
        assert result.importance == "medium"
        assert result.error == "Test error"


@pytest.mark.asyncio
class TestAnalyzerAsync:
    """Async tests for ContentAnalyzer"""

    async def test_analyze_changes_success(self):
        """Test successful analysis"""
        analyzer = ContentAnalyzer()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": json.dumps({
                "summary": "Prix réduit de 20%",
                "key_changes": ["Prix: 100€ → 80€", "Promotion ajoutée"],
                "sentiment": "positive",
                "importance": "high"
            })
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await analyzer.analyze_changes(
                url="https://example.com/product",
                old_content="Prix: 100€",
                new_content="Prix: 80€ - Promotion!",
                diff="-Prix: 100€\n+Prix: 80€ - Promotion!"
            )

            assert result.summary == "Prix réduit de 20%"
            assert len(result.key_changes) == 2
            assert result.sentiment == "positive"
            assert result.importance == "high"
            assert result.error is None

    async def test_analyze_changes_ollama_error(self):
        """Test analysis with Ollama error"""
        analyzer = ContentAnalyzer()

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await analyzer.analyze_changes(
                url="https://example.com",
                old_content="old",
                new_content="new",
                diff="-old\n+new"
            )

            assert result.error is not None
            assert "500" in result.error

    async def test_analyze_changes_connection_error(self):
        """Test analysis with connection error"""
        analyzer = ContentAnalyzer()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(side_effect=Exception("Connection refused"))
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await analyzer.analyze_changes(
                url="https://example.com",
                old_content="old",
                new_content="new",
                diff="-old\n+new"
            )

            assert result.error is not None
            assert "Connection refused" in result.error

    async def test_analyze_changes_invalid_json(self):
        """Test analysis with invalid JSON response"""
        analyzer = ContentAnalyzer()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "This is not valid JSON at all"
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await analyzer.analyze_changes(
                url="https://example.com",
                old_content="old",
                new_content="new",
                diff="-old\n+new"
            )

            # Should fallback to raw text
            assert result.error is None
            assert "This is not valid JSON" in result.summary

    async def test_summarize_content_success(self):
        """Test successful content summarization"""
        analyzer = ContentAnalyzer()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "Résumé du contenu web."
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await analyzer.summarize_content("Long content here...")

            assert result == "Résumé du contenu web."

    async def test_summarize_content_error(self):
        """Test summarization with error"""
        analyzer = ContentAnalyzer()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(side_effect=Exception("Network error"))
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await analyzer.summarize_content("Content")

            assert result == "Erreur lors du résumé"
