"""
x_scraper.py - Fetches tweets using X session cookies.
Works on Render cloud. No browser needed.
"""
 
import os
import json
import time
from datetime import datetime
import requests
 
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
 
CACHE_FILE    = "/tmp/tweets_cache.json"  # use /tmp on Render
CACHE_MAX_AGE = 25 * 60
 
ACCOUNTS_TO_TRACK = [
    "GeoConfirmed", "IntelCrab", "UAWeapons", "OSINTtechnical",
    "WarMonitor3", "sentdefcon", "Conflicts", "RALee85",
    "michaeldweiss", "EliotHiggins", "KofmanMichael",
    "KremlinRussia_E", "MFA_China", "NATO",
    "Reuters", "spectatorindex", "AJEnglish", "BBCBreaking",
]
 
BEARER = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I4xL1vDwAAA%3DBUW0XlbCqsNRxuClBXd1I4EpiJzGOWHnHSvWsMkfkGBnDfnqiG"
 
 
class XClient:
    def __init__(self):
        self.auth_token = os.environ.get("X_AUTH_TOKEN", "").strip()
        self.ct0        = os.environ.get("X_CT0", "").strip()
        self.available  = bool(self.auth_token and self.ct0)
 
        print(f"[X] Auth token present: {bool(self.auth_token)} (length: {len(self.auth_token)})")
        print(f"[X] CT0 present: {bool(self.ct0)} (length: {len(self.ct0)})")
 
        self.session = requests.Session()
        if self.available:
            self.session.headers.update({
                "User-Agent":            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Authorization":         f"Bearer {BEARER}",
                "X-Csrf-Token":          self.ct0,
                "X-Twitter-Auth-Type":   "OAuth2Session",
                "X-Twitter-Active-User": "yes",
                "Referer":               "https://twitter.com/",
                "Content-Type":          "application/json",
            })
            self.session.cookies.set("auth_token", self.auth_token, domain=".twitter.com")
            self.session.cookies.set("ct0",         self.ct0,        domain=".twitter.com")
            self.session.cookies.set("auth_token", self.auth_token, domain=".x.com")
            self.session.cookies.set("ct0",         self.ct0,        domain=".x.com")
 
    def get_user_tweets(self, handle, count=6):
        if not self.available:
            return []
        uid = self._get_user_id(handle)
        if not uid:
            return []
        try:
            url = "https://api.twitter.com/graphql/V7H0Ap3_Hh2FyS75OCDO3Q/UserTweets"
            params = {
                "variables": json.dumps({
                    "userId": uid, "count": count,
                    "includePromotedContent": False,
                }),
                "features": json.dumps({
                    "rweb_lists_timeline_redesign_enabled": True,
                    "responsive_web_graphql_exclude_directive_enabled": True,
                    "verified_phone_label_enabled": False,
                    "creator_subscriptions_tweet_preview_api_enabled": True,
                    "responsive_web_graphql_timeline_navigation_enabled": True,
                    "longform_notetweets_consumption_enabled": True,
                    "freedom_of_speech_not_reach_fetch_enabled": True,
                    "standardized_nudges_misinfo": True,
                    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                    "longform_notetweets_rich_text_read_enabled": True,
                    "longform_notetweets_inline_media_enabled": True,
                    "responsive_web_enhance_cards_enabled": False,
                })
            }
            r    = self.session.get(url, params=params, timeout=10)
            data = r.json()
            tweets = []
            for inst in data.get("data", {}).get("user", {}).get("result", {}).get("timeline_v2", {}).get("timeline", {}).get("instructions", []):
                for entry in inst.get("entries", []):
                    try:
                        legacy = entry["content"]["itemContent"]["tweet_results"]["result"]["legacy"]
                        text   = legacy.get("full_text", "")
                        if text and not text.startswith("RT @") and len(text) > 10:
                            tweets.append({
                                "handle": handle, "title": text[:280],
                                "summary": "", "source": f"@{handle} on X",
                                "scraped_at": datetime.now().isoformat(),
                            })
                    except Exception:
                        continue
            return tweets[:5]
        except Exception as e:
            print(f"[X] Error @{handle}: {e}")
            return []
 
    def _get_user_id(self, handle):
        url = "https://api.twitter.com/graphql/G3KGOASz96M-Qu0nwmGXNg/UserByScreenName"
        params = {
            "variables": json.dumps({"screen_name": handle, "withSafetyModeUserFields": True}),
            "features":  json.dumps({
                "hidden_profile_likes_enabled": True,
                "hidden_profile_subscriptions_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "responsive_web_graphql_timeline_navigation_enabled": True,
            })
        }
        try:
            r = self.session.get(url, params=params, timeout=10)
            uid = r.json().get("data", {}).get("user", {}).get("result", {}).get("rest_id")
            print(f"[X] User ID for @{handle}: {uid}")
            return uid
        except Exception as e:
            print(f"[X] User ID error @{handle}: {e}")
            return None
 
    def get_home_timeline(self, count=40):
        if not self.available:
            return []
        try:
            url = "https://api.twitter.com/graphql/HJFjzBgCs16TqxewQOeLNg/HomeTimeline"
            params = {
                "variables": json.dumps({
                    "count": count, "includePromotedContent": False,
                    "latestControlAvailable": True, "withCommunity": True,
                }),
                "features": json.dumps({
                    "rweb_lists_timeline_redesign_enabled": True,
                    "responsive_web_graphql_exclude_directive_enabled": True,
                    "verified_phone_label_enabled": False,
                    "creator_subscriptions_tweet_preview_api_enabled": True,
                    "responsive_web_graphql_timeline_navigation_enabled": True,
                    "longform_notetweets_consumption_enabled": True,
                    "freedom_of_speech_not_reach_fetch_enabled": True,
                    "standardized_nudges_misinfo": True,
                    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                    "longform_notetweets_rich_text_read_enabled": True,
                    "longform_notetweets_inline_media_enabled": True,
                    "responsive_web_enhance_cards_enabled": False,
                })
            }
            r    = self.session.get(url, params=params, timeout=10)
            data = r.json()
            print(f"[X] Home timeline response keys: {list(data.keys())}")
 
            tweets = []
            for inst in data.get("data", {}).get("home", {}).get("home_timeline_ux", {}).get("instructions", []):
                for entry in inst.get("entries", []):
                    try:
                        result = entry["content"]["itemContent"]["tweet_results"]["result"]
                        legacy = result["legacy"]
                        handle = result["core"]["user_results"]["result"]["legacy"].get("screen_name", "unknown")
                        text   = legacy.get("full_text", "")
                        if text and not text.startswith("RT @") and len(text) > 10:
                            tweets.append({
                                "handle": handle, "title": text[:280],
                                "summary": "", "source": f"@{handle} on X",
                                "scraped_at": datetime.now().isoformat(),
                            })
                    except Exception:
                        continue
            print(f"[X] Home timeline tweets found: {len(tweets)}")
            return tweets
        except Exception as e:
            print(f"[X] Home timeline error: {e}")
            return []
 
 
def cache_is_fresh():
    if not os.path.exists(CACHE_FILE):
        return False
    return (time.time() - os.path.getmtime(CACHE_FILE)) < CACHE_MAX_AGE
 
def load_cache():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []
 
def save_cache(tweets):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(tweets, f, ensure_ascii=False, indent=2)
    print(f"[X] Cached {len(tweets)} tweets")
 
 
_client = None
 
def get_tweets(force_refresh=False):
    global _client
    if _client is None:
        _client = XClient()
 
    if not _client.available:
        print("[X] No cookies found in environment variables")
        return []
 
    if not force_refresh and cache_is_fresh():
        tweets = load_cache()
        print(f"[X] Cache hit - {len(tweets)} tweets")
        return tweets
 
    print("[X] Fetching fresh tweets via cookies...")
 
    # Try home timeline first
    tweets = _client.get_home_timeline(count=50)
 
    if not tweets:
        print("[X] Home timeline empty, trying per-account...")
        for handle in ACCOUNTS_TO_TRACK[:10]:
            t = _client.get_user_tweets(handle, count=5)
            tweets.extend(t)
            time.sleep(0.5)
 
    if tweets:
        save_cache(tweets)
        print(f"[X] Total: {len(tweets)} tweets")
    else:
        print("[X] No tweets fetched - cookies may be expired")
        if os.path.exists(CACHE_FILE):
            print("[X] Using stale cache")
            return load_cache()
 
    return tweets
 
def add_account(handle):
    handle = handle.strip().lstrip("@")
    if handle not in ACCOUNTS_TO_TRACK:
        ACCOUNTS_TO_TRACK.append(handle)
        return True
    return False

def add_account(handle):
    handle = handle.strip().lstrip("@")
    if handle not in ACCOUNTS_TO_TRACK:
        ACCOUNTS_TO_TRACK.append(handle)
        return True
    return False


if __name__ == "__main__":
    import sys
    tweets = get_tweets(force_refresh="--force" in sys.argv)
    print(f"\nTotal: {len(tweets)} tweets")
    for t in tweets[:10]:
        print(f"\n@{t['handle']}: {t['title'][:120]}")
