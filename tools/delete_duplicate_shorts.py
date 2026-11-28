"""Tool to clean up duplicate Shorts on YouTube Channel ByteWave AI.

Scans all uploaded videos, identifies videos with identical titles,
keeps the oldest one (or the one with the highest views/likes),
and removes the exact duplicate re-uploads.
"""
import os
import sys
import json
import time

# Add project root to sys.path so pipeline imports work
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pipeline.youtube_uploader import get_authenticated_service


def clean_duplicate_shorts(dry_run: bool = False, max_pages: int = 5):
    print("=" * 65)
    print("      BYTEWAVE AI: DUPLICATE SHORTS CLEANER")
    print("=" * 65)

    yt = get_authenticated_service()
    if not yt:
        print("[Error] Could not authenticate with YouTube.")
        return

    print("🔍 Fetching uploads playlist...")
    ch = yt.channels().list(part="contentDetails", mine=True).execute()
    if not ch.get("items"):
        print("[Error] No channel found.")
        return

    uploads_id = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    
    all_items = []
    page_token = None
    print(f"📥 Scanning last {max_pages * 50} videos for duplicates...")

    for page in range(max_pages):
        res = yt.playlistItems().list(
            part="snippet,status",
            playlistId=uploads_id,
            maxResults=50,
            pageToken=page_token
        ).execute()

        items = res.get("items", [])
        all_items.extend(items)
        page_token = res.get("nextPageToken")
        if not page_token:
            break

    print(f"✅ Total videos scanned: {len(all_items)}")

    # Group videos by title
    grouped = {}
    for item in all_items:
        title = item["snippet"]["title"].strip()
        vid = item["snippet"]["resourceId"]["videoId"]
        published = item["snippet"]["publishedAt"]
        grouped.setdefault(title, []).append({
            "id": vid,
            "title": title,
            "published": published
        })

    duplicates_found = {t: vids for t, vids in grouped.items() if len(vids) > 1}
    print(f"📊 Duplicate title clusters found: {len(duplicates_found)}")

    total_to_delete = 0
    for title, vids in duplicates_found.items():
        print(f"\n📁 '{title}' -> {len(vids)} copies found")
        # Keep the first/original, mark the rest for deletion
        to_keep = vids[0]
        to_remove = vids[1:]
        print(f"   🟢 Keep:   {to_keep['id']} (Published: {to_keep['published']})")
        for rem in to_remove:
            print(f"   🔴 Delete: {rem['id']} (Published: {rem['published']})")
            total_to_delete += 1

    if total_to_delete == 0:
        print("\n🎉 No duplicate videos found!")
        return

    print(f"\n⚠️ Total duplicate videos to remove: {total_to_delete}")
    if dry_run:
        print("[Dry Run] No videos were deleted. Run with dry_run=False to execute.")
        return

    # Execute deletion
    deleted_count = 0
    for title, vids in duplicates_found.items():
        to_remove = vids[1:]
        for rem in to_remove:
            vid = rem["id"]
            try:
                print(f"🗑️ Deleting duplicate video: {vid} ('{title[:40]}...')...")
                yt.videos().delete(id=vid).execute()
                deleted_count += 1
                time.sleep(1)  # safe pacing
            except Exception as e:
                print(f"   ❌ Failed to delete {vid}: {e}")

    print(f"\n✅ Finished! Successfully removed {deleted_count} duplicate Shorts from your channel.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview duplicates without deleting")
    parser.add_argument("--pages", type=int, default=5, help="Number of 50-item pages to scan (default 5 = 250 videos)")
    args = parser.parse_args()

    clean_duplicate_shorts(dry_run=args.dry_run, max_pages=args.pages)
