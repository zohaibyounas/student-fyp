"""
Load Islamic dream training dataset (CSV) and match user dreams to closest entries.
Falls back to ML model labels when CSV is not present.
"""
import os
import re
import csv
import pickle
from pathlib import Path

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Where to look for the training CSV (first match wins)
DATASET_CANDIDATES = [
    os.environ.get("DREAM_DATASET_PATH", "").strip(),
    str(DATA_DIR / "dataset.csv"),
    str(DATA_DIR / "Dataset.csv"),
    str(DATA_DIR / "islamic_dream_dataset.csv"),
    str(DATA_DIR / "dream_dataset.csv"),
    str(DATA_DIR / "dreams.csv"),
    str(BASE_DIR / "__pycache__" / "data" / "dataset.csv"),
    str(BASE_DIR / "__pycache__" / "data" / "Dataset.csv"),
    str(BASE_DIR / "islamic_dream_dataset.csv"),
]

DREAM_COLS = ("dream", "dream_text", "text", "description", "dream description", "khwab")
SENTIMENT_COLS = (
    "sentiment", "sentiment_analysis", "mood", "emotion", "feeling",
    "label_sentiment", "sentiment_label",
)
ISLAMIC_COLS = (
    "islamic", "islamic_analysis", "islamic_type", "type", "category",
    "dream_type", "islamic_label", "classification",
)
MEANING_COLS = ("meaning", "interpretation", "tafsir", "explanation", "meaning_text", "dream_meaning")


class DreamDataset:
  def __init__(self):
    self.rows = []
    self._matrix = None
    self._vectorizer = None
    self.source = None

  @property
  def loaded(self):
    return len(self.rows) > 0

  def load(self, vectorizer=None):
    path = self._find_csv()
    if not path:
      return False
    self.rows = self._read_csv(path)
    self.source = path
    if vectorizer is not None and self.rows:
      texts = [r["dream"] for r in self.rows]
      self._vectorizer = vectorizer
      self._matrix = vectorizer.transform(texts)
    return self.loaded

  def _find_csv(self):
    for p in DATASET_CANDIDATES:
      if p and os.path.isfile(p):
        return p
    search_dirs = [
      DATA_DIR,
      BASE_DIR / "__pycache__" / "data",
      BASE_DIR,
    ]
    for folder in search_dirs:
      if folder.is_dir():
        csvs = sorted(folder.glob("*.csv"), key=lambda f: f.name.lower())
        for f in csvs:
          return str(f)
    return None

  def _pick_col(self, headers, candidates):
    lower = {h.lower().strip(): h for h in headers}
    for c in candidates:
      if c in lower:
        return lower[c]
    for h in headers:
      hl = h.lower().strip()
      for c in candidates:
        if c in hl or hl in c:
          return h
    return None

  def _read_csv(self, path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
      reader = csv.DictReader(f)
      if not reader.fieldnames:
        return rows
      dream_col = self._pick_col(reader.fieldnames, DREAM_COLS)
      sent_col = self._pick_col(reader.fieldnames, SENTIMENT_COLS)
      isl_col = self._pick_col(reader.fieldnames, ISLAMIC_COLS)
      mean_col = self._pick_col(reader.fieldnames, MEANING_COLS)
      if not dream_col:
        return rows
      for row in reader:
        dream = (row.get(dream_col) or "").strip()
        if len(dream) < 5:
          continue
        rows.append({
          "dream": dream,
          "sentiment": normalize_sentiment(row.get(sent_col, "") if sent_col else ""),
          "islamic": normalize_islamic(row.get(isl_col, "") if isl_col else ""),
          "meaning": (row.get(mean_col, "") if mean_col else "").strip(),
        })
    return rows

  def find_similar(self, text, top_k=3):
    if not self.loaded:
      return []
    if self._matrix is not None and self._vectorizer is not None:
      q = self._vectorizer.transform([str(text).lower()])
      sims = cosine_similarity(q, self._matrix)[0]
      idx = np.argsort(sims)[::-1][:top_k]
      out = []
      for i in idx:
        if sims[i] < 0.08:
          continue
        r = dict(self.rows[i])
        r["similarity"] = float(sims[i])
        out.append(r)
      return out
    return self._find_similar_text(text, top_k)

  def _find_similar_text(self, text, top_k=3):
    """Fallback when ML vectorizer is unavailable — still uses dataset rows."""
    from difflib import SequenceMatcher
    text_l = str(text).lower()
    scored = []
    for i, row in enumerate(self.rows):
      sim = SequenceMatcher(None, text_l, row["dream"].lower()).ratio()
      if sim >= 0.12:
        scored.append((sim, i))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for sim, i in scored[:top_k]:
      r = dict(self.rows[i])
      r["similarity"] = float(sim)
      out.append(r)
    return out


# ─── Label normalization (matches training data labels in .pkl) ─────────────

def normalize_sentiment(label):
  if not label:
    return None
  l = str(label).lower().strip()
  if "negative" in l and "positive" not in l.split("/")[0].strip():
    return "negative"
  if "positive" in l and "negative" not in l.split()[0]:
    return "positive"
  if "neutral" in l:
    return "neutral"
  if l in ("negative", "neg"):
    return "negative"
  if l in ("positive", "pos"):
    return "positive"
  if l in ("neutral",):
    return "neutral"
  if "negative" in l and "positive" in l:
    return "neutral"
  if "negative" in l:
    return "negative"
  if "positive" in l:
    return "positive"
  return "neutral"


def normalize_islamic(label):
  if not label:
    return None
  l = str(label).lower().strip()
  if "rahmani" in l or "rehmani" in l:
    if "shaitani" in l and "/" in l:
      return "mixed"
    return "rehmani"
  if "shaitani" in l or "shaytan" in l:
    return "shaitani"
  if "nafsani" in l or "nafsi" in l:
    return "nafsani"
  return None


def simplify_islamic_from_mixed(raw_label, sentiment):
  """Pick rehmani/shaitani/nafsani when training label is compound."""
  isl = normalize_islamic(raw_label)
  if isl and isl != "mixed":
    return isl
  l = str(raw_label).lower()
  if sentiment == "negative":
    if "shaitani" in l:
      return "shaitani"
    return "nafsani"
  if sentiment == "positive":
    if "rahmani" in l or "rehmani" in l:
      return "rehmani"
    return "nafsani"
  return "nafsani"


def meaning_from_training_label(raw_sentiment, raw_islamic, dream_text):
  """Turn dataset / model class label into user-facing meaning."""
  sent = normalize_sentiment(raw_sentiment) or "neutral"
  raw_i = str(raw_islamic or "")
  isl = simplify_islamic_from_mixed(raw_i, sent)

  parts = []
  if "/" in raw_i or "(" in raw_i:
    parts.append(
      f"Dataset ke mutabiq yeh khwab '{raw_i.strip()}' category mein aata hai — "
      f"apne khwab ki halat (achi ya buri) se pehla hissa dekhein."
    )
  else:
    parts.append(f"Dataset classification: {sent.capitalize()} / {isl.capitalize()}.")

  label_hints = {
    "rehmani (clean) / shaitani (dirty)": "Saf cheez Rahmani, gandi cheez Shaitani alamat.",
    "rahmani (clean) / shaitani (dirty)": "Saf cheez Rahmani, gandi cheez Shaitani alamat.",
    "rahmani (lit) / shaitani (extinguished)": "Roshni/Rahmani barkat; bujhna Shaitani pareshani.",
    "shaitani (blind) / rahmani (guiding)": "Andha hona gum; rasta dikhana hidayat.",
    "nafsani / shaitani": "Yeh zyada tar nafsani ya Shaitani asar dikha sakta hai.",
  }
  key = raw_i.lower().strip()
  for pattern, hint in label_hints.items():
    if pattern in key:
      parts.append(hint)
      break

  snippet = dream_text.strip()[:70]
  if snippet:
    parts.append(f'Aap ka khwab: "{snippet}{"..." if len(dream_text) > 70 else ""}"')
  return " ".join(parts)


def aggregate_class_probabilities(clf, vec, text):
  """Map many training labels → positive/negative/neutral and rehmani/shaitani/nafsani."""
  X = vec.transform([str(text).lower()])
  if not hasattr(clf, "predict_proba"):
    raw_s = clf.predict(X)[0]
    return normalize_sentiment(raw_s), None, raw_s, None

  probs = clf.predict_proba(X)[0]
  classes = [str(c) for c in clf.classes_]

  sent_scores = {"positive": 0.0, "negative": 0.0, "neutral": 0.0}
  isl_scores = {"rehmani": 0.0, "shaitani": 0.0, "nafsani": 0.0}

  raw_sent = classes[int(np.argmax(probs))]
  raw_isl = None

  for cls, p in zip(classes, probs):
    cl = cls.lower()
    if any(x in cl for x in ("positive", "negative", "neutral")):
      if "negative" in cl and "positive" in cl:
        sent_scores["neutral"] += p
      elif "negative" in cl:
        sent_scores["negative"] += p
      elif "positive" in cl:
        sent_scores["positive"] += p
      elif "neutral" in cl:
        sent_scores["neutral"] += p
    if any(x in cl for x in ("rahmani", "rehmani", "shaitani", "nafsani")):
      if "rahmani" in cl or "rehmani" in cl:
        isl_scores["rehmani"] += p
      if "shaitani" in cl:
        isl_scores["shaitani"] += p
      if "nafsani" in cl:
        isl_scores["nafsani"] += p
      if raw_isl is None or p > 0.1:
        if p == max(probs):
          raw_isl = cls

  sentiment = max(sent_scores, key=sent_scores.get)
  islamic = max(isl_scores, key=isl_scores.get) if max(isl_scores.values()) > 0 else "nafsani"

  return sentiment, islamic, raw_sent, raw_isl or classes[int(np.argmax(probs))]


_dataset_cache = None


def get_dataset(vectorizer=None, reload=False):
  global _dataset_cache
  if reload:
    _dataset_cache = None
  if _dataset_cache is None:
    _dataset_cache = DreamDataset()
    _dataset_cache.load(vectorizer)
  elif vectorizer is not None and _dataset_cache._matrix is None and _dataset_cache.loaded:
    _dataset_cache.load(vectorizer)
  return _dataset_cache
