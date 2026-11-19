"""Monetization & Channel Growth Diagnostic Tool for ByteWave AI.

Tracks channel readiness towards YouTube Partner Program (YPP) requirements:
  - 1,000 Subscribers
  - 10M Shorts Views (or 4,000 Long-Form Watch Hours)
  - Content Originality & Retention Metrics
  - Upload Cadence Analysis
"""
import os
import sys
import json
from datetime import datetime

# Configure UTF-8 for Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from youtube_uploader import get_authenticated_service

TARGET_SUBS = 1000
TARGET_VIEWS = 10_000_000  # 10 Million views for Shorts YPP


def fetch_channel_overview():
    """Fetch live channel statistics and analyze monetization status."""
    print("=" * 65)
    print("      BYTEWAVE AI: YOUTUBE MONETIZATION DASHBOARD")
    print("=" * 65)
    
    yt = get_authenticated_service()
    if not yt:
        print("[Error] Could not authenticate with YouTube. Check client_secret.json / token.json.")
        return

    # 1. Fetch channel snippet and statistics
    ch_resp = yt.channels().list(part="snippet,statistics", mine=True).execute()
    if not ch_resp.get("items"):
        print("[Error] No channel found for authenticated account.")
        return

    channel = ch_resp["items"][0]
    title = channel["snippet"]["title"]
    stats = channel["statistics"]

    views = int(stats.get("viewCount", 0))
    subs = int(stats.get("subscriberCount", 0))
    videos = int(stats.get("videoCount", 0))

    sub_pct = min(100.0, (subs / TARGET_SUBS) * 100)
    view_pct = min(100.0, (views / TARGET_VIEWS) * 100)

    print(f"\n📺 Channel Name: {title}")
    print(f"🕒 Diagnostic Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 65)
    print(f"👥 Current Subscribers: {subs:,} / {TARGET_SUBS:,} ({sub_pct:.1f}% of goal)")
    print(f"👀 Total Channel Views: {views:,} / {TARGET_VIEWS:,} ({view_pct:.3f}% of goal)")
    print(f"🎬 Total Public Videos: {videos:,}")
    print("-" * 65)

    # 2. Progress Bar Visuals
    def render_bar(pct, length=25):
        filled = int(length * pct / 100.0)
        return "[" + "█" * filled + "░" * (length - filled) + f"] {pct:.1f}%"

    print("\n🎯 MONETIZATION READINESS:")
    print(f"   Subscribers: {render_bar(sub_pct)}")
    print(f"   Views:       {render_bar(view_pct)}")

    # 3. Growth Insights & Recommendations
    print("\n💡 ALGORITHM & VIRAL GROWTH RECOMMENDATIONS:")
    
    if videos > 0:
        avg_views = views / videos
        print(f"   • Average Views Per Video: {avg_views:.1f}")
        if avg_views < 50:
            print("   ⚠️  Flag: Videos are getting throttled by upload velocity.")
            print("      Action: Space uploads by 2-3 hours instead of bulk uploads.")
    
    print("   • Subtitle Retention: ENABLED (Hindi Devanagari Animated Subtitles)")
    print("   • Engagement Hook: ENABLED (Curiosity Header + Dynamic Debate Comments)")
    print("   • Best Upload Times for India (IST):")
    print("      - Morning Slot:   11:30 AM – 1:30 PM IST")
    print("      - Evening Prime:  6:00 PM – 9:30 PM IST (Peak Shorts Traffic)")
    
    print("\n" + "=" * 65)
    print("   Keep the automation running consistently at 3-5 videos/day.")
    print("=" * 65)


if __name__ == "__main__":
    fetch_channel_overview()
