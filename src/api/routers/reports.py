"""Reports endpoints with authentication"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from ...storage import get_db
from ..auth import get_current_user

router = APIRouter()


@router.get("/reports")
async def list_reports(
    watch_id: Optional[str] = None, 
    limit: int = 100,
    user: dict = Depends(get_current_user)
):
    db = get_db()
    
    # If watch_id provided, verify ownership
    if watch_id:
        watch = db.get_watch(watch_id)
        if not watch:
            raise HTTPException(status_code=404, detail="Watch not found")
        if user["tier"] != "business" and watch.get("user_email") != user["email"]:
            raise HTTPException(status_code=403, detail="Access denied")
        return db.get_reports(watch_id=watch_id, limit=limit)
    
    # Get all reports for user's watches
    reports = db.get_reports(limit=limit)
    
    if user["tier"] != "business":
        user_watches = {w["id"] for w in db.get_watches() if w.get("user_email") == user["email"]}
        reports = [r for r in reports if r["watch_id"] in user_watches]
    
    return reports


@router.get("/reports/{report_id}")
async def get_report(report_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    reports = db.get_reports()
    
    for report in reports:
        if report["id"] == report_id:
            # Verify ownership
            watch = db.get_watch(report["watch_id"])
            if user["tier"] != "business" and watch and watch.get("user_email") != user["email"]:
                raise HTTPException(status_code=403, detail="Access denied")
            return report
    
    raise HTTPException(status_code=404, detail="Report not found")
