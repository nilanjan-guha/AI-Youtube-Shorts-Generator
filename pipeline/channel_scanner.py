"""Channel Intelligence Scanner & Adaptive Viral Content Engine.

Scans your channel's most viewed and most liked videos, uses Gemini AI to analyze
why they succeeded (hook style, topic fascination, emotional triggers, framing),
and feeds those proven concepts directly into the topic picker for new Shorts.
"""
import os
import json
import time
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

CACHE_FILE = os.path.join("data", "channel_insights.json") if os.path.exists("data") else "channel_insights.json"
CACHE_TTL_SECONDS = 3600  # Refresh channel insights every 1 hour


def fetch_channel_top_videos(max_videos: int = 50) -> List[Dict]:
    """Fetch recent uploads from the authenticated YouTube channel and sort by views and likes."""
    try:
        from .youtube_uploader import get_authenticated_service
        yt = get_authenticated_service()
        if not yt:
            print("[Channel Intelligence] YouTube API not authenticated, skipping channel scan.")
            return []

        ch_resp = yt.channels().list(part="snippet,contentDetails,statistics", mine=True).execute()
        if not ch_resp.get("items"):
            return []

        channel_item = ch_resp["items"][0]
        channel_name = channel_item["snippet"]["title"]
        uploads_playlist = channel_item["contentDetails"]["relatedPlaylists"]["uploads"]

        # Fetch playlist items
        pl_resp = yt.playlistItems().list(
            playlistId=uploads_playlist,
            part="snippet,contentDetails",
            maxResults=min(max_videos, 50),
        ).execute()

        vid_ids = [
            item["contentDetails"]["videoId"]
            for item in pl_resp.get("items", [])
            if "contentDetails" in item
        ]

        if not vid_ids:
            return []

        vids_resp = yt.videos().list(
            id=",".join(vid_ids),
            part="snippet,statistics,contentDetails",
        ).execute()

        video_list = []
        for v in vids_resp.get("items", []):
            st = v.get("statistics", {})
            video_list.append({
                "id": v["id"],
                "title": v["snippet"]["title"],
                "views": int(st.get("viewCount", 0)),
                "likes": int(st.get("likeCount", 0)),
                "comments": int(st.get("commentCount", 0)),
                "tags": v["snippet"].get("tags", []),
            })

        # Rank by views first, then likes
        video_list.sort(key=lambda x: (x["views"], x["likes"], x["comments"]), reverse=True)
        return video_list

    except Exception as e:
        print(f"[Channel Intelligence] Error fetching channel videos: {e}")
        return []


def analyze_channel_success_factors(top_videos: List[Dict]) -> Dict:
    """Use Gemini AI to diagnose why top videos got the most views and derive reusable viral hooks & topics."""
    if not top_videos:
        return {}

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {}

    # Take top 8-10 performers
    top_performers = top_videos[:10]
    titles_summary = "\n".join([
        f"- '{v['title']}' ({v['views']} views, {v['likes']} likes)"
        for v in top_performers
    ])

    prompt = f"""You are the world's best YouTube Shorts growth strategist and algorithm hacker.
Analyze the top performing videos from this YouTube Shorts channel:

{titles_summary}

Determine WHY these specific videos performed the best compared to others:
1. What core curiosity hooks, existential questions, psychological triggers, or visual promises made viewers click and stay?
2. What specific sub-niches and topics resonated most with this audience? (e.g. mind-bending physics, multiverse, futuristic AI, Unreal Engine, robots, cosmic mysteries)
3. Generate 12 fresh, high-converting search keywords / topics for future Shorts that directly replicate this winning formula.

Respond ONLY in valid JSON format with this exact structure:
{{
  "winning_patterns": "Brief explanation of why these titles got the most views and likes",
  "proven_sub_niches": ["niche 1", "niche 2", "niche 3"],
  "recommended_keywords": [
    "keyword 1",
    "keyword 2",
    "keyword 3",
    "keyword 4",
    "keyword 5",
    "keyword 6",
    "keyword 7",
    "keyword 8",
    "keyword 9",
    "keyword 10",
    "keyword 11",
    "keyword 12"
  ]
}}
"""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        candidate_models = [
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-flash-lite-latest",
            "gemini-3.5-flash",
            os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
        ]
        
        for model_name in candidate_models:
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={
                        "temperature": 0.3,
                        "response_mime_type": "application/json",
                    }
                )
                if resp and resp.text:
                    parsed = json.loads(resp.text)
                    if "recommended_keywords" in parsed:
                        return parsed
            except Exception:
                continue

    except Exception as e:
        print(f"[Channel Intelligence] Error analyzing channel patterns: {e}")

    return {}


def get_channel_viral_insights(force_refresh: bool = False) -> Dict:
    """Get cached or fresh channel intelligence insights."""
    # Check cache
    if not force_refresh and os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                cached_time = data.get("timestamp", 0)
                if time.time() - cached_time < CACHE_TTL_SECONDS:
                    return data
        except Exception:
            pass

    print("\n🔍 [Channel Intelligence Scanner] Scanning your channel's most viewed & liked videos...")
    top_videos = fetch_channel_top_videos(max_videos=50)
    
    if not top_videos:
        return {}

    print(f" -> Found {len(top_videos)} videos. Top performer: '{top_videos[0]['title'][:45]}...' ({top_videos[0]['views']} views, {top_videos[0]['likes']} likes)")
    print(" -> Analyzing viral DNA & viewer psychological triggers with Gemini AI...")
    
    analysis = analyze_channel_success_factors(top_videos)
    
    insights = {
        "timestamp": time.time(),
        "top_videos": top_videos[:10],
        "winning_patterns": analysis.get("winning_patterns", "High curiosity & mind-bending tech/science hooks"),
        "proven_sub_niches": analysis.get("proven_sub_niches", []),
        "recommended_keywords": analysis.get("recommended_keywords", []),
    }

    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(insights, f, indent=2, ensure_ascii=False)
        print(" -> [Channel Intelligence] Successfully cached channel insights & winning keywords!")
    except Exception as e:
        print(f"[Channel Intelligence] Could not write cache: {e}")

    return insights


def pick_channel_informed_topic() -> Optional[str]:
    """Pick a topic specifically modeled after your channel's most viewed and most liked videos."""
    import random
    insights = get_channel_viral_insights(force_refresh=False)
    keywords = insights.get("recommended_keywords", [])
    
    if keywords:
        chosen = random.choice(keywords)
        print(f" -> [Channel Intelligence Scanner] Selected proven winning topic for your audience: '{chosen}'")
        return chosen
    return None
