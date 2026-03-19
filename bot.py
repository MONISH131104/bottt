"""
bot.py - SIGINT Telegram Bot
"""

import os
import logging
import schedule
import time
import threading
from datetime import datetime

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

def tg_send(chat_id, text):
    chunks = []
    while text:
        if len(text) <= 4000:
            chunks.append(text)
            break
        cut = text.rfind("\n", 0, 4000)
        if cut == -1:
            cut = 4000
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    for chunk in chunks:
        try:
            r = req.post(f"{BASE}/sendMessage", json={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "Markdown"
            }, timeout=20)
            if not r.json().get("ok"):
                req.post(f"{BASE}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": chunk
                }, timeout=20)
        except Exception as e:
            log(f"Send error: {e}")

def tg_get_updates(offset=None):
    try:
        params = {"timeout": 30, "allowed_updates": ["message"]}
        if offset:
            params["offset"] = offset
        r = req.get(f"{BASE}/getUpdates", params=params, timeout=35)
        data = r.json()
        if data.get("ok"):
            return data.get("result", [])
        else:
            log(f"getUpdates error: {data}")
            return []
    except Exception as e:
        log(f"Poll error: {e}")
        return []


class SigintBot:
    def __init__(self):
        self.fetcher  = NewsFetcher()
        self.analyst  = Analyst()
        self.chat_ids = set()
        self.offset   = None
        self._sent_breaking = set()

    def _date(self):
        return datetime.now(IST).strftime("%A, %d %B %Y")

    def broadcast(self, text):
        for cid in self.chat_ids:
            tg_send(cid, text)

    def handle_start(self, cid, name):
        self.chat_ids.add(cid)
        log(f"Registered {name} ({cid})")
        tg_send(cid,
            f"Hey {name}. I am *SIGINT* — your geopolitics intel feed.\n\n"
            "_I read the world so you don't have to wade through the noise. "
            "What's actually happening, why it matters, what to watch._\n\n"
            "----------\n"
            "*Commands*\n"
            "- /brief — Morning intelligence briefing\n"
            "- /evening — End of day situation update\n"
            "- /deep — Weekly big picture deep dive\n"
            "- /mood — World tension level right now\n"
            "- /twitter — Live feed from tracked X accounts\n"
            "- /track @handle — Add an X account to watch\n"
            "- /accounts — See who I am tracking\n"
            "- Or just *type any question* and I will answer it\n\n"
            "----------\n"
            "Auto: morning brief *08:00 IST* · evening update *20:00 IST* · "
            "breaking alerts whenever something major drops\n\n"
            "Let's go."
        )

    def handle_brief(self, cid):
        log(f"[{cid}] /brief")
        tg_send(cid, "_Pulling feeds and scraping X..._")
        try:
            geo    = self.fetcher.fetch_geo()
            tweets = self.fetcher.fetch_tweets()
            log(f"[{cid}] {len(geo)} articles, {len(tweets)} tweets — calling AI...")
            result = self.analyst.morning_briefing(
                self.fetcher.articles_to_text(geo),
                self.fetcher.tweets_to_text(tweets),
                self._date()
            )
            tg_send(cid, result)
            log(f"[{cid}] /brief done")
        except Exception as e:
            log(f"[{cid}] /brief ERROR: {e}")
            tg_send(cid, f"Error: {e}")

    def handle_evening(self, cid):
        log(f"[{cid}] /evening")
        tg_send(cid, "_Checking what moved today..._")
        try:
            geo    = self.fetcher.fetch_geo()
            result = self.analyst.evening_update(
                self.fetcher.articles_to_text(geo), self._date()
            )
            tg_send(cid, result)
            log(f"[{cid}] /evening done")
        except Exception as e:
            log(f"[{cid}] /evening ERROR: {e}")
            tg_send(cid, f"Error: {e}")

    def handle_deep(self, cid):
        log(f"[{cid}] /deep")
        tg_send(cid, "_Pulling the big thread together... give me a minute._")
        try:
            geo    = self.fetcher.fetch_geo()
            news_t = self.fetcher.articles_to_text(geo)
            topic  = self.analyst.pick_deep_dive_topic(news_t)
            tg_send(cid, f"_This week's deep dive: *{topic}*_")
            result = self.analyst.weekly_deep_dive(news_t, topic)
            tg_send(cid, result)
            log(f"[{cid}] /deep done")
        except Exception as e:
            log(f"[{cid}] /deep ERROR: {e}")
            tg_send(cid, f"Error: {e}")

    def handle_mood(self, cid):
        log(f"[{cid}] /mood")
        try:
            geo    = self.fetcher.fetch_geo()
            result = self.analyst.world_mood(
                self.fetcher.articles_to_text(geo, max_chars=3000)
            )
            tg_send(cid, result)
            log(f"[{cid}] /mood done")
        except Exception as e:
            log(f"[{cid}] /mood ERROR: {e}")
            tg_send(cid, f"Error: {e}")

    def handle_twitter(self, cid):
        log(f"[{cid}] /twitter")
        tg_send(cid, "_Reading the X feeds..._")
        try:
            tweets = self.fetcher.fetch_tweets()
            log(f"[{cid}] {len(tweets)} tweets")
            if not tweets:
                tg_send(cid,
                    "Could not fetch X posts right now.\n"
                    "_X login may need refreshing — try again in a few minutes._"
                )
                return
            geo    = self.fetcher.fetch_geo()
            result = self.analyst.twitter_analysis(
                self.fetcher.tweets_to_text(tweets),
                self.fetcher.articles_to_text(geo, max_chars=2000)
            )
            tg_send(cid, result)
            log(f"[{cid}] /twitter done")
        except Exception as e:
            log(f"[{cid}] /twitter ERROR: {e}")
            tg_send(cid, f"Error: {e}")

    def handle_track(self, cid, handle):
        handle = handle.strip().lstrip("@")
        if not handle:
            tg_send(cid, "Usage: /track elonmusk")
            return
        if handle not in Config.TWITTER_ACCOUNTS:
            Config.TWITTER_ACCOUNTS.append(handle)
            tg_send(cid, f"Added *@{handle}* to the watch list.")
        else:
            tg_send(cid, f"Already tracking *@{handle}*.")

    def handle_accounts(self, cid):
        accs  = Config.TWITTER_ACCOUNTS
        lines = "\n".join(f"- @{a}" for a in accs)
        tg_send(cid,
            f"*Watching {len(accs)} accounts on X:*\n\n{lines}\n\n"
            "_Use /track @handle to add more._"
        )

    def handle_question(self, cid, question):
        log(f"[{cid}] Q: {question[:60]}")
        tg_send(cid, "_On it..._")
        try:
            geo    = self.fetcher.fetch_geo()
            result = self.analyst.answer(question, self.fetcher.articles_to_text(geo))
            tg_send(cid, result)
            log(f"[{cid}] answered")
        except Exception as e:
            log(f"[{cid}] Q ERROR: {e}")
            tg_send(cid, f"Error: {e}")

    def route(self, update):
        msg = update.get("message", {})
        if not msg:
            return
        cid  = msg["chat"]["id"]
        self.chat_ids.add(cid)
        name = msg.get("from", {}).get("first_name", "you")
        text = msg.get("text", "").strip()
        if not text:
            return
        log(f"Msg from {name}: {text[:60]}")
        cmd = text.split()[0].lower().split("@")[0]

        if cmd == "/start":
            threading.Thread(target=self.handle_start, args=(cid, name), daemon=True).start()
        elif cmd in ("/brief", "/morning"):
            threading.Thread(target=self.handle_brief, args=(cid,), daemon=True).start()
        elif cmd == "/evening":
            threading.Thread(target=self.handle_evening, args=(cid,), daemon=True).start()
        elif cmd == "/deep":
            threading.Thread(target=self.handle_deep, args=(cid,), daemon=True).start()
        elif cmd == "/mood":
            threading.Thread(target=self.handle_mood, args=(cid,), daemon=True).start()
        elif cmd == "/twitter":
            threading.Thread(target=self.handle_twitter, args=(cid,), daemon=True).start()
        elif cmd == "/track":
            parts  = text.split(maxsplit=1)
            handle = parts[1] if len(parts) > 1 else ""
            self.handle_track(cid, handle)
        elif cmd == "/accounts":
            threading.Thread(target=self.handle_accounts, args=(cid,), daemon=True).start()
        elif text.startswith("/"):
            tg_send(cid, "Unknown command. Send /start to see what I can do.")
        else:
            threading.Thread(target=self.handle_question, args=(cid, text), daemon=True).start()

    def _sched_morning(self):
        log("Auto morning brief...")
        try:
            geo    = self.fetcher.fetch_geo()
            tweets = self.fetcher.fetch_tweets()
            text   = self.analyst.morning_briefing(
                self.fetcher.articles_to_text(geo),
                self.fetcher.tweets_to_text(tweets),
                self._date()
            )
            self.broadcast(text)
            log("Morning brief sent.")
        except Exception as e:
            log(f"Morning error: {e}")

    def _sched_evening(self):
        log("Auto evening...")
        try:
            geo  = self.fetcher.fetch_geo()
            text = self.analyst.evening_update(
                self.fetcher.articles_to_text(geo), self._date()
            )
            self.broadcast(text)
            log("Evening sent.")
        except Exception as e:
            log(f"Evening error: {e}")

    def _sched_weekly(self):
        log("Auto weekly deep dive...")
        try:
            geo    = self.fetcher.fetch_geo()
            news_t = self.fetcher.articles_to_text(geo)
            topic  = self.analyst.pick_deep_dive_topic(news_t)
            text   = self.analyst.weekly_deep_dive(news_t, topic)
            self.broadcast(f"*Weekly Deep Dive*\n\n{text}")
            log("Deep dive sent.")
        except Exception as e:
            log(f"Deep dive error: {e}")

    def _sched_breaking(self):
        try:
            breaking = self.fetcher.fetch_breaking()
            new = [a for a in breaking if a["title"] not in self._sent_breaking]
            if not new:
                return
            news_t = self.fetcher.articles_to_text(new, max_chars=2000)
            alert  = self.analyst.breaking_alert(news_t)
            if alert:
                self.broadcast(alert)
                for a in new:
                    self._sent_breaking.add(a["title"])
                if len(self._sent_breaking) > 200:
                    self._sent_breaking = set(list(self._sent_breaking)[-100:])
                log("Breaking alert sent.")
        except Exception as e:
            log(f"Breaking error: {e}")

    def _scheduler_thread(self):
        schedule.every().day.at(Config.MORNING_BRIEFING_TIME).do(self._sched_morning)
        schedule.every().day.at(Config.EVENING_BRIEF_TIME).do(self._sched_evening)
        schedule.every(Config.BREAKING_CHECK_MINS).minutes.do(self._sched_breaking)
        getattr(schedule.every(), Config.WEEKLY_DEEP_DIVE_DAY).at(
            Config.WEEKLY_DEEP_DIVE_TIME).do(self._sched_weekly)
        log(f"Scheduler: {Config.MORNING_BRIEFING_TIME} morning / {Config.EVENING_BRIEF_TIME} evening / breaking every {Config.BREAKING_CHECK_MINS}min")
        while True:
            schedule.run_pending()
            time.sleep(20)

    def run(self):
        print("""
+--------------------------------------------+
|   SIGINT - Geopolitics Intelligence Bot   |
+--------------------------------------------+
""")
        if not Config.TELEGRAM_TOKEN:
            print("ERROR: TELEGRAM_TOKEN missing from .env"); return
        if not Config.GROQ_API_KEY:
            print("ERROR: GROQ_API_KEY missing from .env"); return

        log(f"Tracking {len(Config.TWITTER_ACCOUNTS)} X accounts")
        log(f"X login: {'YES' if Config.X_USERNAME else 'NO - add X_USERNAME and X_PASSWORD to .env'}")

        threading.Thread(target=self._scheduler_thread, daemon=True).start()

        log("Bot is live. Send /start in Telegram.")
        log("Ctrl+C to stop\n")

        while True:
            try:
                updates = tg_get_updates(self.offset)
                for update in updates:
                    self.offset = update["update_id"] + 1
                    self.route(update)
                time.sleep(1)
            except KeyboardInterrupt:
                log("Stopped.")
                break
            except Exception as e:
                log(f"Loop error: {e}")
                time.sleep(5)


if __name__ == "__main__":
    SigintBot().run()
