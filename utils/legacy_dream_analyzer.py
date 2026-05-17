"""
Legacy dream analyzer — same logic as original Islamic Dream Analyzer.html
(client-side keyword engine). Used as primary analyzer for accurate results.
"""
import re

POSITIVE_WORDS = [
    "happy", "beautiful", "peace", "peaceful", "angel", "success", "win", "love", "heaven",
    "joy", "flying", "smiling", "laugh", "laughter", "bless", "blessing", "light", "bright",
    "flowers", "garden", "paradise", "reward", "victory", "achievement", "achieving",
    "smile", "happiness", "calm", "serene", "beauty", "kindness", "generous", "generosity",
    "helping", "helped", "save", "saved", "rescued", "gift", "prize", "winner", "winning",
    "wealth", "rich", "money", "gold", "silver", "jewel", "jewels", "treasure",
    "successful", "progress", "improve", "improving", "growth", "growing", "healthy", "health",
    "clear", "clean", "pure", "purity", "truth", "true", "honest", "honesty", "good", "goodness",
    "positive", "optimistic", "hope", "hopeful", "faith", "faithful", "trust", "trusting",
    "friend", "friends", "family", "mother", "father", "child", "children", "baby", "babies",
    "wedding", "marriage", "married", "bride", "groom", "celebrate", "celebration", "party",
    "food", "eating", "drinking", "water", "river", "lake", "ocean", "sea", "mountain", "mountains",
    "forest", "trees", "green", "greenery", "bird", "birds", "butterfly", "butterflies", "flower",
    "sun", "sunshine", "moon", "stars", "star", "sky", "blue", "white", "cloud", "clouds",
    "khushi", "sukoon", "aman", "kamyabi",
]

NEGATIVE_WORDS = [
    "scary", "scared", "fear", "fearful", "dark", "darkness", "monster", "monsters", "devil",
    "death", "dead", "dying", "hell", "lost", "lose", "losing", "falling", "fell", "fall",
    "chasing", "chased", "running", "ran", "fighting", "fight", "fought", "crying", "cry",
    "sad", "sadness", "pain", "painful", "hurt", "hurting", "blood", "bleeding", "danger",
    "dangerous", "attack", "attacked", "snake", "snakes", "spider", "spiders", "ghost", "ghosts",
    "demon", "demons", "evil", "trapped", "trap", "drowning", "drown", "fire", "burning", "burn",
    "terror", "horror", "nightmare", "frightening", "frightened", "anxious", "anxiety",
    "worried", "worry", "stress", "stressed", "tension", "tense", "angry", "anger", "mad",
    "frustrated", "frustration", "confused", "confusion", "fail", "failed", "failure",
    "broken", "break", "breaking", "sick", "sickness", "ill", "illness", "disease",
    "poison", "poisonous", "toxic", "accident", "crash", "crashed", "police", "thief",
    "steal", "stolen", "rob", "robbed", "gun", "weapon", "knife", "sword", "war", "battle",
    "enemy", "enemies", "hate", "hatred", "jealous", "jealousy", "envy", "envious",
    "lonely", "loneliness", "alone", "abandoned", "abandon", "reject", "rejected", "rejection",
    "kill", "killed", "killing", "murder", "murdered", "die", "died", "horrifying", "terrifying",
    "terrified", "decapitat", "behead", "excrement", "feces", "foul", "filth",
    "dar", "darr", "khauf", "saanp", "maut", "khoon", "pareshan",
]

REHMANI_WORDS = [
    "prayer", "praying", "prayed", "mosque", "masjid", "quran", "koran", "prophet", "muhammad",
    "allah", "god", "angel", "angels", "light", "peace", "heaven", "jannah", "paradise",
    "bless", "blessing", "blessings", "guidance", "guided", "mercy", "merciful", "forgiveness",
    "forgive", "forgiven", "iman", "faith", "belief", "believer", "muslim", "islam", "islamic",
    "charity", "charitable", "zakat", "sadaqah", "kindness", "kind", "truth", "true",
    "patience", "patient", "gratitude", "thankful", "thanks", "thank", "grateful", "pious",
    "righteous", "virtue", "virtuous", "clean", "pure", "purity", "wudu", "fasting", "fast",
    "ramadan", "hajj", "umrah", "pilgrimage", "kaaba", "mecca", "medina", "imam", "scholar",
    "hadith", "sunna", "sunnah", "spiritual", "spirituality", "adhan", "azan", "namaz", "dua",
]

SHAITANI_WORDS = [
    "devil", "devils", "satan", "shaitan", "shaytan", "demon", "demons", "evil", "sin", "sins",
    "sinful", "darkness", "dark", "fire", "hell", "jahannam", "temptation", "tempt", "tempted",
    "witch", "witches", "magic", "sorcery", "sorcerer", "haram", "forbidden", "prohibited",
    "lying", "lie", "liar", "cheating", "cheat", "stealing", "steal", "thief", "thieves",
    "anger", "angry", "hatred", "hate", "jealousy", "jealous", "envy", "envious", "pride", "proud",
    "arrogant", "arrogance", "greed", "greedy", "selfish", "selfishness", "hypocrite", "hypocrisy",
    "disbelief", "disbeliever", "kafir", "idol", "idols", "idolatry", "witchcraft", "black magic",
    "satanic", "demonic", "possessed", "possession", "curse", "cursed", "damn", "damned",
    "hellfire", "punishment", "punish", "punished", "torment", "tormented", "torture", "tortured",
    "suffering", "suffer", "suffered", "agony", "agonizing", "shaitani", "jinn",
]

MEANINGS = {
    ("positive", "rehmani"): (
        "🌿 This is a very positive and spiritually significant dream! It indicates divine "
        "blessings, success, and spiritual growth in your life. Such dreams are considered good "
        "omens in Islamic tradition."
    ),
    ("positive", "shaitani"): (
        "⚠️ This dream appears positive but may contain subtle negative influences. Be cautious "
        "of temptations appearing as good things. Seek protection through prayers and good deeds."
    ),
    ("positive", "nafsani"): (
        "💭 This positive dream reflects your inner desires, hopes, and aspirations. It shows "
        "optimism for the future and indicates personal growth and satisfaction."
    ),
    ("negative", "rehmani"): (
        "🕌 This negative dream may be a spiritual warning or test from Allah. It suggests you "
        "need to strengthen your faith, increase prayers, and seek protection from negative influences."
    ),
    ("negative", "shaitani"): (
        "🔥 This is a warning dream! It indicates strong negative influences or shaitani whispers. "
        "Seek protection through prayers, recite Ayat-ul-Kursi and the last three Surahs of Quran before sleeping."
    ),
    ("negative", "nafsani"): (
        "😔 This negative dream reflects your fears, anxieties, stress, or unresolved issues in "
        "your waking life. It may indicate the need for emotional healing and stress management."
    ),
    ("neutral", "rehmani"): (
        "📖 This dream has spiritual elements. It reflects your connection with faith and may "
        "contain subtle guidance or reminders about your spiritual duties."
    ),
    ("neutral", "shaitani"): (
        "👁️ This neutral dream may contain hidden negative influences. Stay alert to your "
        "surroundings and maintain your spiritual practices for protection."
    ),
    ("neutral", "nafsani"): (
        "🧠 This dream reflects your daily thoughts, experiences, and subconscious mind. "
        "It's a normal reflection of your mental processes and doesn't carry significant spiritual meaning."
    ),
}


def analyze_dream_legacy(text):
    """Original keyword-based analyzer (matches old HTML behavior)."""
    text_lower = str(text).lower()

    positive_count = sum(1 for w in POSITIVE_WORDS if w in text_lower)
    negative_count = sum(1 for w in NEGATIVE_WORDS if w in text_lower)
    rehmani_count = sum(1 for w in REHMANI_WORDS if w in text_lower)
    shaitani_count = sum(1 for w in SHAITANI_WORDS if w in text_lower)

    if positive_count > negative_count:
        sentiment = "positive"
    elif negative_count > positive_count:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    if rehmani_count > shaitani_count:
        islamic = "rehmani"
    elif shaitani_count > rehmani_count:
        islamic = "shaitani"
    else:
        islamic = "nafsani"

    meaning = MEANINGS.get((sentiment, islamic), MEANINGS[("neutral", "nafsani")])
    meaning += _stats_footer(positive_count, negative_count, rehmani_count, shaitani_count)
    return sentiment, islamic, meaning


def _stats_footer(pos, neg, reh, sha):
    if pos or neg or reh or sha:
        return (
            f'<br><br><small style="color: #666; font-size: 12px;">'
            f"Analysis based on: {pos} positive, {neg} negative, "
            f"{reh} spiritual, {sha} negative-spiritual keywords found.</small>"
        )
    return ""
