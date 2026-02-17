#!/usr/bin/env python3
"""ArkWatch Worker Runner"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.worker import ArkWatchWorker


async def main():
    worker = ArkWatchWorker()
    
    # Run once if --once flag
    if "--once" in sys.argv:
        await worker.run_cycle()
    else:
        # Run forever with 5 minute intervals
        await worker.run_forever(check_interval=300)


if __name__ == "__main__":
    print("Starting ArkWatch Worker...")
    asyncio.run(main())
