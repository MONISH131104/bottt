"""
analyst.py - SIGINT AI brain using Groq (Llama-3)
"""

from groq import Groq
from config import Config

PERSONA = """You are SIGINT - a sharp geopolitical intelligence analyst with real personality.

Your voice:
- Direct, confident, opinionated. You say what you actually think.
- Use analogies that make complex things click instantly.
- Dry wit when the world is being absurd - never at expense of accuracy.
- Always have a "So what?" layer - not just what happened but why it shifts things.
- Short punchy sentences when things are serious. More texture when explaining context.
- Never use: "it remains to be seen", "complex situation", "stakeholders", "multifaceted"
- Treat the reader as smart. No hand-holding.

Telegram formatting rules - follow these exactly:
- *bold* for country names, leader names, organisations, key events: *Iran*, *Putin*, *NATO*
- _italic_ for status, tone, uncertainty: _unconfirmed_, _significant_, _worth watching_
- Tweets must be quoted like this: @handle: "tweet text here" - then your one line analysis
- Section headers: write as *HEADER* on its own line
- Dividers: ----------
- Bullet points: start with -
- NO hashtag headers (#), NO triple backticks, NO markdown tables
"""

def _ask(prompt, max_tokens=1800):
    try:
        client = Groq(api_key=Config.GROQ_API_KEY)
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": PERSONA},
                {"role": "user",   "content": prompt},
            ]
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        return f"AI error: {e}"


class Analyst:

    def morning_briefing(self, news_text, tweet_text, date_str):
        return _ask(f"""Today is {date_str}. Write the morning intelligence briefing.

NEWS FROM RSS SOURCES:
{news_text}

LIVE TWEETS FROM TRACKED X ACCOUNTS:
{tweet_text}

Write the briefing in this exact structure:

Line 1 - world mood: pick one emoji and one sentence
🟢 _Relatively calm_ - [reason]
🟡 _Simmering_ - [reason]
🔴 _Escalating_ - [reason]

----------
*MORNING BRIEF* — {date_str}
----------

*What is happening*
3 to 4 bullets. Each = one real development + one sentence on why it matters.
Bold the key actor or place in each bullet.
Example: - *Russia* launched a new drone wave targeting *Kharkiv* overnight - third attack this week, suggests a shift toward infrastructure pressure ahead of winter.

----------
*The thread connecting everything*
Pick the ONE story that links the most things happening right now.
Write 3 to 4 sentences like you are explaining it to a smart friend who has not been following closely.
Bold key names and places.

----------
*From X — what the feeds are saying*
Pull 2 to 3 of the most significant tweets from the feed below.
Format each one like this:
@handle: "[tweet text]"
_Why this matters: one sentence analysis_

Only include tweets that actually add signal - skip noise and retweets.

----------
*So what*
2 to 3 sentences. What does all of this add up to.
What should a switched on person be watching in the next 24 to 48 hours.
Be specific - name the country, the flashpoint, the thing that could tip.

Under 600 words total.""")

    def evening_update(self, news_text, date_str):
        return _ask(f"""End of day situation update. Date: {date_str}

NEWS:
{news_text}

Write a tight evening update. Under 250 words.

*Evening Update* — {date_str}

*What moved today*
2 to 3 bullets. Only things that genuinely developed or changed since this morning.
Bold key names and places. Skip anything static or routine.

*Overnight watch*
1 to 2 specific things to monitor as Asia and Europe open.
Name the country, the flashpoint, what a bad development would look like.""", max_tokens=600)

    def breaking_alert(self, articles_text):
        result = _ask(f"""Evaluate these news items for a breaking alert.

{articles_text}

Only flag genuinely major events: real military strikes, invasions, coups, nuclear events, major market crashes, assassination attempts.
NOT for: political speeches, minor skirmishes, routine data releases.

If major, write:
🚨 *BREAKING*

[What happened - one direct sentence. Bold the key actor and location.]
[Why it matters - two sentences max.]
[What to watch next - one sentence.]

If nothing is genuinely major, reply with exactly: SKIP""", max_tokens=300)
        if result.strip().upper().startswith("SKIP"):
            return None
        return result

    def answer(self, question, context_text):
        return _ask(f"""Question from user: "{question}"

Current news context:
{context_text}

Answer like yourself - direct, grounded, with a "so what" at the end.
Bold key names and places. Under 350 words.
Use a few bullets where they genuinely help, otherwise prose.""", max_tokens=900)

    def twitter_analysis(self, tweet_text, geo_context):
        return _ask(f"""Analyse the latest posts from tracked X accounts.

TWEETS:
{tweet_text}

NEWS CONTEXT:
{geo_context}

Write a focused X intelligence update.

*X Intelligence Feed*

For each significant tweet write:
@handle: "[tweet text]"
_Analysis: one sentence on what this signals or why it matters_

Then at the end:

*Patterns in the feed*
2 to 3 sentences on what the overall X conversation is converging on today.
What is the signal beneath the noise?

Only include tweets with real intelligence value. Skip fluff.""", max_tokens=1000)

    def weekly_deep_dive(self, news_text, topic):
        return _ask(f"""Write the weekly deep dive analysis. Topic: *{topic}*

NEWS CONTEXT:
{news_text}

*THE BIG THREAD*
*{topic}*
----------

*How we got here*
4 to 5 sentences. What was the situation 6 months ago vs now. What actually changed.
Bold key names and turning points.

----------
*What is actually happening right now*
The current state of play. Who is doing what.
The real dynamic beneath the surface that headlines miss.

----------
*The players and what they actually want*
3 to 4 key actors. Not their public position - what they actually want and why.
One short paragraph each. Bold their names.

----------
*The scenarios*
Two or three plausible ways this develops over the next 1 to 3 months.
Label each clearly. What would have to happen for each one.

----------
*The one thing*
One sentence. The single most important thing to understand about this situation
that most coverage completely misses.

Under 800 words. Write like you mean it.""", max_tokens=2000)

    def world_mood(self, news_text):
        return _ask(f"""Based on today's news, give me the world mood in one line.
Start with the right emoji: 🟢 calm, 🟡 tense or simmering, 🔴 escalating or critical.
Then one sentence in _italic_ explaining why. Max 25 words after the emoji.
Nothing else - just that one line.

NEWS:
{news_text[:2000]}""", max_tokens=60)

    def pick_deep_dive_topic(self, news_text):
        topics = "\n".join(f"- {t}" for t in Config.DEEP_DIVE_TOPICS)
        result = _ask(f"""Which of these topics is most relevant and has the most to analyse this week?

{topics}

Based on this news:
{news_text[:2000]}

Reply with ONLY the topic name. Nothing else.""", max_tokens=30)
        for t in Config.DEEP_DIVE_TOPICS:
            if t.lower() in result.lower():
                return t
        return Config.DEEP_DIVE_TOPICS[0]
