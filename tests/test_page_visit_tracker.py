"""Test du middleware PageVisitTracker"""

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Import the middleware
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "api"))

from middleware.page_visit_tracker import PageVisitTracker


@pytest.fixture
def temp_log_file(tmp_path):
    """Create temporary log file"""
    log_file = tmp_path / "test_visits.json"
    return str(log_file)


@pytest.fixture
def tracker(temp_log_file):
    """Create tracker instance with temp log file"""
    tracker = PageVisitTracker(None)
    tracker.LOG_FILE = temp_log_file
    return tracker


@pytest.mark.asyncio
async def test_tracked_pages_logged(tracker, temp_log_file):
    """Test that tracked pages are logged"""
    # Mock request
    request = MagicMock()
    request.url.path = "/pricing"
    request.client.host = "192.168.1.1"
    request.headers.get = lambda key, default: {
        "user-agent": "Mozilla/5.0",
        "referer": "https://google.com"
    }.get(key, default)
    request.query_params = {}

    # Mock call_next
    call_next = AsyncMock(return_value=MagicMock())

    # Process request
    await tracker.dispatch(request, call_next)

    # Verify log file created
    assert Path(temp_log_file).exists()

    # Verify content
    with open(temp_log_file) as f:
        visits = json.load(f)

    assert len(visits) == 1
    assert visits[0]["page"] == "/pricing"
    assert visits[0]["ip"] == "192.168.1.1"
    assert visits[0]["user_agent"] == "Mozilla/5.0"
    assert visits[0]["referrer"] == "https://google.com"


@pytest.mark.asyncio
async def test_non_tracked_pages_not_logged(tracker, temp_log_file):
    """Test that non-tracked pages are not logged"""
    # Mock request to non-tracked page
    request = MagicMock()
    request.url.path = "/api/v1/watches"
    request.client.host = "192.168.1.1"
    request.headers.get = lambda key, default: "Mozilla/5.0" if key == "user-agent" else default
    request.query_params = {}

    # Mock call_next
    call_next = AsyncMock(return_value=MagicMock())

    # Process request
    await tracker.dispatch(request, call_next)

    # Verify no log file created
    assert not Path(temp_log_file).exists()


@pytest.mark.asyncio
async def test_multiple_visits_appended(tracker, temp_log_file):
    """Test that multiple visits are appended"""
    # Create initial log
    Path(temp_log_file).parent.mkdir(parents=True, exist_ok=True)
    with open(temp_log_file, 'w') as f:
        json.dump([{"page": "/demo", "ip": "1.1.1.1"}], f)

    # Mock new request
    request = MagicMock()
    request.url.path = "/trial"
    request.client.host = "2.2.2.2"
    request.headers.get = lambda key, default: "Mozilla/5.0" if key == "user-agent" else default
    request.query_params = {}

    call_next = AsyncMock(return_value=MagicMock())

    # Process request
    await tracker.dispatch(request, call_next)

    # Verify both visits present
    with open(temp_log_file) as f:
        visits = json.load(f)

    assert len(visits) == 2
    assert visits[0]["ip"] == "1.1.1.1"
    assert visits[1]["ip"] == "2.2.2.2"


@pytest.mark.asyncio
async def test_log_rotation_keeps_last_10000(tracker, temp_log_file):
    """Test that log rotation keeps only last 10000 visits"""
    # Create log with 10001 entries
    Path(temp_log_file).parent.mkdir(parents=True, exist_ok=True)
    with open(temp_log_file, 'w') as f:
        visits = [{"page": "/demo", "ip": f"{i}.{i}.{i}.{i}"} for i in range(10001)]
        json.dump(visits, f)

    # Mock new request
    request = MagicMock()
    request.url.path = "/pricing"
    request.client.host = "new.new.new.new"
    request.headers.get = lambda key, default: "Mozilla/5.0" if key == "user-agent" else default
    request.query_params = {}

    call_next = AsyncMock(return_value=MagicMock())

    # Process request
    await tracker.dispatch(request, call_next)

    # Verify only 10000 visits kept
    with open(temp_log_file) as f:
        visits = json.load(f)

    assert len(visits) == 10000
    # Oldest entry (0.0.0.0) should be removed
    assert not any(v["ip"] == "0.0.0.0" for v in visits)
    # Newest entry should be present
    assert visits[-1]["ip"] == "new.new.new.new"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
