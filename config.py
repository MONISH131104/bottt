"""
config.py
"""
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class Config:
    TELEGRAM_TOKEN        = os.environ.get("TELEGRAM_TOKEN", "")
    GROQ_API_KEY          = os.environ.get("GROQ_API_KEY", "")
    X_USERNAME            = os.environ.get("X_USERNAME", "")
    X_PASSWORD            = os.environ.get("X_PASSWORD", "")

    MORNING_BRIEFING_TIME = "08:00"
    EVENING_BRIEF_TIME    = "20:00"
    WEEKLY_DEEP_DIVE_DAY  = "sunday"
    WEEKLY_DEEP_DIVE_TIME = "10:00"
    BREAKING_CHECK_MINS   = 20

    TWITTER_ACCOUNTS = [
        "GeoConfirmed", "IntelCrab", "UAWeapons", "OSINTtechnical",
        "WarMonitor3", "sentdefcon", "Conflicts", "RALee85",
        "michaeldweiss", "EliotHiggins", "KofmanMichael",
        "KremlinRussia_E", "MFA_China", "NATO",
        "Reuters", "spectatorindex", "AJEnglish", "BBCBreaking",
    ]

    GEOPOLITICS_RSS = [
        "https://feeds.reuters.com/reuters/worldNews",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://foreignpolicy.com/feed/",
        "https://www.theguardian.com/world/rss",
        "https://news.google.com/rss/search?q=war+conflict+geopolitics+2025&hl=en&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Russia+Ukraine+war+latest&hl=en&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Gaza+Israel+Middle+East+conflict&hl=en&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=China+Taiwan+South+China+Sea&hl=en&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=NATO+sanctions+diplomacy+nuclear&hl=en&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=India+Pakistan+border+military&hl=en&gl=IN&ceid=IN:en",
    ]

    BREAKING_RSS = [
        "https://feeds.reuters.com/reuters/topNews",
        "https://feeds.bbci.co.uk/news/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://news.google.com/rss/search?q=breaking+attack+strike+invasion&hl=en&gl=IN&ceid=IN:en",
    ]

    ALERT_KEYWORDS = [
        "nuclear", "missile strike", "invasion", "coup", "assassination",
        "war declared", "attack on", "troops cross", "ceasefire broken",
        "market crash", "emergency declared", "explosion", "bombed",
        "breaking:", "just in:", "developing:",
    ]

    DEEP_DIVE_TOPICS = [
        "Russia-Ukraine war",
        "China-Taiwan tensions",
        "Middle East conflict",
        "Global sanctions and economic war",
        "Nuclear proliferation risks",
    ]
