"""CLI entry point.

Usage:
    python main.py "https://www.youtube.com/watch?v=..." \
        --num-clips 3 --aspect-ratio 9:16
"""
import argparse
import json
import sys

# Windows uses 'charmap' by default, which can't encode Unicode characters
# like →. Reconfigure stdout/stderr to UTF-8 so output works on all platforms.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from shorts_generator import generate_shorts


def main() -> int:
    parser = argparse.ArgumentParser(description="AI YouTube Shorts Generator")
    parser.add_argument("url", nargs="?", default=None, help="YouTube URL, file:// URL, or local file path (optional: if omitted, picks a viral video automatically)")
    parser.add_argument(
        "--mode",
        choices=["api", "local"],
        default="local",
        help="local (default, Whisper + Gemini + OpenCV) or api (MuAPI).",
    )
    parser.add_argument("--num-clips", type=int, default=5, help="How many shorts to render (default: 5)")
    parser.add_argument("--aspect-ratio", default="9:16", help="Output aspect ratio (default: 9:16)")
    parser.add_argument("--format", default="1080", help="Source download resolution (default: 1080)")
    parser.add_argument("--language", default=None, help="Force Whisper language code, e.g. 'en' (default: auto-detect)")
    parser.add_argument("--privacy", choices=["public", "unlisted", "private"], default="public", help="Upload visibility (default: public)")
    parser.add_argument("--output-json", default=None, help="Write the full result JSON to this path")
    args = parser.parse_args()

    # If no URL is provided, run the autonomous pipeline on a viral topic automatically!
    if not args.url:
        from daily_runner import pick_viral_topic
        from pipeline import run_pipeline
        topic = pick_viral_topic()
        print("\n" + "=" * 70)
        print("      BYTEWAVE AI: AUTONOMOUS VIRAL SHORTS GENERATOR")
        print("=" * 70)
        print(f"🎯 Auto-Selected Viral Topic: '{topic}'")
        print(f"🎬 Generating: {args.num_clips} Shorts (Vertical 9:16)")
        print(f"🔒 Privacy: {args.privacy}")
        print("=" * 70 + "\n")
        run_pipeline(
            search_topic=topic,
            num_clips=args.num_clips,
            mode=args.mode,
            privacy_status=args.privacy,
            min_duration=300,
            max_duration=1800,
        )
        return 0

    try:
        result = generate_shorts(
            youtube_url=args.url,
            num_clips=args.num_clips,
            aspect_ratio=args.aspect_ratio,
            download_format=args.format,
            language=args.language,
            mode=args.mode,
        )
    except Exception as e:
        print(f"\nFAILED: {e}", file=sys.stderr)
        return 1

    print("\n" + "=" * 72)
    print(f"Mode:          {result.get('mode', args.mode)}")
    print(f"Source video:  {result['source_video_url']}")
    print(f"Highlights:    {len(result['highlights'])} candidates → kept top {len(result['shorts'])}")
    print("=" * 72)
    for i, s in enumerate(result["shorts"], 1):
        print(f"\n#{i}  score={s.get('score')}  {s.get('start_time'):.1f}s → {s.get('end_time'):.1f}s")
        print(f"     title:  {s.get('title')}")
        print(f"     hook:   {s.get('hook_sentence')}")
        if s.get("clip_url"):
            print(f"     clip:   {s['clip_url']}")
        else:
            print(f"     clip:   FAILED ({s.get('error')})")

    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nFull JSON written to {args.output_json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
