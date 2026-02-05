"""ArkWatch API - Point d'entrée principal"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import watches, reports, health, billing, webhooks

app = FastAPI(
    title="ArkWatch API",
    description="Service de veille IA automatisée",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://arkforge.fr", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, tags=["Health"])
app.include_router(watches.router, prefix="/api/v1", tags=["Watches"])
app.include_router(reports.router, prefix="/api/v1", tags=["Reports"])
app.include_router(billing.router, tags=["Billing"])
app.include_router(webhooks.router, tags=["Webhooks"])


@app.get("/")
async def root():
    return {
        "name": "ArkWatch API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs"
    }
