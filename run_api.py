#!/usr/bin/env python3
"""ArkWatch API Runner"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
    )
