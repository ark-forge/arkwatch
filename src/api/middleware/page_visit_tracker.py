"""Middleware pour tracker les visites des pages clés ArkWatch"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class PageVisitTracker(BaseHTTPMiddleware):
    """Track visits to key conversion pages"""

    TRACKED_PAGES = ["/demo", "/pricing", "/trial"]
    LOG_DIR = "/opt/claude-ceo/workspace/arkwatch/logs"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if this is a tracked page
        path = request.url.path

        if any(path.startswith(page) for page in self.TRACKED_PAGES):
            # Log the visit
            self._log_visit(request)

        response = await call_next(request)
        return response

    def _log_visit(self, request: Request):
        """Log visit data to JSON file"""
        try:
            visit_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "page": request.url.path,
                "ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
                "referrer": request.headers.get("referer", "direct"),
                "query_params": dict(request.query_params) if request.query_params else {}
            }

            # Ensure directory exists - use dynamic date for log rotation
            today = datetime.utcnow().strftime("%Y%m%d")
            log_path = Path(self.LOG_DIR) / f"page_visits_{today}.json"
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # Read existing data
            visits = []
            if log_path.exists():
                try:
                    with open(log_path, 'r') as f:
                        visits = json.load(f)
                except (json.JSONDecodeError, ValueError):
                    visits = []

            # Append new visit
            visits.append(visit_data)

            # Write back (keep last 10000 visits to avoid file bloat)
            with open(log_path, 'w') as f:
                json.dump(visits[-10000:], f, indent=2)

        except Exception as e:
            # Silent fail - don't break the app for logging issues
            print(f"Error logging page visit: {e}")
