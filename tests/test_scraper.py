"""Tests for the web scraper module"""
import pytest
import hashlib
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

import sys
sys.path.insert(0, "/opt/claude-ceo/workspace/arkwatch")

from src.scraper.scraper import WebScraper, ScrapeResult


class TestScrapeResult:
    """Tests for ScrapeResult dataclass"""

    def test_scrape_result_creation(self):
        """Test creating a ScrapeResult"""
        result = ScrapeResult(
            url="https://example.com",
            status_code=200,
            content_hash="abc123",
            text_content="Test content",
            title="Test Title",
            scraped_at=datetime.utcnow(),
        )
        assert result.url == "https://example.com"
        assert result.status_code == 200
        assert result.error is None

    def test_scrape_result_with_error(self):
        """Test ScrapeResult with error"""
        result = ScrapeResult(
            url="https://example.com",
            status_code=0,
            content_hash="",
            text_content="",
            title=None,
            scraped_at=datetime.utcnow(),
            error="Connection timeout",
        )
        assert result.error == "Connection timeout"
        assert result.status_code == 0


class TestWebScraper:
    """Tests for WebScraper class"""

    def test_scraper_init(self):
        """Test WebScraper initialization"""
        scraper = WebScraper(timeout=60)
        assert scraper.timeout == 60
        assert "ArkWatch" in scraper.headers["User-Agent"]

    def test_scraper_default_timeout(self):
        """Test default timeout value"""
        scraper = WebScraper()
        assert scraper.timeout == 30


class TestComputeDiff:
    """Tests for compute_diff static method"""

    def test_no_changes(self):
        """Test when content is identical"""
        old = "Same content"
        new = "Same content"
        has_changes, diff = WebScraper.compute_diff(old, new)
        assert has_changes is False
        assert diff == ""

    def test_with_changes(self):
        """Test when content has changed"""
        old = "Old content\nLine 2"
        new = "New content\nLine 2"
        has_changes, diff = WebScraper.compute_diff(old, new)
        assert has_changes is True
        assert "-Old content" in diff
        assert "+New content" in diff

    def test_added_lines(self):
        """Test when lines are added"""
        old = "Line 1"
        new = "Line 1\nLine 2"
        has_changes, diff = WebScraper.compute_diff(old, new)
        assert has_changes is True
        assert "+Line 2" in diff

    def test_removed_lines(self):
        """Test when lines are removed"""
        old = "Line 1\nLine 2"
        new = "Line 1"
        has_changes, diff = WebScraper.compute_diff(old, new)
        assert has_changes is True
        assert "-Line 2" in diff


class TestContentHash:
    """Tests for content hashing"""

    def test_hash_consistency(self):
        """Test that same content produces same hash"""
        content = "Test content for hashing"
        hash1 = hashlib.sha256(content.encode()).hexdigest()[:16]
        hash2 = hashlib.sha256(content.encode()).hexdigest()[:16]
        assert hash1 == hash2

    def test_hash_different_content(self):
        """Test that different content produces different hash"""
        content1 = "Content version 1"
        content2 = "Content version 2"
        hash1 = hashlib.sha256(content1.encode()).hexdigest()[:16]
        hash2 = hashlib.sha256(content2.encode()).hexdigest()[:16]
        assert hash1 != hash2

    def test_hash_length(self):
        """Test that hash is truncated to 16 chars"""
        content = "Test content"
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        assert len(content_hash) == 16


@pytest.mark.asyncio
class TestScraperAsync:
    """Async tests for WebScraper"""

    async def test_scrape_success(self, sample_html_content):
        """Test successful scrape with mocked response"""
        scraper = WebScraper()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = sample_html_content

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await scraper.scrape("https://example.com")

            assert result.status_code == 200
            assert result.title == "Test Page"
            assert result.error is None
            assert "Main Content" in result.text_content
            # Nav, footer, script should be removed
            assert "Navigation" not in result.text_content
            assert "Footer" not in result.text_content

    async def test_scrape_error(self):
        """Test scrape with network error"""
        scraper = WebScraper()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(side_effect=Exception("Connection failed"))
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await scraper.scrape("https://invalid.example")

            assert result.status_code == 0
            assert result.error is not None
            assert "Connection failed" in result.error
