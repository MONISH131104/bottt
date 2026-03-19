"""
bot_render.py - Use this on Render instead of bot.py
Has health check server so UptimeRobot can ping it.
Rename to bot.py when deploying to Render.
"""

import os
import logging
import schedule
import time
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

import pytz
import requests as req

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config import Config
from fetcher import NewsFetcher
from analyst import Analyst

logging.basicConfig(level=logging.WARNING)
IST  = pytz.timezone("Asia/Kolkata")
BASE = f"https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}"

def ts():
    return datetime.now(IST).strftime("%H:%M:%S")
def log(msg):
    print(f"[{ts()}] {msg}", flush=True)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"SIGINT alive")
    def log_message(self, *args): pass

def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    log(f"Health server on port {port}")
    HTTPServer(("0.0.0.0", port), HealthHandler).serve_forever()

def tg_send(chat_id, text):
    chunks = []
    while text:
        if len(text) <= 4000:
            chunks.append(text); break
        cut = text.rfind("\n", 0, 4000)
        if cut == -1: cut = 4000
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    for chunk in chunks:
        try:
            r = req.post(f"{BASE}/sendMessage", json={
                "chat_id": chat_id, "text": chunk, "parse_mode": "Markdown"
            }, timeout=20)
            if not r.json().get("ok"):
                req.post(f"{BASE}/sendMessage", json={"chat_id": chat_id, "text": chunk}, timeout=20)
        except Exception as e:
            log(f"Send error: {e}")

def tg_get_updates(offset=None):
    try:
        params = {"timeout": 30, "allowed_updates": ["message"]}
        if offset: params["offset"] = offset
        r = req.get(f"{BASE}/getUpdates", params=params, timeout=35)
        data = r.json()
        return data.get("result", []) if data.get("ok") else []
    except Exception as e:
        log(f"Poll error: {e}"); return []

class SigintBot:
    def __init__(self):
        self.fetcher = NewsFetcher()
        self.analyst = Analyst()
        self.chat_ids = set()
        self.offset = None
        self._sent_breaking = set()

    def _date(self):
        return datetime.now(IST).strftime("%A, %d %B %Y")

    def broadcast(self, text):
        for cid in self.chat_ids: tg_send(cid, text)

    def handle_start(self, cid, name):
        self.chat_ids.add(cid)
        tg_send(cid,
            f"Hey {name}. I am *SIGINT* — your geopolitics intel feed.\n\n"
            "_I read the world so you don't have to wade through the noise._\n\n"
            "----------\n*Commands*\n"
            "- /brief — Morning intelligence briefing\n"
            "- /evening — End of day update\n"
            "- /deep — Weekly big picture deep dive\n"
            "- /mood — World tension level right now\n"
            "- /twitter — Live X feed analysis\n"
            "- /track @handle — Add an X account\n"
            "- /accounts — Who I am watching\n"
            "- Or just *type any question*\n\n"
            "----------\n"
            "Auto: *08:00 IST* morning · *20:00 IST* evening · breaking alerts anytime\n\nLet's go."
        )

    def handle_brief(self, cid):
        tg_send(cid, "_Pulling feeds and X..._")
        try:
            geo = self.fetcher.fetch_geo()
            tweets = self.fetcher.fetch_tweets()
            result = self.analyst.morning_briefing(
                self.fetcher.articles_to_text(geo),
                self.fetcher.tweets_to_text(tweets), self._date())
            tg_send(cid, result)
        except Exception as e:
            tg_send(cid, f"Error: {e}")

    def handle_evening(self, cid):
        tg_send(cid, "_Checking what moved today..._")
        try:
            geo = self.fetcher.fetch_geo()
            tg_send(cid, self.analyst.evening_update(self.fetcher.articles_to_text(geo), self._date()))
        except Exception as e:
            tg_send(cid, f"Error: {e}")

    def handle_deep(self, cid):
        tg_send(cid, "_Pulling the big thread together..._")
        try:
            geo = self.fetcher.fetch_geo()
            news_t = self.fetcher.articles_to_text(geo)
            topic = self.analyst.pick_deep_dive_topic(news_t)
            tg_send(cid, f"_This week: *{topic}*_")
            tg_send(cid, self.analyst.weekly_deep_dive(news_t, topic))
        except Exception as e:
            tg_send(cid, f"Error: {e}")

    def handle_mood(self, cid):
        try:
            geo = self.fetcher.fetch_geo()
            tg_send(cid, self.analyst.world_mood(self.fetcher.articles_to_text(geo, max_chars=3000)))
        except Exception as e:
            tg_send(cid, f"Error: {e}")

    def handle_twitter(self, cid):
        tg_send(cid, "_Reading the X feeds..._")
        try:
            tweets = self.fetcher.fetch_tweets()
            if not tweets:
                tg_send(cid, "Could not fetch X posts right now. Try again shortly."); return
            geo = self.fetcher.fetch_geo()
            tg_send(cid, self.analyst.twitter_analysis(
                self.fetcher.tweets_to_text(tweets),
                self.fetcher.articles_to_text(geo, max_chars=2000)))
        except Exception as e:
            tg_send(cid, f"Error: {e}")

    def handle_track(self, cid, handle):
        handle = handle.strip().lstrip("@")
        if not handle:
            tg_send(cid, "Usage: /track elonmusk"); return
        if handle not in Config.TWITTER_ACCOUNTS:
            Config.TWITTER_ACCOUNTS.append(handle)
            tg_send(cid, f"Added *@{handle}* to the watch list.")
        else:
            tg_send(cid, f"Already tracking *@{handle}*.")

    def handle_accounts(self, cid):
        lines = "\n".join(f"- @{a}" for a in Config.TWITTER_ACCOUNTS)
        tg_send(cid, f"*Watching {len(Config.TWITTER_ACCOUNTS)} accounts:*\n\n{lines}")

    def handle_question(self, cid, question):
        tg_send(cid, "_On it..._")
        try:
            geo = self.fetcher.fetch_geo()
            tg_send(cid, self.analyst.answer(question, self.fetcher.articles_to_text(geo)))
        except Exception as e:
            tg_send(cid, f"Error: {e}")

    def route(self, update):
        msg = update.get("message", {})
        if not msg: return
        cid  = msg["chat"]["id"]
        self.chat_ids.add(cid)
        name = msg.get("from", {}).get("first_name", "you")
        text = msg.get("text", "").strip()
        if not text: return
        log(f"Msg from {name}: {text[:60]}")
        cmd = text.split()[0].lower().split("@")[0]

        dispatch = {
            "/start":   lambda: self.handle_start(cid, name),
            "/brief":   lambda: self.handle_brief(cid),
            "/morning": lambda: self.handle_brief(cid),
            "/evening": lambda: self.handle_evening(cid),
            "/deep":    lambda: self.handle_deep(cid),
            "/mood":    lambda: self.handle_mood(cid),
            "/twitter": lambda: self.handle_twitter(cid),
            "/accounts":lambda: self.handle_accounts(cid),
        }
        if cmd in dispatch:
            threading.Thread(target=dispatch[cmd], daemon=True).start()
        elif cmd == "/track":
            parts = text.split(maxsplit=1)
            self.handle_track(cid, parts[1] if len(parts) > 1 else "")
        elif text.startswith("/"):
            tg_send(cid, "Unknown command. Send /start to see what I can do.")
        else:
            threading.Thread(target=self.handle_question, args=(cid, text), daemon=True).start()

    def _sched_morning(self):
        try:
            geo = self.fetcher.fetch_geo()
            tweets = self.fetcher.fetch_tweets()
            self.broadcast(self.analyst.morning_briefing(
                self.fetcher.articles_to_text(geo),
                self.fetcher.tweets_to_text(tweets), self._date()))
            log("Morning brief sent.")
        except Exception as e: log(f"Morning error: {e}")

    def _sched_evening(self):
        try:
            geo = self.fetcher.fetch_geo()
            self.broadcast(self.analyst.evening_update(self.fetcher.articles_to_text(geo), self._date()))
            log("Evening sent.")
        except Exception as e: log(f"Evening error: {e}")

    def _sched_weekly(self):
        try:
            geo = self.fetcher.fetch_geo()
            news_t = self.fetcher.articles_to_text(geo)
            topic = self.analyst.pick_deep_dive_topic(news_t)
            self.broadcast(self.analyst.weekly_deep_dive(news_t, topic))
            log("Deep dive sent.")
        except Exception as e: log(f"Deep dive error: {e}")

    def _sched_breaking(self):
        try:
            breaking = self.fetcher.fetch_breaking()
            new = [a for a in breaking if a["title"] not in self._sent_breaking]
            if not new: return
            alert = self.analyst.breaking_alert(self.fetcher.articles_to_text(new, max_chars=2000))
            if alert:
                self.broadcast(alert)
                for a in new: self._sent_breaking.add(a["title"])
                log("Breaking alert sent.")
        except Exception as e: log(f"Breaking error: {e}")

    def _scheduler_thread(self):
        schedule.every().day.at(Config.MORNING_BRIEFING_TIME).do(self._sched_morning)
        schedule.every().day.at(Config.EVENING_BRIEF_TIME).do(self._sched_evening)
        schedule.every(Config.BREAKING_CHECK_MINS).minutes.do(self._sched_breaking)
        getattr(schedule.every(), Config.WEEKLY_DEEP_DIVE_DAY).at(Config.WEEKLY_DEEP_DIVE_TIME).do(self._sched_weekly)
        log(f"Scheduler ready")
        while True:
            schedule.run_pending()
            time.sleep(20)

    def run(self):
        print("\n+------------------------------------------+\n|  SIGINT - Geopolitics Intelligence Bot  |\n+------------------------------------------+\n")
        if not Config.TELEGRAM_TOKEN: print("ERROR: TELEGRAM_TOKEN missing"); return
        if not Config.GROQ_API_KEY: print("ERROR: GROQ_API_KEY missing"); return
        log(f"Tracking {len(Config.TWITTER_ACCOUNTS)} X accounts")
        threading.Thread(target=start_health_server, daemon=True).start()
        threading.Thread(target=self._scheduler_thread, daemon=True).start()
        log("Bot live.")
        while True:
            try:
                updates = tg_get_updates(self.offset)
                for update in updates:
                    self.offset = update["update_id"] + 1
                    self.route(update)
                time.sleep(1)
            except KeyboardInterrupt:
                log("Stopped."); break
            except Exception as e:
                log(f"Loop error: {e}"); time.sleep(5)

if __name__ == "__main__":
    SigintBot().run()
