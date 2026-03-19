"""
x_login.py — Logs into X with your username and password, scrapes tweets.
No cookie copying. No manual steps. Just username + password in .env

Add to .env:
  X_USERNAME=your_email_or_username
  X_PASSWORD=your_password

INSTALL (one time):
  pip install playwright
  playwright install chromium

This script is called automatically by the bot.
Run standalone to test: python x_login.py
"""

import os
import json
import time
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

CACHE_FILE      = "tweets_cache.json"
CACHE_MAX_AGE   = 20 * 60   # 20 minutes
SESSION_FILE    = "x_session.json"

ACCOUNTS = [
    "GeoConfirmed", "IntelCrab", "UAWeapons", "OSINTtechnical",
    "WarMonitor3", "sentdefcon", "Conflicts", "RALee85",
    "michaeldweiss", "EliotHiggins", "KofmanMichael",
    "KremlinRussia_E", "MFA_China", "NATO",
    "Reuters", "spectatorindex", "AJEnglish", "BBCBreaking",
]


# ── Cache helpers ─────────────────────────────────────────────────────────────

def cache_fresh():
    if not os.path.exists(CACHE_FILE):
        return False
    return (time.time() - os.path.getmtime(CACHE_FILE)) < CACHE_MAX_AGE

def save_cache(tweets):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(tweets, f, ensure_ascii=False, indent=2)
    print(f"[X] Saved {len(tweets)} tweets to cache")

def load_cache():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


# ── Browser scraper ───────────────────────────────────────────────────────────

def scrape_with_browser(headless=True):
    """
    Opens a real Chromium browser, logs into X with your credentials,
    scrapes tweets from each tracked account.
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        print("[X] Playwright not installed. Run: pip install playwright && playwright install chromium")
        return []

    username = os.environ.get("X_USERNAME", "").strip()
    password = os.environ.get("X_PASSWORD", "").strip()

    if not username or not password:
        print("[X] X_USERNAME or X_PASSWORD not set in .env")
        return []

    all_tweets = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)

        # Try to reuse saved session (skips login if still valid)
        try:
            if os.path.exists(SESSION_FILE):
                ctx = browser.new_context(
                    storage_state=SESSION_FILE,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 900}
                )
                print("[X] Loaded saved session")
            else:
                raise FileNotFoundError
        except Exception:
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 900}
            )

        page = ctx.new_page()

        # ── Check if already logged in ────────────────────────────────────────
        try:
            page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=20000)
            time.sleep(3)
            needs_login = "login" in page.url or "i/flow" in page.url or "signin" in page.url
        except Exception:
            needs_login = True

        # ── Login if needed ───────────────────────────────────────────────────
        if needs_login:
            print("[X] Logging in...")
            try:
                page.goto("https://x.com/login", wait_until="domcontentloaded", timeout=20000)
                time.sleep(2)

                # Enter username
                page.wait_for_selector('input[autocomplete="username"]', timeout=10000)
                page.fill('input[autocomplete="username"]', username)
                time.sleep(1)
                page.keyboard.press("Enter")
                time.sleep(2)

                # X sometimes asks for username again as extra check
                try:
                    extra = page.locator('input[data-testid="ocfEnterTextTextInput"]')
                    if extra.count() > 0:
                        print("[X] Extra verification step — entering username...")
                        extra.fill(username)
                        page.keyboard.press("Enter")
                        time.sleep(2)
                except Exception:
                    pass

                # Enter password
                page.wait_for_selector('input[name="password"]', timeout=10000)
                page.fill('input[name="password"]', password)
                time.sleep(1)
                page.keyboard.press("Enter")
                time.sleep(5)

                if "home" in page.url:
                    print("[X] Login successful")
                    ctx.storage_state(path=SESSION_FILE)
                    print("[X] Session saved — next run will skip login")
                else:
                    print(f"[X] Login may have failed. Current URL: {page.url}")
                    browser.close()
                    return []

            except Exception as e:
                print(f"[X] Login error: {e}")
                browser.close()
                return []
        else:
            print("[X] Already logged in")
            # Refresh saved session
            ctx.storage_state(path=SESSION_FILE)

        # ── Scrape each account ────────────────────────────────────────────────
        print(f"[X] Scraping {len(ACCOUNTS)} accounts...")

        for handle in ACCOUNTS:
            try:
                page.goto(f"https://x.com/{handle}", wait_until="domcontentloaded", timeout=15000)
                time.sleep(2)
                page.mouse.wheel(0, 600)
                time.sleep(1)

                tweet_els = page.locator('[data-testid="tweetText"]').all()
                count = 0
                for el in tweet_els[:5]:
                    try:
                        text = el.inner_text().strip()
                        if text and len(text) > 15:
                            all_tweets.append({
                                "handle":     handle,
                                "title":      text[:280],
                                "summary":    "",
                                "source":     f"@{handle} on X",
                                "scraped_at": datetime.now().isoformat(),
                            })
                            count += 1
                    except Exception:
                        continue

                print(f"[X]   @{handle}: {count} tweets")
                time.sleep(1)

            except PWTimeout:
                print(f"[X]   @{handle}: timeout, skipping")
                continue
            except Exception as e:
                print(f"[X]   @{handle}: error - {e}")
                continue

        browser.close()

    print(f"[X] Total scraped: {len(all_tweets)} tweets")
    return all_tweets


# ── Main entry point called by bot ────────────────────────────────────────────

def get_tweets(force_refresh=False):
    """
    Returns tweets. Uses cache if fresh, otherwise scrapes.
    Called by fetcher.py automatically.
    """
    if not force_refresh and cache_fresh():
        tweets = load_cache()
        print(f"[X] Cache hit — {len(tweets)} tweets")
        return tweets

    tweets = scrape_with_browser(headless=True)

    if tweets:
        save_cache(tweets)
        return tweets

    # Scrape failed — return stale cache if available
    if os.path.exists(CACHE_FILE):
        print("[X] Scrape failed, using stale cache")
        return load_cache()

    return []

def add_account(handle):
    handle = handle.strip().lstrip("@")
    if handle not in ACCOUNTS:
        ACCOUNTS.append(handle)
        return True
    return False


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    force   = "--force"  in sys.argv
    visible = "--show"   in sys.argv

    if visible:
        print("[X] Visible browser mode...")
        tweets = scrape_with_browser(headless=False)
        if tweets:
            save_cache(tweets)
    else:
        tweets = get_tweets(force_refresh=force)

    print(f"\n{'='*50}")
    print(f"Total: {len(tweets)} tweets")
    print(f"{'='*50}")
    for t in tweets[:15]:
        print(f"\n@{t['handle']}:")
        print(f"  {t['title'][:120]}")
