import json
import re
import os
import requests

from utils.dream_dataset import (
    get_dataset,
    aggregate_class_probabilities,
    meaning_from_training_label,
    normalize_sentiment,
    normalize_islamic,
    simplify_islamic_from_mixed,
)

# ─── Keyword weights (word → score) ───────────────────────────────────────────
POSITIVE_WEIGHTS = {
    "happy": 2, "joy": 2, "peace": 2, "peaceful": 2, "beautiful": 2, "blessed": 2,
    "blessing": 2, "love": 2, "smile": 1, "calm": 2, "safe": 2, "success": 2,
    "flying": 1, "garden": 2, "paradise": 2, "green": 1, "flowers": 1, "rainbow": 2,
    "khushi": 3, "sukoon": 3, "aman": 2, "kamyabi": 2, "umeed": 2, "acha": 1, "accha": 1,
}

NEGATIVE_WEIGHTS = {
    "scary": 3, "scared": 3, "terrified": 3, "terrifying": 5, "horror": 3, "horrifying": 5,
    "horrific": 5, "nightmare": 4, "afraid": 2, "fear": 2, "frightening": 4, "petrified": 4,
    "dark": 2, "darkness": 2, "monster": 3, "death": 3, "dead": 3, "die": 2, "dying": 2,
    "snake": 3, "snakes": 3, "fire": 2, "burning": 2, "falling": 2, "chasing": 2, "chase": 2,
    "crying": 2, "blood": 3, "demon": 3, "demons": 3, "evil": 3, "drowning": 3,
    "hurt": 2, "pain": 2, "war": 2, "fight": 2, "lost": 1, "trapped": 2, "hell": 3,
    "devil": 3, "satan": 3, "ghost": 2, "terror": 3, "wound": 2, "killed": 3, "kill": 3,
    "attack": 2, "attacked": 2, "decapitat": 6, "behead": 6, "excrement": 5, "feces": 5,
    "filth": 4, "foul": 4, "disgusting": 4, "locust": 3, "locusts": 3, "swarm": 2,
    "coffin": 3, "funeral": 3, "whisper": 2, "crawling": 2, "shadow": 2, "colder": 2,
    "footsteps": 2, "unable": 1, "paralyzed": 3, "stole": 2, "stealing": 2, "cut": 2,
    "dar": 3, "darr": 3, "khauf": 3, "andhera": 2, "saanp": 3, "aag": 2, "larai": 2,
    "khoon": 3, "maut": 3, "mar": 2, "rona": 2, "pareshan": 2, "azab": 2, "dukh": 2,
    "ghum": 2, "bura": 2, "kharab": 2, "dhamki": 2, "takleef": 2, "zalim": 2,
}

REHMANI_WEIGHTS = {
    "allah": 3, "prophet": 3, "muhammad": 3, "quran": 3, "mosque": 2, "masjid": 3,
    "namaz": 3, "prayer": 2, "pray": 2, "dua": 2, "angel": 2, "angels": 2, "jannah": 3,
    "heaven": 2, "kaaba": 3, "hajj": 2, "umrah": 2, "hadith": 2, "sunnah": 2,
    "ramadan": 2, "iman": 2, "faith": 1, "rehmat": 2, "barkat": 2, "farishta": 3,
    "prophetic": 3, "wudu": 2, "surah": 2, "ayat": 2,
}

SHAITANI_WEIGHTS = {
    "devil": 3, "satan": 3, "shaitan": 3, "demon": 3, "demons": 3, "evil": 2,
    "sin": 1, "haram": 2, "magic": 2, "witch": 2, "hell": 3, "jahannam": 3,
    "curse": 2, "jinn": 3, "ghost": 2, "nightmare": 2, "shaitani": 3, "azab": 2,
    "sorcery": 2, "whisper": 2, "temptation": 2, "black magic": 3,
}

DREAM_TYPE_HINTS = {
    "nightmare": {"sentiment": "negative", "islamic": "shaitani", "boost": 4},
    "prophetic": {"sentiment": "positive", "islamic": "rehmani", "boost": 4},
}

SYMBOL_INTERPRETATIONS = [
    (r"\b(snake|saanp|snakes)\b", "Saanp (Ibn Sirin ke mutabiq) aksar dushman, chhupa hua khatra ya gham dikhata hai."),
    (r"\b(water|pani|river|sea|ocean|darya)\b", "Pani saf ho to rehmat, ganda ho to pareshani ki alamat ho sakta hai."),
    (r"\b(fire|aag|burning|flame)\b", "Aag fitna, gussa ya azmaish ki nishani ho sakti hai — sabr aur istighfar karein."),
    (r"\b(fall|falling|girna|girta)\b", "Girna izzat ya maqam mein kami ya zindagi mein tabdeeli dikha sakta hai."),
    (r"\b(fly|flying|udna|urta)\b", "Udna aksar azadi, izzat ya buland maqam ki taraf ishara hai."),
    (r"\b(death|maut|dead|mar)\b", "Maut ka khwab aksar zindagi mein bari tabdeeli ya kisi rishtay ka khatma dikha sakta hai."),
    (r"\b(mosque|masjid|namaz|prayer)\b", "Masjid/namaz deeni ya roohani hidayat ki nishani hai."),
    (r"\b(dog|kutta)\b", "Kutta dushman ya nafs ki kamzori dikha sakta hai."),
    (r"\b(cat|billi)\b", "Billi ghar ki larki ya chhupi hui baat ki alamat ho sakti hai."),
    (r"\b(baby|bacha|child)\b", "Bacha nayi zimmedari ya khushi ki khabar ho sakta hai."),
    (r"\b(teeth|tooth|dant).*(fell|fall|falling|gir)\b", "Dant girna (Ibn Sirin) aksar gham, nuqsan ya khandan mein pareshani dikha sakta hai."),
    (r"\b(teeth|dant)\b", "Dant khwab mein izzat, rishtay ya sehat se mutaliq ho sakta hai."),
    (r"\b(prophet|muhammad)\b", "Nabi ﷺ ka zikr khwab mein hidayat dikha sakta hai — lekin agar khwab khaufnaak ho to Shaitan ki waswasay se bachein."),
    (r"\b(excrement|feces|filth|foul)\b", "Gandagi/najasat aksar haram kamai, gunaah ya buri soch ki alamat ho sakti hai."),
    (r"\b(locust|locusts|swarm)\b", "Tiddi dal fitna, nuqsan ya qehat ki taraf ishara kar sakti hai."),
    (r"\b(chase|chasing|bhag|bhaag)\b", "Kisi ka peecha karna masla se bachna ya dushman se bachne ki koshish dikha sakta hai."),
    (r"\b(dark|andhera|darkness)\b", "Andhera gum, confusion ya shaitani waswasay ki taraf ho sakta hai."),
    (r"\b(angel|farishta|angels)\b", "Farishta bohat achi khabar aur Allah ki rehmat dikha sakta hai."),
    (r"\b(shaitan|devil|satan|demon)\b", "Shaitan/satan deeni azmaish ya hifazat ki zarurat dikha sakta hai."),
    (r"\b(blood|khoon)\b", "Khoon gunaah, takleef ya nuqsan ki alamat ho sakta hai."),
    (r"\b(money|paisa|gold|sona)\b", "Maal dunya ki fikar ya imtihaan dikha sakta hai — halal kamai par ghor karein."),
    (r"\b(road|sarak|rasta|path)\b", "Rasta zindagi ka rukh dikha sakta hai — seedha ho to asani, kharab ho to mushkil."),
    (r"\b(rain|barish)\b", "Barish rehmat aur Allah ki raham ki nishani ho sakti hai."),
    (r"\b(mountain|pahar)\b", "Pahar mushkil kaam ya izzat dikha sakta hai."),
]

BASE_MEANINGS = {
    ("positive", "rehmani"): "Bohat acha roohani khwab — Allah ki rehmat aur hidayat ki nishani.",
    ("positive", "shaitani"): "Zahiri khushi hai lekin chupi hui pareshani ho sakti hai — hifazat ki dua karein.",
    ("positive", "nafsani"): "Khushi aur umeed ka khwab — dil ki halat achi hai.",
    ("negative", "rehmani"): "Roohani ishara/tobah ka pegham — namaz aur istighfar barhayein.",
    ("negative", "shaitani"): "Khaufnaak khwab — shaitan se panah maangein, teen Qul parhein.",
    ("negative", "nafsani"): "Zehni dabao ya khauf — apne masail hal karein, kisi se baat karein.",
    ("neutral", "rehmani"): "Zindagi ke faislon par ghor karne ka ishara.",
    ("neutral", "shaitani"): "Chhupi hui pareshani — zyada dhikr karein.",
    ("neutral", "nafsani"): "Roz marra ke khayalat — routine theek rakhein.",
}


def _normalize(text):
    text = str(text).lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def _is_sacred_in_negative_context(text):
    """Prophet/Allah in violent or horrifying dream — NOT rehmani."""
    clean = _normalize(text)
    if not re.search(r"\b(prophet|muhammad|allah|quran|masjid|kaaba|namaz|adhan)\b", clean):
        return False
    negative_ctx = (
        r"(decapitat|behead|killing|killed|kill|murder|blood|horrif|terrifying|"
        r"terrified|attack|harm|violence|insult|sin|nightmare|dark|fear|demon|evil|shaitan)"
    )
    return bool(re.search(negative_ctx, clean))


def _score_weighted(text, weights, skip_if_sacred=False):
    if skip_if_sacred and weights is REHMANI_WEIGHTS and _is_sacred_in_negative_context(text):
        return 0.0
    clean = _normalize(text)
    words = set(clean.split())
    score = 0.0
    for word, w in weights.items():
        if " " in word:
            if word in clean:
                score += w
        elif word in words or word in clean:
            score += w
    return score


def apply_critical_overrides(text):
    """Hard rules for obvious misclassifications (horror, sacred disrespect, etc.)."""
    clean = _normalize(text)

    if re.search(r"\b(horrifying|horrific|terrifying|petrified|nightmare)\b", clean):
        if not re.search(r"\b(peace|happy|joy|blessed|jannah|beautiful)\b", clean):
            isl = "shaitani" if re.search(
                r"\b(demon|devil|shaitan|shadow|whisper|crawling|darkness|evil)\b", clean
            ) else "nafsani"
            meaning = _build_meaning(text, "negative", isl)
            return "negative", isl, meaning

    if re.search(r"\b(teeth|tooth)\b", clean) and re.search(
        r"\b(fell|fall|falling|caught|mouth)\b", clean
    ):
        isl = "shaitani" if re.search(r"\b(terrifying|scary|horrif|fear)\b", clean) else "nafsani"
        sent = "negative" if re.search(r"\b(terrifying|scary|horrif|fear)\b", clean) else "neutral"
        if sent == "neutral" and re.search(r"\b(terrifying|scary|horrif)\b", clean):
            sent = "negative"
        meaning = (
            "Dant girna Ibn Sirin ke mutabiq gham, nuqsan ya izzat ki kami dikha sakta hai. "
            + _build_meaning(text, sent, isl).split(". ", 1)[-1]
        )
        return sent, isl, meaning

    if re.search(r"\b(excrement|feces|faeces|sewage|filth|foul)\b", clean):
        return (
            "negative",
            "shaitani",
            "Najasat/gandagi aksar haram kamai, gunaah ya Shaitani asar dikha sakti hai — "
            "tawba, halal rozgar aur paak zindagi par amal karein.",
        )

    if re.search(r"\b(adhan|azan|calling)\b", clean) and re.search(
        r"\b(prayer|namaz|mosque|masjid)\b", clean
    ):
        if not re.search(r"\b(horrif|terrifying|dark|fear|blood|kill)\b", clean):
            return (
                "positive",
                "rehmani",
                "Adhan/namaz ka khwab bohat acha — hidayat aur deen ki taraf bulawa ho sakta hai.",
            )

    return None


def _extract_symbols(text):
    clean = _normalize(text)
    found = []
    for pattern, meaning in SYMBOL_INTERPRETATIONS:
        if re.search(pattern, clean):
            found.append(meaning)
    return found[:3]


def _build_meaning(text, sentiment, islamic):
    symbols = _extract_symbols(text)
    base = BASE_MEANINGS.get((sentiment, islamic), BASE_MEANINGS[("neutral", "nafsani")])
    parts = [base]
    if symbols:
        parts.append(" ".join(symbols))
    snippet = text.strip()[:80]
    if snippet:
        parts.append(f'Aap ne likha: "{snippet}{"..." if len(text) > 80 else ""}" — is ke alamat par ghor karein.')
    return " ".join(parts)


def _apply_islamic_rules(sentiment, pos_s, neg_s, reh_s, sha_s, text=None):
    """Negative dreams should not default to rehmani without strong spiritual context."""
    if sentiment == "negative":
        if sha_s >= 1 or neg_s >= 4:
            return "shaitani"
        if reh_s >= 2 and sha_s == 0:
            return "rehmani"
        return "nafsani"
    if sentiment == "positive":
        if reh_s >= 2:
            return "rehmani"
        if sha_s >= 2:
            return "shaitani"
        return "nafsani"
    if reh_s > sha_s + 1:
        return "rehmani"
    if sha_s > reh_s + 1:
        return "shaitani"
    return "nafsani"


def _apply_sentiment_rules(pos_s, neg_s, dream_type=None, text=None):
    if dream_type == "nightmare":
        neg_s += 4
    if dream_type == "prophetic":
        pos_s += 4
    if text:
        clean = _normalize(text)
        if re.search(r"\b(horrifying|terrifying|horrific|petrified)\b", clean):
            neg_s += 5
        if re.search(r"\b(dark|death|blood|kill|demon|shadow|whisper|coffin|funeral)\b", clean):
            neg_s += 2

    if pos_s >= neg_s + 2:
        return "positive"
    if neg_s >= pos_s + 1:
        return "negative"
    if neg_s > pos_s:
        return "negative"
    if pos_s > neg_s:
        return "positive"
    return "neutral"


def analyze_dream_keywords(text, dream_type=None):
    override = apply_critical_overrides(text)
    if override:
        return override

    pos_s = _score_weighted(text, POSITIVE_WEIGHTS)
    neg_s = _score_weighted(text, NEGATIVE_WEIGHTS)
    reh_s = _score_weighted(text, REHMANI_WEIGHTS, skip_if_sacred=True)
    sha_s = _score_weighted(text, SHAITANI_WEIGHTS)

    if dream_type and dream_type in DREAM_TYPE_HINTS:
        hint = DREAM_TYPE_HINTS[dream_type]
        boost = hint["boost"]
        if hint["sentiment"] == "negative":
            neg_s += boost
        else:
            pos_s += boost
        if hint["islamic"] == "shaitani":
            sha_s += boost
        else:
            reh_s += boost

    sentiment = _apply_sentiment_rules(pos_s, neg_s, dream_type, text)
    islamic = _apply_islamic_rules(sentiment, pos_s, neg_s, reh_s, sha_s, text)
    meaning = _build_meaning(text, sentiment, islamic)
    return sentiment, islamic, meaning


def _get_ml_pair(model_tuple):
    """Models saved as (classifier, vectorizer)."""
    if not model_tuple or len(model_tuple) != 2:
        return None, None
    a, b = model_tuple[0], model_tuple[1]
    if hasattr(b, "transform"):
        return a, b
    if hasattr(a, "transform"):
        return b, a
    return None, None


def analyze_with_dataset_csv(text, sentiment_model=None):
    """Match dream to closest rows in training CSV."""
    vec = None
    if sentiment_model:
        _, vec = _get_ml_pair(sentiment_model)
    ds = get_dataset(vec)
    if not ds.loaded:
        return None

    matches = ds.find_similar(text, top_k=3)
    if not matches:
        return None

    best = matches[0]
    sentiments = [m["sentiment"] for m in matches if m.get("sentiment")]
    islamics = [m["islamic"] for m in matches if m.get("islamic")]

    sentiment = sentiments[0] if sentiments else "neutral"
    if len(set(sentiments)) > 1:
        from collections import Counter
        sentiment = Counter(sentiments).most_common(1)[0][0]

    islamic = islamics[0] if islamics else "nafsani"
    if len(set(islamics)) > 1:
        from collections import Counter
        islamic = Counter(islamics).most_common(1)[0][0]

    meanings = [m["meaning"] for m in matches if m.get("meaning")]
    if meanings:
        meaning = meanings[0]
        if len(matches) > 1:
            meaning += " (Milta julta dataset khwab: " + matches[1]["dream"][:60] + "...)"
    else:
        meaning = _build_meaning(text, sentiment, islamic)

    meaning = f"[Dataset: {os.path.basename(ds.source)} | match {best['similarity']:.0%}] {meaning}"
    return sentiment, islamic, meaning


def analyze_with_ml_models(text, sentiment_model, islamic_model, dream_type=None):
    """Primary path: ML models trained on your FYP dataset."""
    override = apply_critical_overrides(text)
    if override:
        s, i, m = override
        return s, i, "[Dataset rules] " + m

    clf_s, vec_s = _get_ml_pair(sentiment_model)
    clf_i, vec_i = _get_ml_pair(islamic_model)
    if not clf_s or not vec_s:
        return None

    sent, _, raw_sent, _ = aggregate_class_probabilities(clf_s, vec_s, text)

    raw_isl = None
    if clf_i and vec_i:
        _, isl, _, raw_isl = aggregate_class_probabilities(clf_i, vec_i, text)
    else:
        isl = "nafsani"

    pos_s = _score_weighted(text, POSITIVE_WEIGHTS)
    neg_s = _score_weighted(text, NEGATIVE_WEIGHTS)
    sha_s = _score_weighted(text, SHAITANI_WEIGHTS)
    kw_sent, kw_isl, _ = analyze_dream_keywords(text, dream_type)

    if dream_type == "nightmare":
        sent, isl = "negative", "shaitani"
    elif dream_type == "prophetic":
        sent, isl = "positive", "rehmani"
    else:
        if kw_sent == "negative" or neg_s >= 3:
            sent = kw_sent if kw_sent != "neutral" else "negative"
        elif kw_sent == "positive" and pos_s >= 3:
            sent = "positive"
        elif sent == "neutral" and kw_sent != "neutral":
            sent = kw_sent
        isl = kw_isl
        isl = simplify_islamic_from_mixed(raw_isl or isl, sent)
        if sent == "neutral" and neg_s >= 3:
            sent = "negative"
            isl = "shaitani" if sha_s >= 1 else "nafsani"

    meaning = meaning_from_training_label(raw_sent, raw_isl or isl, text)
    symbols = _extract_symbols(text)
    if symbols:
        meaning += " " + symbols[0]
    meaning = "[Trained dataset model] " + meaning

    return sent, isl, meaning


def _extract_json(raw):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
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
        "Islamic dream interpreter. Analyze ONLY this dream. Return JSON only.\n"
        f'Dream: "{text}"\n'
        "Rules:\n"
        "- scary/evil/chase/death/snake/blood → sentiment negative\n"
        "- peace/joy/mosque/angel/jannah → sentiment positive\n"
        "- negative scary dream → islamic shaitani or nafsani, NOT rehmani unless explicit divine warning\n"
        "- meaning: 2-3 sentences SPECIFIC to dream symbols (Urdu/English), mention Ibn Sirin style if relevant\n"
        '{"sentiment":"...","islamic":"...","meaning":"..."}'
    )
    endpoints = [
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}",
    ]
    for url in endpoints:
        try:
            resp = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "maxOutputTokens": 1024,
                        "temperature": 0.35,
                        "responseMimeType": "application/json",
                    },
                },
                timeout=25,
            )
            if resp.status_code != 200:
                continue
            candidates = resp.json().get("candidates") or []
            if not candidates:
                continue
            parsed = _extract_json(candidates[0]["content"]["parts"][0]["text"])
            if not parsed:
                continue

            sentiment = normalize_sentiment(parsed.get("sentiment")) or "neutral"
            islamic = normalize_islamic(parsed.get("islamic")) or "nafsani"
            if islamic == "mixed":
                islamic = simplify_islamic_from_mixed(parsed.get("islamic"), sentiment)
            meaning = str(parsed.get("meaning", "")).strip()

            if sentiment not in ("positive", "negative", "neutral"):
                sentiment = "neutral"
            if islamic not in ("rehmani", "shaitani", "nafsani"):
                islamic = "nafsani"

            if not meaning or len(meaning) < 40:
                meaning = _build_meaning(text, sentiment, islamic)

            return sentiment, islamic, meaning
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            continue
        except (KeyError, IndexError):
            continue
    return None


def analyze_dream(text, api_key=None, dream_type=None, sentiment_model=None, islamic_model=None):
    """
    Priority:
    1) Training CSV (dataset.csv) — closest dream match + meaning from dataset
    2) ML models trained on the same dataset
    3) Critical safety overrides
    4) Legacy keyword engine (fallback)
    5) Gemini API (optional)
    """
    from utils.legacy_dream_analyzer import analyze_dream_legacy

    # 1) Dataset CSV (primary)
    csv_result = analyze_with_dataset_csv(text, sentiment_model)
    if csv_result:
        return csv_result

    # 2) ML models from dataset training
    if sentiment_model and islamic_model:
        ml_result = analyze_with_ml_models(text, sentiment_model, islamic_model, dream_type)
        if ml_result:
            return ml_result

    override = apply_critical_overrides(text)
    if override:
        return override

    legacy = analyze_dream_legacy(text)
    pos = _score_weighted(text, POSITIVE_WEIGHTS)
    neg = _score_weighted(text, NEGATIVE_WEIGHTS)
    if legacy[0] != "neutral" or pos > 0 or neg > 0:
        return legacy

    key = (api_key or os.environ.get("GEMINI_API_KEY", "")).strip()
    if key:
        gemini_result = analyze_dream_with_gemini(text, key, dream_type)
        if gemini_result:
            return gemini_result

    return legacy
