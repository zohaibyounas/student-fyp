from flask import Flask, request, jsonify, render_template
import pickle
import re
import os
import requests
import smtplib
from email.message import EmailMessage
from config import conn

app = Flask(__name__)

# ─── Text Cleaner ────────────────────────────────────────────────────────────
def clean_text(text):
    text = str(text).lower()
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# ─── Load ML Models ──────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    sentiment_model = pickle.load(open(os.path.join(BASE_DIR, "models/sentiment_model.pkl"), "rb"))
    print("✅ Sentiment model loaded")
except Exception as e:
    print(f"⚠️  Could not load sentiment model: {e}")
    sentiment_model = None

try:
    islamic_model = pickle.load(open(os.path.join(BASE_DIR, "models/islamic_model.pkl"), "rb"))
    print("✅ Islamic model loaded")
except Exception as e:
    print(f"⚠️  Could not load Islamic model: {e}")
    islamic_model = None

# ─── Database Connection Check ───────────────────────────────────────────────
try:
    from config import conn
    if conn:
        print("✅ Database connected successfully")
    else:
        print("⚠️  Database not connected (app will work without it)")
except Exception as e:
    print(f"⚠️  Database connection error: {e}")
    conn = None

# ─── Dream Analyzer ──────────────────────────────────────────────────────────
def analyze_dream_ml(text):
    clean = clean_text(text)
    if sentiment_model:
        sentiment = sentiment_model.predict([clean])[0]
    else:
        sentiment = "neutral"
    if islamic_model:
        islamic = islamic_model.predict([clean])[0]
    else:
        islamic = "nafsani"
    meaning = f"This dream reflects {sentiment} emotions and {islamic} influence."
    return sentiment, islamic, meaning

# ─── Routes ──────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("Islamic Dream Analyzer.html")

@app.route("/test", methods=["GET"])
def test():
    db_status = "connected" if conn else "not connected"
    db_count = 0
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM dreams")
                db_count = cursor.fetchone()[0]
        except Exception as e:
            db_status = f"error: {str(e)}"
    
    return jsonify({
        "status": "ok", 
        "message": "Server is running",
        "database": {
            "status": db_status,
            "dreams_count": db_count
        },
        "models": {
            "sentiment": "loaded" if sentiment_model else "not loaded",
            "islamic": "loaded" if islamic_model else "not loaded"
        }
    })

@app.route("/analyze-dream", methods=["POST"])
def dream_analyzer():
    data = request.json
    dream_text = data.get("dream_text", "").strip()
    if not dream_text:
        return jsonify({"error": "Dream text is required"}), 400
    try:
        sentiment, islamic, meaning = analyze_dream_ml(dream_text)
        
        # Save to database if connected
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO dreams (dream_text, sentiment, islamic, meaning) VALUES (%s, %s, %s, %s)",
                        (dream_text, sentiment, islamic, meaning)
                    )
                    conn.commit()
                print("✅ Dream saved to database")
            except Exception as db_e:
                print(f"⚠️  Could not save to database: {db_e}")
        
        return jsonify({"sentiment": sentiment, "islamic_analysis": islamic, "meaning": meaning})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── AI Chatbot (Gemini API) ──────────────────────────────────────────────────

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyDqy1EP6HLXi5JZXX9j7Ohth0TKdTva2-I")

@app.route("/chatbot", methods=["POST"])
def chatbot():
    data = request.json
    user_message = data.get("message", "").strip()
    history = data.get("history", [])

    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    if GEMINI_API_KEY == "I was in deep water and struggling to stay above the surface" or not GEMINI_API_KEY:
        return jsonify({
            "error": " GEMINI_API_KEY not working "
        }), 503

    SYSTEM_PROMPT = (
        "You are DreamBot, an expert Islamic dream interpreter and emotional support assistant.\n\n"
        "Rules:\n"
        "- Only provide meanings based on authentic Islamic sources (Quran, Hadith, Ibn Sirin, Al-Nabulsi).\n"
        "- Do NOT fabricate references. If no authentic reference is known, say 'No authentic reference found'.\n"
        "- For every dream interpretation, provide:\n"
        "  1. Meaning (detailed)\n"
        "  2. Category: Positive / Neutral / Negative\n"
        "  3. Type: Rehmani (from Allah) / Shaitani (from Shaytan) / Nafsani (from self)\n"
        "  4. Reference (Hadith / Scholar name)\n"
        "  5. Brief explanation in simple Urdu at the end (labeled 'اردو تشریح:')\n\n"
        "Format dream analysis with clear sections using emojis:\n"
        "🔮 **Dream Meaning:** ...\n"
        "📊 **Category:** ...\n"
        "✨ **Type:** ...\n"
        "📚 **Reference:** ...\n"
        "🕌 **اردو تشریح:** ...\n\n"
        "For non-dream emotional support messages, respond warmly and Islamically.\n"
        "Always be empathetic, supportive, and spiritually grounded."
    )

    gemini_contents = [
        {"role": "user", "parts": [{"text": SYSTEM_PROMPT}]},
        {"role": "model", "parts": [{"text": "Understood. I am DreamBot, ready to interpret Islamic dreams. Assalamu Alaikum!"}]}
    ]
    for h in history[-10:]:
        role = "user" if h["role"] == "user" else "model"
        gemini_contents.append({"role": role, "parts": [{"text": h["content"]}]})
    gemini_contents.append({"role": "user", "parts": [{"text": user_message}]})

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={"contents": gemini_contents, "generationConfig": {"maxOutputTokens": 1000, "temperature": 0.7}},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()

        if "error" in result:
            err_msg = result["error"].get("message", "Unknown error")
            return jsonify({"error": f"Gemini error: {err_msg}"}), 503

        if not result.get("candidates"):
            return jsonify({"error": "Gemini gave empty response . check API key."}), 503

        bot_reply = result["candidates"][0]["content"]["parts"][0]["text"]
        return jsonify({"reply": bot_reply})

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else 0
        if status == 403 or status == 400:
            return jsonify({"error": "Gemini API key is invalid . Get a new key from: https://aistudio.google.com/app/apikey"}), 503
        elif status == 429:
            return jsonify({"error": "API rate limit exceeded. wait and try again."}), 503
        return jsonify({"error": f"Gemini HTTP error {status}: {str(e)}"}), 503
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Internet connection check . Gemini API is not connecting ."}), 503
    except requests.exceptions.Timeout:
        return jsonify({"error": "Gemini API timeout .  try again."}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Mental Health Email Alert ────────────────────────────────────────────────
# 👇 APNI GMAIL AUR APP PASSWORD YAHAN DAALO
# Gmail App Password kaise banayein: Google Account > Security > 2-Step Verification > App Passwords
EMAIL_SENDER   = os.environ.get("EMAIL_SENDER",   "fataekim2601@gmail.com")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "kim2601@")

@app.route("/send-mental-health-alert", methods=["POST"])
def send_mental_health_alert():
    data           = request.json
    to_email       = data.get("email", "").strip()
    negative_count = data.get("negativeCount", 7)
    user_name      = data.get("userName", "User")

    if not to_email:
        return jsonify({"error": "Email address required hai"}), 400

    # If email not configured, still return success (app works, just no email)
    if EMAIL_SENDER == "fataekim2601@gmail.com" or EMAIL_PASSWORD == "kim2601@":
        print(f"⚠️  Email not configured — would have sent alert to {to_email}")
        return jsonify({
            "success": True,
            "message": "Alert recorded! (Email server configured nahi hai abhi)",
            "email_sent": False
        })

    try:
        msg            = EmailMessage()
        msg["Subject"] = "🌙 Islamic Dream Analyzer — Mental Health Alert"
        msg["From"]    = EMAIL_SENDER
        msg["To"]      = to_email
        msg.set_content(f"""Assalamu Alaikum {user_name},

⚠️  MENTAL HEALTH ALERT — Islamic Dream Analyzer

Aap ne {negative_count} consecutive negative dreams record kiye hain.
Yeh pattern stress, anxiety, ya emotional imbalance ki nishani ho sakta hai.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Islamic Guidance & Suggestions:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 📿 Sone se pehle Ayat-ul-Kursi (2:255) parhein
2. 🌙 Sone se pehle Surah Ikhlas, Falaq, Naas teen teen baar parhein
3. 🤲 Dua: "A'oothu bi kalimaatillaahit-taammaati min sharri maa khalaq"
4. 💚 Kisi trusted Islamic counselor ya mental health professional se baat karein
5. 🧘 Din mein dhikr ki practice karein — SubhanAllah, Alhamdulillah, Allahu Akbar
6. 😴 Raat ko 7-8 ghante ki neend zaroor lein

Rasool Allah ﷺ ne farmaya: "Agar koi bura khwab dekhe to Shaytan se Allah ki panaah maange aur us khwab ki burai se bhi." (Bukhari & Muslim)

Aap akele nahi hain. Allah aapko sukoon aur sehat ata farmaye. Ameen.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Islamic Dream Analyzer — Mental Health Support
""")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)

        print(f"✅ Mental health alert sent to {to_email}")
        return jsonify({"success": True, "message": "Mental health alert email bhej diya gaya!", "email_sent": True})

    except smtplib.SMTPAuthenticationError:
        return jsonify({
            "error": "Gmail login fail. Regular password nahi, App Password use karo.",
            "help": "Google Account > Security > 2-Step Verification > App Passwords"
        }), 500
    except Exception as e:
        return jsonify({"error": f"Email send nahi hua: {str(e)}"}), 500


# ─── Dream Diary ──────────────────────────────────────────────────────────────
@app.route("/api/dreams", methods=["GET"])
def get_dreams():
    if not conn:
        return jsonify({"message": "Database not connected", "dreams": []})
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, dream_text, sentiment, islamic, meaning, created_at FROM dreams ORDER BY created_at DESC")
            rows = cursor.fetchall()
            dreams = [
                {
                    "id": row[0],
                    "dream_text": row[1],
                    "sentiment": row[2],
                    "islamic": row[3],
                    "meaning": row[4],
                    "created_at": row[5].isoformat() if row[5] else None
                }
                for row in rows
            ]
        return jsonify({"dreams": dreams})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/dreams", methods=["GET"])
def view_dreams():
    if not conn:
        return "Database not connected", 500
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, dream_text, sentiment, islamic, meaning, created_at FROM dreams ORDER BY created_at DESC")
            rows = cursor.fetchall()
        return render_template("dreams.html", dreams=rows)
    except Exception as e:
        return f"Error loading dreams: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
