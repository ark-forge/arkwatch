"""Pytest configuration and fixtures"""
import pytest
import os
import tempfile
import json
from pathlib import Path


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary data directory for tests"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return str(data_dir)


@pytest.fixture
def mock_watches_file(temp_data_dir):
    """Create a mock watches.json file"""
    watches_file = Path(temp_data_dir) / "watches.json"
    watches_file.write_text("[]")
    return str(watches_file)


@pytest.fixture
def mock_reports_file(temp_data_dir):
    """Create a mock reports.json file"""
    reports_file = Path(temp_data_dir) / "reports.json"
    reports_file.write_text("[]")
    return str(reports_file)


@pytest.fixture
def sample_watch():
    """Sample watch data"""
    return {
        "name": "Test Watch",
        "url": "https://example.com",
        "check_interval": 3600,
        "notify_email": "test@example.com"
    }


@pytest.fixture
def sample_html_content():
    """Sample HTML content for scraper tests"""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page</title></head>
    <body>
        <nav>Navigation</nav>
        <main>
            <h1>Main Content</h1>
            <p>This is the main content of the page.</p>
        </main>
        <footer>Footer content</footer>
        <script>console.log('test');</script>
    </body>
    </html>
    """
