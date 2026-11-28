"""Live Geopolitical & India Future News Scanner.

Scrapes real-time breaking news from top verified sources:
  - Google News (India Geopolitics, Defence, Global Deals, ISRO & Future Tech)
  - Live RSS Feeds

Uses Gemini AI to convert breaking geopolitical & future tech developments
into high-CTR, viral YouTube search queries to discover fresh podcast & analysis videos
(TRS Hindi, StudyIQ, Think School, Nitish Rajput, World Affairs style).
"""
import os
import re
import json
import random
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from typing import List

from dotenv import load_dotenv

load_dotenv()

# Real-time RSS feeds covering Indian Geopolitics, Defence Deals, Global Trade & Future Tech
NEWS_FEEDS = [
    # India Geopolitics & Global Deals
    "https://news.google.com/rss/search?q=India+geopolitics+OR+foreign+policy+OR+defence+deal&hl=en-IN&gl=IN&ceid=IN:en",
    # India Future Tech & Strategic Capabilities
    "https://news.google.com/rss/search?q=ISRO+OR+India+semiconductor+OR+India+AI+OR+quantum&hl=en-IN&gl=IN&ceid=IN:en",
    # Global Conflict & World Affairs impacting India
    "https://news.google.com/rss/search?q=India+trade+corridor+OR+BRICS+OR+dollar+crisis&hl=en-IN&gl=IN&ceid=IN:en",
    # Indian Defence, Border & Maritime Strategy
    "https://news.google.com/rss/search?q=Indian+Ocean+strategy+OR+Indian+Navy+OR+IAF+jets&hl=en-IN&gl=IN&ceid=IN:en",
]


def fetch_live_geopolitics_headlines(max_headlines: int = 12) -> List[str]:
    """Fetch live real-time breaking geopolitical & strategic news headlines."""
    headlines = []
    seen = set()

    for url in NEWS_FEEDS:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                root = ET.fromstring(resp.read())
                for item in root.findall(".//item"):
                    title_elem = item.find("title")
                    if title_elem is not None and title_elem.text:
                        clean_title = re.sub(r"\s*-\s*[^-]+$", "", title_elem.text).strip()
                        if clean_title.lower() not in seen and len(clean_title) > 20:
                            seen.add(clean_title.lower())
                            headlines.append(clean_title)
                            if len(headlines) >= max_headlines:
                                break
        except Exception:
            continue

    return headlines


def discover_news_informed_query() -> str:
    """Discovers a live YouTube search query based on what is happening RIGHT NOW
    in Indian geopolitics, future tech, defence deals, or world trade.
    """
    headlines = fetch_live_geopolitics_headlines(max_headlines=10)
    if not headlines:
        return ""

    sample_news = random.sample(headlines, min(len(headlines), 4))
    print(f"\n🌍 [Geopolitics News Radar] Scanned real-time headlines:")
    for h in sample_news:
        print(f"    • {h}")

    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            
            prompt = (
                "You are an expert Indian YouTube viral strategist (specializing in TRS Hindi, Think School, Nitish Rajput, StudyIQ, World Affairs).\n"
                "Here are real-time breaking news headlines regarding India's geopolitics, defence deals, global trade, and future tech:\n"
                f"{chr(10).join(f'- {h}' for h in sample_news)}\n\n"
                "TASK:\n"
                "Pick the single most explosive, controversial, or shocking story from these headlines.\n"
                "Convert it into 1 high-CTR YouTube search query (3 to 6 words) to find deep analysis videos or podcasts.\n"
                "Do not write full sentences or clickbait words like 'Shocking' or quotes.\n"
                "Examples: 'India Middle East Europe Corridor geopolitics' or 'India semiconductor manufacturing future' or 'India stealth fighter jet deal analysis'.\n"
                "Output ONLY the 3-6 word search query, nothing else."
            )
            resp = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
                contents=prompt
            )
            query = resp.text.strip().replace('"', '').replace("'", "")
            if query and 5 < len(query) < 60:
                print(f" -> [Geopolitics News Radar] Converted breaking news into search query: '{query}'")
                return query
        except Exception as e:
            print(f" -> [Geopolitics News Radar] AI note: {e}")

    # Fallback if Gemini is busy
    headline = sample_news[0]
    words = [w for w in headline.split() if len(w) > 3][:5]
    fallback_query = " ".join(words) + " analysis"
    return fallback_query
