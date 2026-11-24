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
    1. Channel Intelligence Scanner (learns from your most viewed & liked videos)
    2. Real-time Live YouTube Search Trend Scanners (from dynamic seeds)
    3. Dynamic AI Generation with Gemini (creative viral angles)
    4. Direct selection from viral_topics.json (320+ pure keywords)
    """
    # 1. 40% chance: Model after your channel's top performing videos (most views & likes)
    if random.random() < 0.40:
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
                "next-gen game engine engineering, unreal engine 5 graphics tech, or ray tracing physics"
            ])
            prompt = (
                f"Give 1 short 2 to 4 word YouTube search keyword to find trending videos about: {angle}.\n"
                f"Do not write sentences. Do not use names of any individual YouTubers, gamers, or creators.\n"
                f"Example format: 'bgmi 1v4 clutch' or 'future tech' or 'gta 6 gameplay'.\n"
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


def run_daily_autopilot(
    max_cycles: int = 1,
    num_shorts: int = 4,
    privacy: str = "public",
    delay_seconds: int = 30,
):
    """Runs the daily viral video automation with safety limits:
    1. Downloads high-res 720p+ candidate video based on channel success intelligence
    2. Extracts high-hook 9:16 vertical Shorts with animated subtitles
    3. Uploads to YouTube with dynamic tags and pinned engagement questions
    4. Automatically cleans 100% of temporary files from local disk
    5. After completing the designated daily limit (default: 1 cycle / batch of shorts),
       safely stops automatically so your channel isn't throttled.
    """
    cycle = 1
    num_shorts = max(1, num_shorts)
    
    print("\n" + "=" * 70)
    print("      BYTEWAVE AI: DAILY AUTOMATION RUNNER")
    if max_cycles > 0:
        print(f"  Target Run Limit: {max_cycles} cycle(s) (1 cycle = ~{num_shorts} Shorts)")
        print("  Bot will stop automatically once the target limit is reached.")
    else:
        print("  Mode: Continuous Loop (Ctrl+C to stop)")
    print(f"  Shorts Per Cycle: {num_shorts} Shorts (720p HD)")
    print(f"  Privacy: {privacy}")
    print("=" * 70)

    while True:
        try:
            query = pick_viral_topic()
            print(f"\n🚀 [Daily Cycle #{cycle}{f' of {max_cycles}' if max_cycles > 0 else ''}] Starting Topic: '{query}'")
            print(f"🎯 Target: {num_shorts} Shorts (720p HD)")
            
            run_pipeline(
                search_topic=query,
                num_clips=num_shorts,
                mode="local",
                privacy_status=privacy,
                min_duration=300,   # 5 minutes
                max_duration=1800,  # 30 minutes
            )

            print(f"\n✅ [Cycle #{cycle} Complete] Uploaded successfully & local storage 100% cleaned!")

            # Check if daily limit reached
            if max_cycles > 0 and cycle >= max_cycles:
                print("\n" + "=" * 70)
                print(f"🎉 [DAILY GOAL COMPLETED] Finished {cycle} cycle(s) with {num_shorts} shorts!")
                print("🛑 Daily limit reached. Stopping automatically to protect algorithm health.")
                print("=" * 70 + "\n")
                break

            print(f"⏳ Cooldown: Waiting {delay_seconds} seconds before starting the next video...")
            for remaining in range(delay_seconds, 0, -5):
                print(f" -> Next video starts in {remaining}s... (Press Ctrl+C to stop)")
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
                print("Stopping bot for today so quota can reset.")
                break
            else:
                print(f"Retrying next topic in {delay_seconds} seconds...")
                time.sleep(delay_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Smart YouTube Shorts Daily Automation")
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="How many video cycles to run before stopping automatically (default: 1 cycle = 4 shorts; set 0 for infinite loop)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=4,
        help="Number of shorts to make per cycle (default: 4 shorts)",
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
    args = parser.parse_args()

    run_daily_autopilot(
        max_cycles=args.limit,
        num_shorts=args.count,
        privacy=args.privacy,
        delay_seconds=args.cooldown,
    )
