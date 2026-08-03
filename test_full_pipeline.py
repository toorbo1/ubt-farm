"""Test the full 3-AI pipeline locally."""
import asyncio, sys, os
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from video_engine.builder import VideoBuilder

async def main():
    builder = VideoBuilder()
    print("=" * 60)
    print("FULL PIPELINE TEST (AI#1 + AI#2 + AI#3)")
    print("=" * 60)

    try:
        out = await builder.build(topic="кибербезопасность")
        print(f"\n=== SUCCESS ===")
        print(f"Output: {out}")
        print(f"Size: {out.stat().st_size} bytes")
    except Exception as e:
        print(f"\n=== FAILED ===")
        import traceback
        traceback.print_exc()

    await builder.cleanup()

asyncio.run(main())
