"""Daily Automation Scheduler:
Loads from a massive viral_topics.json database (100+ viral queries) + Gemini AI dynamic queries.
Produces 4-5 viral shorts daily, uploads them to your channel, and cleans 100% of video storage.
"""
import os
import json
import random
import time
import argparse
from pipeline import run_pipeline, pick_channel_informed_topic
from pipeline.news_scanner import discover_news_informed_query
from dotenv import load_dotenv

load_dotenv()

TOPICS_FILE = os.path.join("data", "viral_topics.json") if os.path.exists("data") else "viral_topics.json"


def load_all_topics() -> list:
    """Load keywords exclusively from viral_topics.json (320+ creator-free keywords)."""
    if os.path.exists(TOPICS_FILE):
        try:
            with open(TOPICS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                kws = data.get("keywords") or data.get("topics") or []
                if kws:
                    return kws
        except Exception as e:
            print(f"[Warning] Could not read {TOPICS_FILE}: {e}")
            
    # Minimal fallback only if file is missing
    return [
        "bgmi 1v4 clutch", "bgmi new update", "bgmi shayari montage",
        "future tech 2026", "gta 6 gameplay leak", "ai revolution 2026",
        "humanoid robot demonstration", "james webb telescope mystery"
    ]


def fetch_live_trending_topic() -> str:
    """Fetch real-time live search queries directly from YouTube's auto-complete engine
    using random seed keywords chosen dynamically from viral_topics.json.
    """
    import urllib.request
    import urllib.parse
    
    all_kws = load_all_topics()
    sample_seeds = random.sample(all_kws, min(len(all_kws), 8))
    
    for seed in sample_seeds:
        try:
            url = f"https://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={urllib.parse.quote(seed + ' ')}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if len(data) > 1 and isinstance(data[1], list) and data[1]:
                    live_candidates = [q for q in data[1] if len(q) > 6]
                    if live_candidates:
                        chosen = random.choice(live_candidates[:5])
                        print(f" -> [Live Trend Scanner] Real-time YouTube search trend discovered: '{chosen}'")
                        return chosen
        except Exception:
            continue
    return ""


def pick_viral_topic() -> str:
    """Dynamically picks or discovers viral search keywords for YouTube.
    
    Combines:
    1. Real-time Breaking Geopolitical & India Future News Scanner (highest priority)
    2. Channel Intelligence Scanner (learns from your most viewed & liked videos)
    3. Real-time Live YouTube Search Trend Scanners (from dynamic seeds)
    4. Dynamic AI Generation with Gemini (creative viral angles)
    5. Direct selection from viral_topics.json (460+ pure keywords)
    """
    # 1. 40% priority: Real-time Breaking Indian Geopolitics, Defence Deals & Future Tech News
    if random.random() < 0.40:
        try:
            news_query = discover_news_informed_query()
            if news_query:
                return news_query
        except Exception as e:
            print(f" -> [News Scanner Note]: {e}")

    # 2. 30% chance: Model after your channel's top performing videos (most views & likes)
    if random.random() < 0.35:
        try:
            channel_topic = pick_channel_informed_topic()
            if channel_topic:
                return channel_topic
        except Exception as e:
            print(f" -> [Channel Scanner Note]: {e}")

    # 2. 30% chance: Discover live trending YouTube search queries happening right now
    if random.random() < 0.50:
        live_query = fetch_live_trending_topic()
        if live_query:
            return live_query

    # 3. Dynamic AI Generation with Gemini (creative viral angles)
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and random.random() < 0.50:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            angle = random.choice([
                "future tech breakthroughs, technological singularity, or future technology 2026",
                "humanoid robots, tesla optimus, boston dynamics atlas, or autonomous robotics",
                "artificial intelligence breakthroughs, deepseek vs openai, or autonomous ai agents",
                "quantum computing breakthroughs, quantum supremacy, or superconductor physics",
                "neuralink brain chip, brain computer interfaces, or bionic cybernetics",
                "shocking space discoveries, james webb telescope, black holes, or cosmic mysteries",
                "universe physics, multiverse theory, dark matter, or time travel paradoxes",
                "spacex starship mars mission, isro space missions, or deep space exploration",
                "next-gen game engine engineering, unreal engine 5 graphics tech, or ray tracing physics",
                "future of cryptocurrency and blockchain technology, how governments try to block or regulate crypto, decentralization vs CBDC, and zero knowledge cryptography",
                "crypto security, quantum computing threats to blockchain, self-custody cold wallets, and AI autonomous cryptocurrency economy"
            ])
            prompt = (
                f"Give 1 short 2 to 4 word YouTube search keyword to find trending videos about: {angle}.\n"
                f"Do not write sentences. Do not use individual cryptocurrency shilling names or meme coin hype; focus on broad concepts like 'future of crypto', 'crypto regulation', 'blockchain technology', 'cbdc privacy', 'smart contracts', 'zero knowledge proofs'.\n"
                f"Output ONLY the short keyword phrase, nothing else."
            )
            resp = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
                contents=prompt
            )
            query = resp.text.strip().replace('"', '').replace("'", "")
            if query and 3 < len(query) < 50:
                print(f" -> [AI Trend Engine] Dynamically generated viral keyword: '{query}'")
                return query
        except Exception:
            pass

    # 3. Pick directly from the 320+ creator-free keywords pool in viral_topics.json
    keywords = load_all_topics()
    return random.choice(keywords)


def run_continuous_autopilot(
    num_shorts: int = 5,
    privacy: str = "public",
    delay_seconds: int = 30,
    max_cycles: int = 0,
):
    """Runs continuous autopilot indefinitely:
    1. Picks viral topic guided by channel success intelligence & live search trends
    2. Downloads 720p HD video (5-30 mins)
    3. Generates 5 high-hook vertical 9:16 Shorts with animated subtitles & thumbnails
    4. Uploads all 5 Shorts to YouTube with dynamic tags & pinned engagement comments
    5. Cleans 100% of temporary disk storage
    6. Waits cooldown and immediately begins the next cycle continuously until stopped (Ctrl+C).
    """
    cycle = 1
    num_shorts = max(1, num_shorts)
    
    print("\n" + "=" * 70)
    print("      BYTEWAVE AI: CONTINUOUS 24/7 AUTOPILOT ACTIVATED")
    if max_cycles > 0:
        print(f"  Target Run Limit: {max_cycles} cycle(s) ({max_cycles * num_shorts} Shorts total)")
    else:
        print("  Runs indefinitely until stopped (Press Ctrl+C anytime to stop)")
    print(f"  Per Cycle: 1 Downloaded Video → {num_shorts} Shorts (at 720p HD)")
    print(f"  Cooldown between cycles: {delay_seconds} seconds")
    print(f"  Privacy: {privacy}")
    print("=" * 70)

    while True:
        try:
            query = pick_viral_topic()
            print(f"\n🚀 [Cycle #{cycle}{f' of {max_cycles}' if max_cycles > 0 else ''}] Starting Topic: '{query}'")
            print(f"🎯 Target: {num_shorts} Shorts (720p HD)")
            
            run_pipeline(
                search_topic=query,
                num_clips=num_shorts,
                mode="local",
                privacy_status=privacy,
                min_duration=300,   # 5 minutes
                max_duration=1800,  # 30 minutes
            )

            print(f"\n✅ [Cycle #{cycle} Complete] 1 Video processed → {num_shorts} Shorts generated & uploaded! Local storage 100% cleaned.")

            if max_cycles > 0 and cycle >= max_cycles:
                print("\n" + "=" * 70)
                print(f"🎉 Completed all {cycle} cycle(s) ({cycle * num_shorts} Shorts total)!")
                print("=" * 70 + "\n")
                break

            print(f"⏳ Cooldown: Waiting {delay_seconds} seconds before starting the next video...")
            for remaining in range(delay_seconds, 0, -5):
                print(f" -> Next cycle starts in {remaining}s... (Press Ctrl+C to stop)")
                time.sleep(min(5, remaining))

            cycle += 1

        except KeyboardInterrupt:
            print("\n\n🛑 [Stopped by User] Autopilot safely paused. All local files cleaned.")
            break
        except Exception as e:
            err_msg = str(e)
            print(f"\n[Warning] Cycle encountered an issue: {err_msg}")
            if "upload quota exceeded" in err_msg.lower() or "uploadlimitexceeded" in err_msg.lower():
                print("\n💤 YouTube daily upload limit reached (10,000 units/day).")
                print("Sleeping for 1 hour before checking if quota has reset. (Press Ctrl+C to stop)...")
                time.sleep(3600)
            else:
                print(f"Retrying next topic in {delay_seconds} seconds...")
                time.sleep(delay_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Dynamic Continuous YouTube Shorts Automation")
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of shorts to make per video (default: 5)",
    )
    parser.add_argument(
        "--privacy",
        choices=["public", "unlisted", "private"],
        default="public",
        help="Upload privacy (default: public)",
    )
    parser.add_argument(
        "--cooldown",
        type=int,
        default=30,
        help="Cooldown seconds between cycles (default: 30)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional: stop after N cycles (default: 0 = continuous non-stop loop)",
    )
    args = parser.parse_args()

    run_continuous_autopilot(
        num_shorts=args.count,
        privacy=args.privacy,
        delay_seconds=args.cooldown,
        max_cycles=args.limit,
    )
