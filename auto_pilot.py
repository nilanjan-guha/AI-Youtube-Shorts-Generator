"""Complete Autonomous YouTube Shorts Pipeline:
1. Search YouTube for videos matching a query/topic with 10-15 minute duration.
2. Download candidate video temporarily.
3. Generate top 3-4 vertical 9:16 Shorts (using Gemini/MuAPI + Whisper + FFmpeg).
4. Upload generated Shorts to your YouTube Channel.
5. Auto-delete all downloaded source videos and rendered clips to free up 100% memory/disk.
"""
import os
import sys
import shutil
import glob
import time
import argparse
from typing import List, Dict, Optional

# Ensure UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import yt_dlp
from shorts_generator import generate_shorts
from youtube_uploader import get_authenticated_service, upload_video, set_thumbnail, post_pinned_comment, generate_engagement_comment


HISTORY_FILE = "history.json"


def get_used_video_ids() -> set:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                import json
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_used_video_id(video_id: str):
    used = get_used_video_ids()
    used.add(video_id)
    with open(HISTORY_FILE, "w") as f:
        import json
        json.dump(list(used), f, indent=2)


# Guaranteed fallback queries when primary search returns zero results
_FALLBACK_QUERIES = [
    "ranveer allahbadia podcast hindi latest",
    "prakhar ke pravachan latest episode",
    "dhruv rathee analysis latest",
    "ISRO space mission latest update hindi",
    "artificial intelligence future explained hindi",
    "Raj Shamani podcast motivational",
    "TRS Hindi podcast latest",
    "facttechz amazing facts hindi",
    "getsetfly science latest",
    "think school business case study",
    "nitish rajput geopolitics latest",
    "Dostcast podcast latest",
    "sandeep maheshwari latest motivational",
    "Elon Musk AI robotics latest interview",
    "Sam Altman OpenAI future interview",
    "black hole mystery James Webb",
    "quantum computing explained future",
]


def search_youtube_videos(query: str, max_results: int = 10, min_duration: int = 240, max_duration: int = 2100, _depth: int = 0) -> List[Dict]:
    """Search YouTube and discover related recommended videos (4 to 35 mins) that haven't been used before.
    
    3-tier fallback system:
      1. Primary search for the exact query
      2. Broadened search with 'podcast hindi' appended
      3. Guaranteed fallback from a curated list of always-available channels
    """
    print(f"\n[Search] Searching YouTube & related recommendations for '{query}' ({min_duration//60}-{max_duration//60} mins)...")
    used_ids = get_used_video_ids()
    
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "search_sort": "upload_date",
        "skip_download": True,
    }
    
    found_videos = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"ytsearch{max_results * 10}:{query}", download=False)
            entries = result.get("entries", []) if result else []
            
            for entry in entries:
                vid = entry.get("id")
                if not vid or vid in used_ids:
                    continue
                
                # In extract_flat mode, duration and view_count are already extracted instantly!
                duration = entry.get("duration")
                view_count = int(entry.get("view_count") or 0)
                title = entry.get("title") or "Viral Video"
                
                # If flat extract didn't get duration, fetch with flat detail
                if not duration:
                    try:
                        detail = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
                        duration = detail.get("duration")
                        view_count = int(detail.get("view_count") or view_count)
                        title = detail.get("title") or title
                    except Exception:
                        continue
                
                if duration and min_duration <= duration <= max_duration:
                    print(f" -> Found match: [{duration//60}m {duration%60}s | {view_count:,} views] {title[:55]}...")
                    found_videos.append({
                        "id": vid,
                        "title": title,
                        "duration": duration,
                        "view_count": view_count,
                        "url": f"https://www.youtube.com/watch?v={vid}",
                    })
                    if len(found_videos) >= max_results * 2:
                        break
    except Exception as e:
        print(f" -> Search error: {e}")

    # TIER 2: Broaden the query with 'podcast hindi'
    if not found_videos and _depth == 0 and "podcast" not in query.lower():
        print(f" -> No results for '{query}'. Tier 2: broadening search...")
        return search_youtube_videos(f"{query} podcast hindi", max_results=max_results,
                                      min_duration=min_duration, max_duration=max_duration, _depth=1)

    # TIER 3: Guaranteed fallback — pick a random query from curated always-popular channels
    if not found_videos and _depth <= 1:
        import random
        fallback_q = random.choice(_FALLBACK_QUERIES)
        print(f" -> Tier 3 guaranteed fallback: '{fallback_q}'")
        return search_youtube_videos(fallback_q, max_results=max_results,
                                      min_duration=min_duration, max_duration=max_duration, _depth=2)
                    
    # Sort candidates by view count in descending order to guarantee highest viral potential
    found_videos.sort(key=lambda x: x.get("view_count", 0), reverse=True)
    return found_videos[:max_results]


def generate_video_thumbnail(video_path: str, title: str, out_thumb_path: str) -> Optional[str]:
    """Capture a high-energy frame from the video and format it as a high-CTR thumbnail."""
    try:
        import cv2
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        # Pick a frame around 20-30% in (past intro, into high-energy content)
        target_frame = max(1, int(total_frames * 0.25))
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        cap.release()

        if ret and frame is not None:
            cv2.imwrite(out_thumb_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            return out_thumb_path
    except Exception as e:
        print(f" -> Thumbnail generation error: {e}")
    return None


def cleanup_storage(source_paths: List[str], clips: List[Dict], thumbnails: Optional[List[str]] = None, output_dir: str = "output"):
    """Delete all downloaded long source videos, generated short clips, and temporary thumbnails."""
    print("\n[Cleanup] Deleting temporary video & thumbnail data to free disk and memory...")
    
    # Delete thumbnail files
    thumbnails = thumbnails or []
    for th in thumbnails:
        if th and os.path.exists(th):
            try:
                os.remove(th)
                print(f" -> Deleted thumbnail: {th}")
            except Exception:
                pass
    
    # Delete source files
    for sp in source_paths:
        if sp and os.path.exists(sp):
            try:
                os.remove(sp)
                print(f" -> Deleted source video: {sp}")
            except Exception as e:
                print(f" -> Could not delete {sp}: {e}")

    # Delete clip files
    for clip in clips:
        clip_path = clip.get("clip_url")
        if clip_path and os.path.exists(clip_path):
            try:
                os.remove(clip_path)
                print(f" -> Deleted generated short: {clip_path}")
            except Exception as e:
                print(f" -> Could not delete {clip_path}: {e}")

    # Also clean any leftover temporary subclips/artifacts in output folder
    if os.path.exists(output_dir):
        for pattern in ["subclip_*.mp4", "source_*.*", "clip_*.mp4"]:
            for f in glob.glob(os.path.join(output_dir, pattern)):
                try:
                    os.remove(f)
                    print(f" -> Cleaned temporary artifact: {f}")
                except Exception:
                    pass
    print("[Cleanup] Done. All video storage reclaimed.")


def fetch_trending_search_queries(seed_text: str, max_results: int = 8) -> List[str]:
    """Fetch live real-time YouTube search suggestions directly from YouTube's auto-complete engine.
    
    Returns high-traffic search phrases that real users are actively typing into YouTube right now.
    """
    import urllib.request
    import urllib.parse
    import json as json_lib

    clean = " ".join([w for w in seed_text.replace("#", "").split() if len(w) > 2][:4])
    if not clean:
        return []

    suggestions: List[str] = []
    try:
        url = f"https://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={urllib.parse.quote(clean)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json_lib.loads(resp.read().decode("utf-8"))
            if len(data) > 1 and isinstance(data[1], list):
                suggestions = [str(s) for s in data[1][:max_results]]
    except Exception:
        pass
    return suggestions


def generate_dynamic_metadata(content_text: str, original_title: str, is_short: bool = True) -> Dict:
    """Dynamically generate high-CTR viral title, tags, and description using Gemini AI,
    real-time YouTube Search Auto-Complete Trends, and High-Traffic Question Hooks.
    
    Combines:
    1. Real-time YouTube live search query data (what users are actively typing)
    2. High-traffic question formats ("Why...", "How...", "What happens if...")
    3. Gemini AI SEO optimization tailored to the video's actual speech
    """
    is_hindi = any('\u0900' <= char <= '\u097f' for char in (content_text + original_title))
    
    # 1. Fetch live YouTube search suggestions for this topic
    live_trending_searches = fetch_trending_search_queries(original_title or content_text)
    if not live_trending_searches:
        live_trending_searches = fetch_trending_search_queries(content_text[:60])
    
    trending_context = ", ".join(f"'{s}'" for s in live_trending_searches[:5]) if live_trending_searches else "None"
    print(f" -> [SEO Engine] Live YouTube search trends detected: {trending_context}")

    # Try querying Gemini AI for tailored viral metadata
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            from google import genai
            import json as json_lib
            client = genai.Client(api_key=api_key)
            prompt = (
                f"You are a top YouTube Shorts SEO growth strategist.\n"
                f"Goal: Generate a high-CTR, algorithm-favored viral title and SEO metadata.\n\n"
                f"Video Context / Hook: {content_text[:600]}\n"
                f"Original Title: {original_title}\n"
                f"Is Short format: {is_short}\n"
                f"Language: {'Hindi/Hinglish' if is_hindi else 'English'}\n"
                f"Real-Time YouTube Search Suggestions (Active high-traffic queries): {trending_context}\n\n"
                f"INSTRUCTIONS FOR TITLE & KEYWORDS:\n"
                f"1. Use a high-curiosity QUESTION or shocking search-friendly phrasing that people actively search for (e.g. 'Can AI Do This?', 'Why Neuralink Shocked Everyone?', 'Sach Me Aisa Hua?').\n"
                f"2. Incorporate the strongest live search suggestion into the title or tags naturally.\n"
                f"3. Keep title under 70 characters so it fits on mobile Shorts screens without being cut off.\n\n"
                f"Return ONLY valid JSON matching this schema:\n"
                f"{{\n"
                f'  "title": "High-CTR search-optimized question or hook under 70 chars",\n'
                f'  "tags": ["8-12 high-search-volume keywords including live trends"],\n'
                f'  "hashtags": ["#5-8 relevant hashtags"],\n'
                f'  "description": "Engaging 2-sentence summary answering the title curiosity",\n'
                f'  "debate_question": "Controversial question prompting viewers to comment Yes or No"\n'
                f"}}"
            )
            models_to_try = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-flash-lite-latest", os.getenv("GEMINI_MODEL", "gemini-3.5-flash")]
            resp = None
            for m in list(dict.fromkeys(models_to_try)):
                try:
                    resp = client.models.generate_content(
                        model=m,
                        contents=prompt,
                        config={"response_mime_type": "application/json"}
                    )
                    if resp and resp.text:
                        break
                except Exception:
                    continue
            if not resp or not resp.text:
                raise RuntimeError("All flash-lite models busy")
            data = json_lib.loads(resp.text)
            
            title = data.get("title", original_title)
            tags = data.get("tags", [])
            ai_hashtags = data.get("hashtags", [])
            desc_text = data.get("description", original_title)
            debate_q = data.get("debate_question") or "What do you think about this? Drop your thoughts below! 👇"
            
            # Universal top-trending viral tags & hashtags for Shorts algorithm
            core_viral_hashtags = [
                "#Shorts", "#YouTubeShorts", "#Viral", "#ViralShorts",
                "#Trending", "#TrendingShorts", "#FYP", "#ForYou"
            ]
            
            # Niche-specific viral hashtags based on content
            content_lower = (content_text + " " + original_title).lower()
            niche_hashtags = []
            if any(k in content_lower for k in ["bgmi", "pubg", "jonathan", "mortal", "scout", "dynamo", "clutch", "shayari"]):
                niche_hashtags.extend(["#BGMI", "#BGMIShorts", "#BGMIShayari", "#JonathanGaming", "#Mortal", "#Scout", "#DynamoGaming", "#BGMIClutch", "#PUBGIndia"])
            if any(k in content_lower for k in ["gta", "gta 6", "rockstar", "game", "gaming", "vice city"]):
                niche_hashtags.extend(["#GTA6", "#GTA6Trailer", "#GTA6Gameplay", "#GamingShorts", "#RockstarGames", "#ViceCity"])
            if any(k in content_lower for k in ["ai", "artificial intelligence", "robot", "robotics", "tech", "coding"]):
                niche_hashtags.extend(["#AI", "#ArtificialIntelligence", "#TechShorts", "#FutureTech", "#HumanoidRobot", "#TechNews"])
            if any(k in content_lower for k in ["isro", "space", "nasa", "black hole", "universe", "moon"]):
                niche_hashtags.extend(["#Space", "#ISRO", "#NASA", "#BlackHole", "#Astronomy", "#ScienceFacts"])
            if is_hindi:
                niche_hashtags.extend(["#Hindi", "#ShortsHindi", "#HindiFacts", "#DesiTech"])

            # Clean and combine all hashtags ensuring no duplicates
            all_raw = core_viral_hashtags + niche_hashtags + [h if h.startswith("#") else f"#{h}" for h in ai_hashtags]
            clean_hashtags = []
            seen = set()
            for h in all_raw:
                formatted = "#" + h.lstrip("#").replace(" ", "")
                if formatted.lower() not in seen and len(formatted) > 2:
                    seen.add(formatted.lower())
                    clean_hashtags.append(formatted)

            # Blend in live YouTube trending searches into the tags
            combined_tags = list(dict.fromkeys(tags + live_trending_searches + ["Shorts", "Viral", "Trending", "YouTube Shorts"]))[:18]
            
            if is_short and "#shorts" not in title.lower():
                title = f"{title[:72]} #Shorts"
            elif not is_short and "| Full Episode" not in title:
                title = f"{title[:80]} | Full Episode"

            full_desc = (
                f"{desc_text}\n\n"
                f"🔥 QUESTION FOR YOU:\n"
                f"{debate_q}\n"
                f"Drop your answer in the comments below! 👇\n\n"
                f"🔍 Trending Topics Covered: {', '.join(live_trending_searches[:4])}\n\n"
                f"🚨 Subscribe to @ByteWaveAI for daily future breakthroughs, AI & gaming updates! 🚀\n\n"
                f"{' '.join(clean_hashtags[:18])}"
            )
            return {
                "title": title[:95],
                "tags": combined_tags,
                "description": full_desc,
            }
        except Exception as e:
            print(f" -> [SEO Engine] AI metadata note: {e}")

    # Dynamic fallback: Extract meaningful keywords directly from content
    words = [w.strip(" ,.-!?|()[]{}#\"':;") for w in content_text.split() if len(w) > 3]
    stopwords = {"this", "that", "with", "from", "have", "what", "when", "where", "your", "they", "will", "about", "there", "their", "video", "shorts"}
    meaningful = [w for w in words if w.lower() not in stopwords]
    unique_words = list(dict.fromkeys(meaningful))

    content_lower = (content_text + " " + original_title).lower()
    
    # Core viral hashtags for Shorts algorithm
    core_viral_hashtags = [
        "#Shorts", "#YouTubeShorts", "#Viral", "#ViralShorts",
        "#Trending", "#TrendingShorts", "#FYP", "#ForYou"
    ]
    
    # Niche hashtags
    niche_hashtags = []
    if any(k in content_lower for k in ["bgmi", "pubg", "jonathan", "mortal", "scout", "dynamo", "clutch", "shayari"]):
        niche_hashtags.extend(["#BGMI", "#BGMIShorts", "#BGMIShayari", "#JonathanGaming", "#Mortal", "#Scout", "#DynamoGaming", "#BGMIClutch", "#PUBGIndia"])
    if any(k in content_lower for k in ["gta", "gta 6", "rockstar", "game", "gaming", "vice city"]):
        niche_hashtags.extend(["#GTA6", "#GTA6Trailer", "#GTA6Gameplay", "#GamingShorts", "#RockstarGames", "#ViceCity"])
    if any(k in content_lower for k in ["ai", "artificial intelligence", "robot", "robotics", "tech", "coding"]):
        niche_hashtags.extend(["#AI", "#ArtificialIntelligence", "#TechShorts", "#FutureTech", "#HumanoidRobot", "#TechNews"])
    if any(k in content_lower for k in ["isro", "space", "nasa", "black hole", "universe", "moon"]):
        niche_hashtags.extend(["#Space", "#ISRO", "#NASA", "#BlackHole", "#Astronomy", "#ScienceFacts"])
    if is_hindi:
        niche_hashtags.extend(["#Hindi", "#ShortsHindi", "#HindiFacts", "#DesiTech"])

    # Fallback keyword hashtags
    keyword_hashtags = [f"#{w.capitalize()}" for w in unique_words[:8]]
    all_raw = core_viral_hashtags + niche_hashtags + keyword_hashtags
    clean_hashtags = []
    seen = set()
    for h in all_raw:
        formatted = "#" + h.lstrip("#").replace(" ", "")
        if formatted.lower() not in seen and len(formatted) > 2:
            seen.add(formatted.lower())
            clean_hashtags.append(formatted)

    dynamic_tags = list(dict.fromkeys(["Shorts", "Viral", "Trending", "YouTube Shorts"] + [w.capitalize() for w in unique_words[:10]] + live_trending_searches))[:18]

    clean_title = original_title.strip(" .?!-")
    if is_short:
        final_title = f"{clean_title[:70]} 🤯 #Shorts" if "#shorts" not in clean_title.lower() else clean_title[:85]
    else:
        final_title = f"{clean_title[:78]} | Full Episode"

    full_desc = (
        f"{original_title}\n\n"
        f"🚨 Subscribe to @ByteWaveAI for daily mind-bending breakthroughs & podcasts! 🚀\n"
        f"Drop your comments and perspective below 👇\n\n"
        f"{' '.join(clean_hashtags[:18])}"
    )

    return {
        "title": final_title,
        "tags": dynamic_tags[:18],
        "description": full_desc,
    }


def run_pipeline(
    search_topic: str,
    num_clips: int = 5,
    mode: str = "local",
    privacy_status: str = "private",
    min_duration: int = 300,
    max_duration: int = 1800
):
    print("=" * 70)
    print("      AUTONOMOUS YOUTUBE SHORTS GENERATOR & UPLOADER")
    print("=" * 70)

    # 1. Search for video (10-15 mins)
    videos = search_youtube_videos(search_topic, max_results=1, min_duration=min_duration, max_duration=max_duration)
    if not videos:
        print("[Error] No videos found between 10-15 minutes for this topic. Try broader search terms.")
        return

    chosen_video = videos[0]
    save_used_video_id(chosen_video["id"])
    print(f"\n[Selected Video]: {chosen_video['title']}")
    print(f"URL: {chosen_video['url']} (Length: {chosen_video['duration']//60}m {chosen_video['duration']%60}s)")

    # 2. Generate Shorts
    print(f"\n[Processing] Extracting top {num_clips} Shorts using mode='{mode}' at 720p HD...")
    try:
        result = generate_shorts(
            youtube_url=chosen_video["url"],
            num_clips=num_clips,
            aspect_ratio="9:16",
            download_format="720",
            mode=mode,
        )
    except Exception as e:
        print(f"[Error] Failed to generate shorts: {e}")
        return

    shorts = result.get("shorts", [])
    source_video_path = result.get("source_video_url", "")
    print(f"\n[Success] Generated {len(shorts)} shorts!")

    # 3. Authenticate & Upload
    print("\n[Upload] Connecting to YouTube Channel...")
    youtube = get_authenticated_service()

    created_thumbnails: List[str] = []

    if not youtube:
        print("[Warning] YouTube service authentication not complete. Skipping upload.")
    else:
        # Full long video upload DISABLED to prevent copyright strikes!
        # ONLY 100% transformational 9:16 vertical Shorts are uploaded.

        # Upload all Vertical Shorts only
        for idx, short in enumerate(shorts, 1):
            clip_path = short.get("clip_url")
            if not clip_path or not os.path.exists(clip_path):
                print(f" -> Short #{idx} file not found on disk, skipping.")
                continue

            hook = short.get("hook_sentence") or short.get("title") or chosen_video["title"]
            base_title = short.get("title") or hook
            
            # Generate 100% dynamic viral title, tags, hashtags tailored to this exact short's content
            short_meta = generate_dynamic_metadata(
                content_text=f"{hook} {base_title} {chosen_video['title']}",
                original_title=base_title,
                is_short=True,
            )

            # Generate individual thumbnail for this short
            short_thumb_path = os.path.join("output", f"thumb_short_{idx:02d}.jpg")
            generate_video_thumbnail(clip_path, short_meta["title"], short_thumb_path)
            if os.path.exists(short_thumb_path):
                created_thumbnails.append(short_thumb_path)

            print(f"\n[Upload] Uploading Short #{idx} to YouTube: '{short_meta['title']}'...")
            try:
                video_id = upload_video(
                    youtube,
                    file_path=clip_path,
                    title=short_meta["title"],
                    description=short_meta["description"],
                    tags=short_meta["tags"],
                    privacy_status=privacy_status,
                )
                print(f" -> Upload complete! Video URL: https://youtube.com/shorts/{video_id}")
                
                # Apply custom thumbnail
                if os.path.exists(short_thumb_path):
                    set_thumbnail(youtube, video_id, short_thumb_path)
                
                # Post auto-pinned engagement comment for subscriber conversion
                comment_text = generate_engagement_comment(short_meta["title"], is_short=True)
                post_pinned_comment(youtube, video_id, comment_text, is_short=True)
            except Exception as e:
                err_str = str(e)
                print(f" -> Upload failed: {err_str}")
                # If YouTube 10,000 daily API quota or upload limit reached, stop further attempts in this cycle
                if "quotaExceeded" in err_str or "rateLimitExceeded" in err_str or "uploadLimitExceeded" in err_str:
                    print("\n[Quota Alert] YouTube daily upload quota reached. Further uploads paused until daily quota reset.")
                    raise RuntimeError("YouTube upload quota exceeded for today.")

    # 4. Cleanup all files from disk (videos, clips, and generated thumbnails)
    cleanup_storage([source_video_path], shorts, thumbnails=created_thumbnails)
    print("\n[All Done] Pipeline cycle successfully finished!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous YouTube Shorts Bot")
    parser.add_argument("--query", type=str, default="productivity podcast", help="Search topic to find videos")
    parser.add_argument("--num-clips", type=int, default=3, help="Number of shorts to make per video (3-4)")
    parser.add_argument("--mode", choices=["local", "api"], default="local", help="local (Gemini/Whisper) or api (MuAPI)")
    parser.add_argument("--privacy", choices=["public", "unlisted", "private"], default="private", help="Upload visibility")
    parser.add_argument("--min-min", type=int, default=10, help="Min source video length in minutes (default: 10)")
    parser.add_argument("--max-min", type=int, default=15, help="Max source video length in minutes (default: 15)")

    args = parser.parse_args()

    run_pipeline(
        search_topic=args.query,
        num_clips=args.num_clips,
        mode=args.mode,
        privacy_status=args.privacy,
        min_duration=args.min_min * 60,
        max_duration=args.max_min * 60,
    )
