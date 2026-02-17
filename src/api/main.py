"""ArkWatch API - Point d'entrée principal"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .middleware.page_visit_tracker import PageVisitTracker
from .routers import alert_hot_visit, arkwatch_checkout, audit_gratuit, audit_gratuit_exit_capture, auth, billing, conversion_dashboard, conversion_metrics, early_adopter, email_tracking, first_3, free_trial, health, leadgen_analytics, lifetime, mcp_checkout, page_visit_alert, pricing, pricing_ab, quick_check, reports, stats, subscribe, support_email, track_visitor_audit_gratuit, trial_14d, trial_signup, trial_tracking, try_check, unified_email_tracking, watches, webhooks

is_dev = os.getenv("ARKWATCH_ENV", "production") == "development"

app = FastAPI(
    title="ArkWatch API",
    description="Web monitoring API with AI-powered change summaries. Free tier: 3 URLs, daily checks.",
    version="0.1.0",
    docs_url="/docs" if is_dev else None,
    redoc_url="/redoc" if is_dev else None,
    openapi_url="/openapi.json" if is_dev else None,
)

# Page visit tracking for conversion monitoring
app.add_middleware(PageVisitTracker)

# CORS - restricted to actual methods and headers used
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://arkforge.fr"] if not is_dev else ["https://arkforge.fr", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

# Routers
app.include_router(health.router, tags=["Health"])
app.include_router(quick_check.router, prefix="/api/v1", tags=["Quick Check"])
app.include_router(try_check.router, prefix="/api", tags=["Try Before Signup"])
app.include_router(watches.router, prefix="/api/v1", tags=["Watches"])
app.include_router(reports.router, prefix="/api/v1", tags=["Reports"])
app.include_router(pricing.router, tags=["Pricing"])
app.include_router(billing.router, tags=["Billing"])
app.include_router(webhooks.router, tags=["Webhooks"])
app.include_router(auth.router, tags=["Auth"])
app.include_router(early_adopter.router, tags=["Early Adopter"])
app.include_router(free_trial.router, tags=["Free Trial"])
app.include_router(subscribe.router, tags=["Subscribe"])
app.include_router(lifetime.router, tags=["Lifetime"])
app.include_router(first_3.router, tags=["First 3 Customers"])
app.include_router(trial_14d.router, tags=["Trial 14 Days"])
app.include_router(trial_signup.router, tags=["Trial Signup"])
app.include_router(trial_tracking.router, tags=["Trial Tracking"])
app.include_router(stats.router, tags=["Stats"])
app.include_router(leadgen_analytics.router, tags=["Lead Analytics"])
app.include_router(email_tracking.router, tags=["Email Tracking"])
app.include_router(page_visit_alert.router, tags=["Page Visit Alert"])
app.include_router(alert_hot_visit.router, tags=["Alert Hot Visit"])
app.include_router(conversion_dashboard.router, tags=["Conversion Dashboard"])
app.include_router(conversion_metrics.router, tags=["Conversion Metrics"])
app.include_router(mcp_checkout.router, tags=["MCP Checkout"])
app.include_router(unified_email_tracking.router, tags=["Unified Email Tracking"])
app.include_router(support_email.router, tags=["Support Email"])
app.include_router(audit_gratuit.router, tags=["Audit Gratuit"])
app.include_router(track_visitor_audit_gratuit.router, tags=["Track Visitor Audit Gratuit"])
app.include_router(audit_gratuit_exit_capture.router, tags=["Audit Gratuit Exit Capture"])
app.include_router(arkwatch_checkout.router, tags=["ArkWatch Checkout"])
app.include_router(pricing_ab.router, tags=["Pricing A/B Test"])


@app.get("/")
async def root():
    return {
        "name": "ArkWatch API",
        "version": "0.1.0",
        "status": "running",
    }
