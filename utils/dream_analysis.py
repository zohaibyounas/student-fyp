import json
import re
import os
import requests

POSITIVE_WORDS = {
    "happy", "peace", "peaceful", "angel", "angels", "light", "bright", "prayer", "pray",
    "mosque", "masjid", "heaven", "beautiful", "blessed", "blessing", "flying", "garden",
    "paradise", "success", "love", "joy", "calm", "safe", "smile", "smiling", "green",
    "water", "river", "quran", "prophet", "allah", "jannah", "mercy", "guidance", "faith",
    "kaaba", "hajj", "umrah", "white", "gold", "flowers", "tree", "trees", "rainbow",
    "khushi", "sukoon", "aman", "masjid", "namaz", "dua", "roshni", "noor", "hara",
    "phool", "pak", "muhabbat", "kamyabi", "umeed", "rehmat", "barkat", "farishta",
    "jannat", "khush", "acha", "accha", "sawab", "rahmat",
}

NEGATIVE_WORDS = {
    "scary", "scared", "dark", "darkness", "monster", "death", "dead", "die", "dying",
    "snake", "snakes", "fire", "burning", "falling", "chasing", "chase", "fear", "afraid",
    "crying", "cry", "blood", "demon", "demons", "evil", "nightmare", "drowning", "hurt",
    "pain", "war", "fight", "fighting", "lost", "trapped", "prison", "hell", "devil",
    "satan", "shaitan", "ghost", "horror", "terror", "wound", "injured", "killed",
    "dar", "darr", "andhera", "saanp", "aag", "larai", "khoon", "jinn", "maut", "mar",
    "rona", "pareshan", "azab", "dukh", "ghum", "bura", "kharab", "dhamki", "khauf",
    "shaitani", "jahannam", "zalim", "takleef",
}

REHMANI_WORDS = {
    "prayer", "pray", "mosque", "masjid", "quran", "prophet", "muhammad", "allah",
    "angel", "angels", "heaven", "jannah", "blessing", "guidance", "mercy", "faith",
    "iman", "kaaba", "hadith", "sunnah", "ramadan", "hajj", "umrah", "noor", "light",
    "namaz", "dua", "roza", "wudu", "surah", "ayat", "rehmat", "barkat", "farishta",
    "prophetic", "rehmani",
}

SHAITANI_WORDS = {
    "devil", "satan", "demon", "demons", "evil", "sin", "haram", "magic", "witch",
    "hell", "temptation", "curse", "darkness", "shaitan", "sorcery", "jinn", "ghost",
    "nightmare", "black magic", "shaitani", "azab", "jahannam", "whisper",
}

DREAM_TYPE_HINTS = {
    "nightmare": ("negative", "shaitani"),
    "prophetic": ("positive", "rehmani"),
}

MEANINGS = {
    ("positive", "rehmani"): (
        "Yeh khwab bohat acha aur roohani taur par aham hai. Is mein Allah ki rehmat, "
        "hidayat aur barkat ki nishani hai — apni ibadat aur zikr ko mazeed mazboot rakhein."
    ),
    ("positive", "shaitani"): (
        "Khwab ke alamat achi lagti hain lekin chupi hui pareshani ho sakti hai. "
        "Sone se pehle Ayat-ul-Kursi aur teen Qul parhein aur Allah ki panah maangein."
    ),
    ("positive", "nafsani"): (
        "Yeh khwab aap ki umeed, khushi aur dil ki khawahishon ko dikhata hai. "
        "Achi soch ko barkarar rakhein aur din mein shukr ada karein."
    ),
    ("negative", "rehmani"): (
        "Yeh khwab ek roohani ishara ho sakta hai — apni galtiyon se tawba karein, "
        "namaz aur dua mein izafa karein taake dil ko sukoon mile."
    ),
    ("negative", "shaitani"): (
        "Yeh ek khaufnaak ya pareshan kun khwab hai jo shaitani waswasay ki taraf ishara kar sakta hai. "
        "Sone se pehle wudu karke teen Qul aur Ayat-ul-Kursi parhein, daein karvat son."
    ),
    ("negative", "nafsani"): (
        "Yeh khwab zyada tar aap ke zehni dabao, khauf ya pareshani ko dikhata hai. "
        "Apne masail par ghor karein aur zarurat ho to kisi bharosemand se baat karein."
    ),
    ("neutral", "rehmani"): (
        "Is khwab mein iman aur zindagi ke faislon par ghor karne ki nishani hai. "
        "Allah se hidayat maangein aur apne din ka hisaab rakhein."
    ),
    ("neutral", "shaitani"): (
        "Khwab mein chupi hui pareshani ho sakti hai. Zyada dhikr, namaz aur Quran ki tilawat "
        "se dil ko sukoon milta hai — in par amal karein."
    ),
    ("neutral", "nafsani"): (
        "Yeh khwab aam tor par roz marra ke khayalat aur zehni halat ko dikhata hai. "
        "Neend, khana aur din ki routine theek rakhein."
    ),
}


def _normalize(text):
    text = str(text).lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _count_matches(text, word_set):
    words = set(_normalize(text).split())
    count = len(words & word_set)
    for phrase in word_set:
        if " " in phrase and phrase in text:
            count += 1
    return count


def analyze_dream_keywords(text, dream_type=None):
    """Keyword-based analysis with English + Roman Urdu support."""
    clean = _normalize(text)
    pos = _count_matches(clean, POSITIVE_WORDS)
    neg = _count_matches(clean, NEGATIVE_WORDS)
    reh = _count_matches(clean, REHMANI_WORDS)
    sha = _count_matches(clean, SHAITANI_WORDS)

    if dream_type and dream_type in DREAM_TYPE_HINTS:
        type_sent, type_isl = DREAM_TYPE_HINTS[dream_type]
        if pos == neg:
            pos, neg = (2, 0) if type_sent == "positive" else (0, 2)
        if reh == sha:
            reh, sha = (2, 0) if type_isl == "rehmani" else (0, 2)

    if pos > neg:
        sentiment = "positive"
    elif neg > pos:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    if reh > sha:
        islamic = "rehmani"
    elif sha > reh:
        islamic = "shaitani"
    else:
        islamic = "nafsani"

    meaning = MEANINGS.get((sentiment, islamic), MEANINGS[("neutral", "nafsani")])

    matched_pos = [w for w in POSITIVE_WORDS if w in clean and " " not in w][:3]
    matched_neg = [w for w in NEGATIVE_WORDS if w in clean and " " not in w][:3]
    if matched_pos or matched_neg:
        hints = []
        if matched_pos:
            hints.append("positive themes: " + ", ".join(matched_pos))
        if matched_neg:
            hints.append("negative themes: " + ", ".join(matched_neg))
        meaning += " (" + "; ".join(hints) + ")"

    return sentiment, islamic, meaning


def _extract_json(raw):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[^{}]*\"sentiment\"[^{}]*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    sentiment_m = re.search(r'"sentiment"\s*:\s*"(positive|negative|neutral)"', raw, re.I)
    islamic_m = re.search(r'"islamic"\s*:\s*"(rehmani|shaitani|nafsani)"', raw, re.I)
    meaning_m = re.search(r'"meaning"\s*:\s*"((?:[^"\\]|\\.)*)"', raw, re.S)
    if sentiment_m:
        return {
            "sentiment": sentiment_m.group(1).lower(),
            "islamic": islamic_m.group(1).lower() if islamic_m else "nafsani",
            "meaning": meaning_m.group(1) if meaning_m else "",
        }
    return None


def analyze_dream_with_gemini(text, api_key, dream_type=None):
    prompt = (
        "You are an Islamic dream interpreter. Return ONLY valid JSON (no markdown).\n"
        f'Dream: "{text}"\n'
        "Keys: sentiment (positive|negative|neutral), islamic (rehmani|shaitani|nafsani), "
        "meaning (2-3 sentences in simple Urdu/English mix, specific to THIS dream's symbols).\n"
        "Classify sentiment from emotional tone, not only pleasant imagery."
    )

    generation_config = {
        "maxOutputTokens": 1024,
        "temperature": 0.4,
        "responseMimeType": "application/json",
    }

    endpoints = [
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}",
        f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent?key={api_key}",
    ]

    for url in endpoints:
        try:
            resp = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": generation_config,
                },
                timeout=25,
            )
            if resp.status_code != 200:
                print(f"Gemini dream API {resp.status_code}: {resp.text[:300]}")
                continue

            result = resp.json()
            candidates = result.get("candidates") or []
            if not candidates:
                continue

            raw = candidates[0]["content"]["parts"][0]["text"]
            parsed = _extract_json(raw)
            if not parsed:
                print(f"Gemini JSON parse failed, raw preview: {raw[:200]}")
                continue

            sentiment = str(parsed.get("sentiment", "neutral")).lower()
            islamic = str(parsed.get("islamic", "nafsani")).lower()
            meaning = str(parsed.get("meaning", "")).strip()

            if sentiment not in ("positive", "negative", "neutral"):
                sentiment = "neutral"
            if islamic not in ("rehmani", "shaitani", "nafsani"):
                islamic = "nafsani"
            if not meaning:
                _, _, meaning = analyze_dream_keywords(text, dream_type)

            return sentiment, islamic, meaning

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            continue
        except (KeyError, IndexError) as e:
            print(f"Gemini response structure error: {e}")
            continue

    return None


def analyze_dream(text, api_key=None, dream_type=None, sentiment_model=None, islamic_model=None):
    """Full pipeline: optional ML → Gemini → keyword fallback."""
    if sentiment_model and islamic_model:
        try:
            from utils.text_cleaning import clean_text

            clean = clean_text(text)
            if clean:
                sent_pred = sentiment_model.predict([clean])[0]
                isl_pred = islamic_model.predict([clean])[0]
                sentiment = str(sent_pred).lower()
                islamic = str(isl_pred).lower()
                if sentiment in ("positive", "negative", "neutral") and islamic in (
                    "rehmani",
                    "shaitani",
                    "nafsani",
                ):
                    _, _, meaning = analyze_dream_keywords(text, dream_type)
                    return sentiment, islamic, meaning
        except Exception as e:
            print(f"ML model prediction failed: {e}")

    key = (api_key or os.environ.get("GEMINI_API_KEY", "")).strip()
    if key:
        gemini_result = analyze_dream_with_gemini(text, key, dream_type)
        if gemini_result:
            return gemini_result
        print("Gemini unavailable — using keyword analysis")

    return analyze_dream_keywords(text, dream_type)
