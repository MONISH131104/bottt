"""
fetcher.py - News from RSS + tweets
Automatically uses:
  - x_login.py (Playwright) if X_USERNAME set - for local PC
  - x_scraper.py (cookies) if X_AUTH_TOKEN set - for Render cloud
  - Google News RSS fallback if neither is set
"""

import re
import os
import time
import feedparser
from config import Config

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def _clean(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()

def _parse_feed(url, limit=10):
    try:
        feed = feedparser.parse(url, request_headers=HEADERS)
        out  = []
        for e in feed.entries[:limit]:
            title   = _clean(e.get("title", ""))
            summary = _clean(e.get("summary", e.get("description", "")))
            if title:
                out.append({
                    "title":   title,
                    "summary": summary[:350],
                    "link":    e.get("link", ""),
                    "source":  _clean(feed.feed.get("title", url.split("/")[2])),
                })
        return out
    except Exception:
        return []


class NewsFetcher:

    def fetch_geo(self):
        articles = []
        for url in Config.GEOPOLITICS_RSS:
            articles.extend(_parse_feed(url, limit=8))
            time.sleep(0.2)
        return self._dedup(articles)[:50]

    def fetch_breaking(self):
        articles = []
        for url in Config.BREAKING_RSS:
            articles.extend(_parse_feed(url, limit=6))
        kws  = [k.lower() for k in Config.ALERT_KEYWORDS]
        hits = [a for a in articles if any(k in (a["title"] + a["summary"]).lower() for k in kws)]
        return self._dedup(hits)[:15]

    def fetch_tweets(self, force_refresh=False):
        # Option 1: Playwright login (local PC - uses username/password)
        if os.environ.get("X_USERNAME") and os.environ.get("X_PASSWORD"):
            try:
                from x_login import get_tweets
                tweets = get_tweets(force_refresh=force_refresh)
                if tweets:
                    return tweets
            except Exception as e:
                print(f"[FETCHER] x_login error: {e}")

        # Option 2: Cookie-based (Render cloud - uses auth_token + ct0)
        if os.environ.get("X_AUTH_TOKEN") and os.environ.get("X_CT0"):
            try:
                from x_scraper import get_tweets
                tweets = get_tweets(force_refresh=force_refresh)
                if tweets:
                    return tweets
            except Exception as e:
                print(f"[FETCHER] x_scraper error: {e}")

        # Option 3: Google News fallback
        print("[FETCHER] No X credentials - using Google News fallback")
        return self._news_fallback()

    def _news_fallback(self):
        searches = [
            ("Ukraine Russia military conflict", "UAWeapons"),
            ("OSINT conflict geolocated",        "GeoConfirmed"),
            ("NATO military statement",           "NATO"),
            ("Kremlin Russia official",           "KremlinRussia_E"),
            ("China foreign ministry",            "MFA_China"),
            ("Middle East Gaza conflict",         "AJEnglish"),
            ("breaking war attack",               "Reuters"),
            ("geopolitics intelligence",          "IntelCrab"),
        ]
        tweets = []
        for query, handle in searches:
            url  = f"https://news.google.com/rss/search?q={query}&hl=en&gl=IN&ceid=IN:en"
            arts = _parse_feed(url, limit=3)
            for a in arts:
                tweets.append({
                    "handle":  handle,
                    "title":   a["title"],
                    "summary": a["summary"],
                    "source":  f"@{handle} via news",
                })
            time.sleep(0.2)
        return tweets

    def _dedup(self, items):
        seen, out = set(), []
        for a in items:
            k = a["title"].lower()[:55]
            if k not in seen:
                seen.add(k); out.append(a)
        return out

    def articles_to_text(self, articles, max_chars=7000):
        lines = []
        for i, a in enumerate(articles, 1):
            src = a.get("source", a.get("handle", "?"))
            lines.append(f"{i}. [{src}] {a['title']}")
            if a.get("summary"):
                lines.append(f"   {a['summary'][:200]}")
        return "\n".join(lines)[:max_chars]

    def tweets_to_text(self, tweets, max_chars=3000):
        lines = [f"@{t['handle']}: {t['title']}" for t in tweets[:30]]
        return "\n".join(lines)[:max_chars]
